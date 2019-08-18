# pylint: disable=line-too-long
"""geniClient.py
    Functions for geni REST API access and processing
    """
import os, logging, time
from flask import session
import requests
import json

BASE_URL = 'https://www.geni.com/'
REDIRECT_URL = os.getenv('GENI_REDIRECT_URL', 'http://localhost:5050/home')
AUTH_URL = 'platform/oauth/authorize'
CLIENT_ID = os.getenv('GENI_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('GENI_CLIENT_SECRET', '')
TOKEN_URL = 'https://www.geni.com/platform/oauth/request_token'
PROF_URL = 'https://www.geni.com/api/profile/immediate-family?fields=id,deleted,merged_into,name,guid'
PATH_TO_URL = 'https://www.geni.com/api/profile-g{source}/path-to/profile-g{target}?skip_email=1&skip_notify=1'
INVALIDATE_URL = 'https://www.geni.com/platform/oauth/invalidate_token'
PUBLIC_URL = 'http://www.geni.com/people/private/{guid}'
OTHERS_URL = 'https://www.geni.com/api/profile-g{guid}'
PROJECT_URL = 'https://www.geni.com/api/project-{project}/profiles?fields=guid&page={page}'
PROJECT_NAME_URL = 'https://www.geni.com/api/project-{project}?fields=name'
GENI_API_SLEEP_REMAINING = 50
GENI_API_SLEEP_LIMIT = 50
GENI_API_SLEEP_WINDOW = 10

LOGGER = logging.getLogger()
logging.getLogger("requests").setLevel(logging.WARNING)

def build_auth_url():
    """Create the OAuth url for the application"""
    LOGGER.debug("buildAuthUrl")
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URL
    }
    params = '&'.join(['%s=%s' % (k, v) for k, v in params.iteritems()])
    url = '%s%s?%s' % (BASE_URL, AUTH_URL, params)
    return url

def get_new_token(code):
    """Get the authorization tokens from OAuth"""
    LOGGER.debug("get_new_token")

    params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_url': REDIRECT_URL
    }

    token_response = requests.get(TOKEN_URL, params=params)
    token_response = token_response.text
    return token_response

