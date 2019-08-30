import os,logging
import requests
import certifi
#Mailgun api

LOGGER = logging.getLogger(__name__)

mailgun_url = os.getenv('GENI_MAILGUN_URL', '')
mailgun_api_key = os.getenv('GENI_MAILGUN_API_KEY', '')
from_addr = os.getenv('GENI_FROM_ADDR', '')

def sendEmail(toMail, data):
    subject = "P2U relationship from " + data['source_name'] + " to " + data['target_name']
    htmlContent = prepareHtml(data)
    ret = requests.post(
                        mailgun_url,
                        verify=certifi.where(),
                        auth=("api", mailgun_api_key),
                        data={"from": from_addr,
                              "to": toMail,
                              "subject": subject,
                              "html": htmlContent})
    if (ret.status_code != requests.codes.ok):
        LOGGER.exception('Bad mailgun return %d', ret.status_code)
        ret.raise_for_status()

def sendErrorEmail(toMail, data):
    subject = "ERROR: P2U relationship from " + data['source_id'] + " to " + data['target_id']
    htmlContent = prepareErrorHtml(data)
    ret = requests.post(
                        mailgun_url,
                        verify=certifi.where(),
                        auth=("api", mailgun_api_key),
                        data={"from": from_addr,
                              "to": toMail,
                              "subject": subject,
                              "html": htmlContent})
    if (ret.status_code != requests.codes.ok):
        LOGGER.exception('Bad mailgun return %d', ret.status_code)
        ret.raise_for_status()
#Step    Profiles    Total
#1       8           8
#2       12          20
def prepareHtml(data):
    LOGGER.info('Preparing html with data: %s', str(data))
    htmlContent = u'<html><body>'
    htmlContent = htmlContent + u'<h3>Hi,</h3><br/>'
    htmlContent = htmlContent + u'<h5>Your P2U background job is finished. Status:' + data['status'] + u'<br/></h5>'
    htmlContent = htmlContent + u'<table border="1"><tr><th>Source</th><th>Target</th><th>Relationship<th>Direct</th><th>Steps</th></tr>'
    htmlContent = htmlContent + u'<tr><td><a href="' + data['source_url'] + '">' + data['source_name'] + u'</a></td>'
    htmlContent = htmlContent + u'<td><a href="' + data['target_url'] + '">' + data['target_name'] + u'</a></td>'
    htmlContent = htmlContent + u'<td><a href="'+ str(data['url'])+ u'">' + str(data['relationship']) + u'</a></td>'
    inlaw_distance = data.get('inlaw_distance', 0)
    if (inlaw_distance == 0):
        direct = "Direct"
    else:
        direct = "Indirect by " + str(inlaw_distance)
    htmlContent = htmlContent + u'<td>' + direct + u'</td><td>' + str(data['step_count']) + u'</td></tr></table><br/><br/>'
    # htmlContent = htmlContent + u'<table border=\'1\'><tr><th>Name</th><th>Relation</th></tr>'
    # for r in data['relations']:
    #     htmlContent = htmlContent + u'<tr><td>' + u''.join(r['name'])
    #     htmlContent = htmlContent + u'</td><td>' + r.get('relation','N/A').encode('UTF-8') + u'</td></tr>'
    # htmlContent = htmlContent + u'</table><br/><br/>'
    htmlContent = htmlContent + u'Please visit P2U  <b><a href=\'http://p2u.wnx.com\'>here</a></b>.<br/><br/>'
    htmlContent = htmlContent + u'Thank you,<br/>P2U</body></html>'
    return htmlContent

def prepareErrorHtml(data):
    LOGGER.info('Preparing error html with data: %s', str(data))
    htmlContent = u'<html><body>'
    htmlContent = htmlContent + u'<h3>Hi,</h3><br/>'
    htmlContent = htmlContent + u'<h5>Your P2U background job had an error. Status:' + data.get('status', 'API_ERROR') + u'<br/></h5>'
    if (data.get('error')):
        htmlContent = htmlContent + u'<br/><h5>Geni returned a message:' + str(data['error']['message']) + '<br/></h5>'
    htmlContent = htmlContent + u'Please visit P2U  <b><a href=\'http://p2u.wnx.com\'>here</a></b>.<br/><br/>'
    htmlContent = htmlContent + u'Thank you,<br/>P2U</body></html>'
    return htmlContent

def sendSetsEmail(toMail, data):
    subject = data['set_name'] + " relationship to " + data['source_name']
    htmlContent = prepareSetsHtml(data)
    ret = requests.post(
                        mailgun_url,
                        verify=certifi.where(),
                        auth=("api", mailgun_api_key),
                        data={"from": from_addr,
                              "to": toMail,
                              "subject": subject,
                              "html": htmlContent})
    if (ret.status_code != requests.codes.ok):
        LOGGER.exception('Bad mailgun return %d', ret.status_code)
        ret.raise_for_status()

def prepareSetsHtml(data):
    LOGGER.info('Preparing html with data: %s', str(data))
    htmlContent = u'<html><body>'
    htmlContent = htmlContent + u'<h3>Hi,</h3><br/>'
    htmlContent = htmlContent + u'<h5>Your <a href="' + data['set_url'] + '">' + data['set_name'] + '</a> background job is finished. <br/></h5>'
    htmlContent = htmlContent + u'<table border="1"><tr><th>Source</th><th>Target</th><th>Relationship<th>Direct</th><th>Steps</th></tr>'
    for set_data in data['set_data']:
        htmlContent = htmlContent + u'<tr><td><a href="' + data['source_url'] + '">' + data['source_name'] + u'</a></td>'
        if (set_data is not None):
            if (set_data.get('target_url')):
                htmlContent = htmlContent + u'<td><a href="' + set_data['target_url'] + '">' + set_data['target_name'] + u'</a></td>'
            else:
                htmlContent = htmlContent + u'<td>' + set_data['target_name'] + u'</td>'
            if (set_data.get('url')):
                htmlContent = htmlContent + u'<td><a href="'+ str(set_data['url'])+ u'">'
                htmlContent = htmlContent + u''.join(set_data['relationship'])
                htmlContent = htmlContent + u'</a></td>'
                inlaw_distance = set_data.get('inlaw_distance', 0)
                if (inlaw_distance == 0):
                    direct = "Direct"
                else:
                    direct = "Indirect by " + str(inlaw_distance)
                htmlContent = htmlContent + u'<td>' + direct + u'</td><td>' + str(set_data['step_count']) + u'</td></tr>'
            else:
                htmlContent = htmlContent + u'<td>No relationship found</td><td>N/A</td><td>N/A</td></tr>'
    htmlContent = htmlContent + '</table><br/><br/>'
    htmlContent = htmlContent + u'Please visit P2U  <b><a href=\'http://p2u.wnx.com\'>here</a></b>.<br/><br/>'
    htmlContent = htmlContent + u'Thank you,<br/>P2U</body></html>'
    return htmlContent