def get_refreshed_token(refresh_token):
    """Refresh an expired token via OAuth"""
    LOGGER.debug("get_refreshed_token")

    params = {
        'client_id': CLIENT_ID,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    token_response = requests.get(TOKEN_URL, params=params)
    token_response = token_response.text
    LOGGER.info('get_refreshed_token returns %s', token_response)
    return token_response

def get_profile_details(access_token, refresh_token):
    """Get the profile details for the logged in account"""
    global GENI_API_SLEEP_REMAINING, GENI_API_SLEEP_WINDOW, GENI_API_SLEEP_LIMIT
    payload = {'access_token':access_token}
    if 0 == GENI_API_SLEEP_REMAINING:
        LOGGER.debug('sleeping before geni api calling')
        time.sleep(GENI_API_SLEEP_WINDOW)
        GENI_API_SLEEP_REMAINING = GENI_API_SLEEP_LIMIT

    continue_flag = True
    profile_object = None
    new_access_token = None
    new_refresh_token = None
    while continue_flag:
        try:
            profile_response = requests.get(PROF_URL, params=payload)
            LOGGER.debug("Header X-API-Rate-Limit: %s", profile_response.headers['X-API-Rate-Limit'])
            LOGGER.debug("Header X-API-Rate-Remaining: %s", profile_response.headers['X-API-Rate-Remaining'])
            LOGGER.debug("Header X-API-Rate-Window: %s", profile_response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(profile_response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(profile_response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(profile_response.headers['X-API-Rate-Window'])
            profile_object = get_profile_obj(profile_response.text)
            if profile_object['status'] == 'API_ERROR':
                time.sleep(10)
            else:
                continue_flag = False
        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.debug('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token = new_access_token = token_response['access_token']
            refresh_token = new_refresh_token = token_response['refresh_token']
            payload = {'access_token':new_access_token}
        except:     #Catch all errors
            LOGGER.exception('Geni api connection error...retrying: ')
            time.sleep(5)

    profile_object['access_token'] = new_access_token if new_access_token != None else access_token
    profile_object['refresh_token'] = new_refresh_token if new_refresh_token != None else refresh_token
    return profile_object

def get_other_profile(access_token, guid):
    """Retrieve the profile of the non-logged in user as specified"""
    LOGGER.debug("get_other_profile")

    global GENI_API_SLEEP_REMAINING, GENI_API_SLEEP_WINDOW, GENI_API_SLEEP_LIMIT
    payload = {'access_token':access_token}
    if 0 == GENI_API_SLEEP_REMAINING:
        LOGGER.debug('sleeping before geni api calling')
        time.sleep(GENI_API_SLEEP_WINDOW)
        GENI_API_SLEEP_REMAINING = GENI_API_SLEEP_LIMIT

    retry_count = 0
    continue_flag = True
    profile_text = ""
    while continue_flag and retry_count < 5:
        try:
            url = OTHERS_URL.replace('{guid}', guid)
            profile_response = requests.get(url, params=payload)
            LOGGER.debug("Header X-API-Rate-Limit: %s", profile_response.headers['X-API-Rate-Limit'])
            LOGGER.debug("Header X-API-Rate-Remaining: %s", profile_response.headers['X-API-Rate-Remaining'])
            LOGGER.debug("Header X-API-Rate-Window: %s", profile_response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(profile_response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(profile_response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(profile_response.headers['X-API-Rate-Window'])
            if (profile_response.status_code != 200 or len(profile_response.text) < 16):
                LOGGER.error("Could not retrieve profile: %d - attempt %d url - %s", profile_response.status_code, retry_count, url)
                retry_count = retry_count + 1
                time.sleep(5)
            else:
                continue_flag = False
                profile_text = profile_response.text
        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.debug('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token = new_access_token = token_response['access_token']
            refresh_token = new_refresh_token = token_response['refresh_token']
            payload = {'access_token':new_access_token}
        except requests.exceptions.HTTPError as err:
            LOGGER.exception('Geni api error %s ', err)
            continue_flag = False
        except Exception as err:     #Catch all errors
            continue_flag = False
            LOGGER.exception('Geni api connection error...retrying: %s', err)
            time.sleep(5)
    return profile_text

def get_profile_obj(profile_response):
    """Parse the JSON profile response and build return object"""
    LOGGER.debug("get_profile_obj")
    data = {}
    try:
        jsoncontents = json.loads(profile_response)
    except ValueError:
        LOGGER.error("get_profile_obj error decoding JSON: %s", profile_response)
        return data
    error = jsoncontents.get('error', False)
    if error and jsoncontents['error']['type'] == 'OAuthException':
        raise GeniOAuthError(jsoncontents['error']['message'])
    elif error != False:
        data['status'] = 'API_ERROR'
        return data
    data['status'] = 'SUCCESS'

    public_url = PUBLIC_URL
    public_url = public_url.replace('{guid}', jsoncontents['focus']['guid'])
    data['id'] = jsoncontents['focus']['id']
    data['profileName'] = jsoncontents['focus'].get('name', '')
    data['geniLink'] = public_url
    data['guid'] = jsoncontents['focus']['guid']
    LOGGER.debug("get_profile_obj details - profileName=%s, guid=%s, id=%", data['profileName'], data['guid'], data['id'])
    return data

def get_geni_path_to(access_token, refresh_token, source_id, target_id):
    """Get the path to user for this source and target"""
    assert (source_id != target_id), "get_geni_path_to equal ids passed"
    global GENI_API_SLEEP_REMAINING, GENI_API_SLEEP_WINDOW, GENI_API_SLEEP_LIMIT
    payload = {'access_token':access_token}
    if 0 == GENI_API_SLEEP_REMAINING:
        LOGGER.debug('sleeping before geni api calling')
        time.sleep(GENI_API_SLEEP_WINDOW)
        GENI_API_SLEEP_REMAINING = GENI_API_SLEEP_LIMIT

    continue_flag = True
    profile_object = None
    new_access_token = None
    new_refresh_token = None
    path_object = {}
    while continue_flag:
        try:
            url = PATH_TO_URL
            url = url.replace('{source}', source_id)
            url = url.replace('{target}', target_id)
            LOGGER.info('get_geni_path_to with urls: %s', url)
            path_response = requests.get(url, params=payload)
            LOGGER.info("Header X-API-Rate-Limit: %s", path_response.headers['X-API-Rate-Limit'])
            LOGGER.info("Header X-API-Rate-Remaining: %s", path_response.headers['X-API-Rate-Remaining'])
            LOGGER.info("Header X-API-Rate-Window: %s", path_response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(path_response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(path_response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(path_response.headers['X-API-Rate-Window'])
            LOGGER.info('Geni path-to returned %s', path_response.text)
            path_object = get_path_obj(path_response.text)
            if (path_object['status'] == 'API_ERROR' and path_object['error']['message'] == 'Rate limit exceeded.'):
                time.sleep(10)
            elif (path_object['status'] == 'API_ERROR'):
                path_object.raise_for_status()
                continue_flag = False
            else:
                continue_flag = False
        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.debug('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token = new_access_token = token_response['access_token']
            refresh_token = new_refresh_token = token_response['refresh_token']
            payload = {'access_token':new_access_token}
        except requests.exceptions.HTTPError as err:
            LOGGER.exception('Geni api error %s ', err)
            path_object['status'] = 'error'
            continue_flag = False
        except:     #Catch all errors
            continue_flag = False
            LOGGER.exception('Geni api connection error...retrying: ')
            path_object['status'] = 'error'

    path_object['access_token'] = new_access_token if new_access_token != None else access_token
    path_object['refresh_token'] = new_refresh_token if new_refresh_token != None else refresh_token
    return path_object

def get_path_obj(path_response):
    """Parse the JSON path response and build return object"""
    LOGGER.debug("get_path_obj")
    data = {}
    try:
        data = json.loads(path_response)
    except ValueError:
        LOGGER.error("get_path_obj error decoding JSON: %s", path_response)
        return data
    error = data.get('error', False)
    if error and data['error']['type'] == 'OAuthException':
        raise GeniOAuthError(jsoncontents['error']['message'])
    elif error != False:
        data['status'] = 'API_ERROR'
        return data

    return data

def get_geni_project_guids(access_token, refresh_token, project_id):
    """Get the guids for a given project number"""
    global GENI_API_SLEEP_REMAINING, GENI_API_SLEEP_WINDOW, GENI_API_SLEEP_LIMIT
    page_number = 1
    total_count = 0
    guids = []
    payload = {'access_token':access_token}
    if 0 == GENI_API_SLEEP_REMAINING:
        LOGGER.debug('sleeping before geni api calling')
        time.sleep(GENI_API_SLEEP_WINDOW)
        GENI_API_SLEEP_REMAINING = GENI_API_SLEEP_LIMIT

    continue_flag = True
    new_access_token = None
    new_refresh_token = None
    project_name = None
    while continue_flag:
        try:
            data = {}
            url = PROJECT_NAME_URL
            url = url.replace('{project}', str(project_id))
            LOGGER.info('get_geni_project_guids with urls: %s', url)
            project_response = requests.get(url, params=payload)
            LOGGER.info("Header X-API-Rate-Limit: %s", project_response.headers['X-API-Rate-Limit'])
            LOGGER.info("Header X-API-Rate-Remaining: %s", project_response.headers['X-API-Rate-Remaining'])
            LOGGER.info("Header X-API-Rate-Window: %s", project_response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(project_response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(project_response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(project_response.headers['X-API-Rate-Window'])
            LOGGER.info('Geni path-to returned %s', project_response.text)
            try:
                data = json.loads(project_response.text)
                project_name = data.get('name')
                continue_flag = False
            except ValueError:
                LOGGER.error("get_geni_project_guids error decoding JSON: %s", project_response)
        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.debug('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token = new_access_token = token_response['access_token']
            refresh_token = new_refresh_token = token_response['refresh_token']
            payload = {'access_token':new_access_token}
        except requests.exceptions.HTTPError as err:
            LOGGER.exception('Geni api error %s ', err)
            continue_flag = False
        except:     #Catch all errors
            continue_flag = False
            LOGGER.exception('Geni api connection error...retrying: ')
    continue_flag = True
    while continue_flag:
        try:
            data = {}
            url = PROJECT_URL
            url = url.replace('{page}', str(page_number))
            url = url.replace('{project}', str(project_id))
            LOGGER.info('get_geni_project_guids with urls: %s', url)
            project_response = requests.get(url, params=payload)
            LOGGER.info("Header X-API-Rate-Limit: %s", project_response.headers['X-API-Rate-Limit'])
            LOGGER.info("Header X-API-Rate-Remaining: %s", project_response.headers['X-API-Rate-Remaining'])
            LOGGER.info("Header X-API-Rate-Window: %s", project_response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(project_response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(project_response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(project_response.headers['X-API-Rate-Window'])
            LOGGER.info('Geni path-to returned %s', project_response.text)
            try:
                data = json.loads(project_response.text)
            except ValueError:
                LOGGER.error("get_geni_project_guids error decoding JSON: %s", project_response)
            if (project_response.status_code != 200 and data.get('error', False) and data['error']['message'] == 'Rate limit exceeded.'):
                time.sleep(10)
            elif (project_response.status_code != 200):
                continue_flag = False
            else:
                total_count = data.get('total_count', 0)
                for result in data['results']:
                    if (len(guids) <= 200):
                        guids.append(result['guid'])
                if (len(guids) > 200 or len(guids) >= total_count):
                    continue_flag = False
                else:
                    page_number = page_number + 1
        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.debug('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token = new_access_token = token_response['access_token']
            refresh_token = new_refresh_token = token_response['refresh_token']
            payload = {'access_token':new_access_token}
        except requests.exceptions.HTTPError as err:
            LOGGER.exception('Geni api error %s ', err)
            continue_flag = False
        except:     #Catch all errors
            continue_flag = False
            LOGGER.exception('Geni api connection error...retrying: ')

    return project_name, guids


def invalidate_token(access_token):
    """Invalidate the given access token via the API for logging out"""
    LOGGER.debug("invalidateToken")
    payload = {'access_token':access_token}
    requests.get(INVALIDATE_URL, params=payload)

class GeniOAuthError(Exception):
    """Custom exception raised when session expires and we need to renew"""
    def __init__(self, value):
        super(GeniOAuthError, self).__init__(value)
        self.value = value
    def __str__(self):
        return repr(self.value)
