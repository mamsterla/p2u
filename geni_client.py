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
PROJECT_NAME_URL = 'https://www.geni.com/api/project-{project}?fields=name,url'
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
    LOGGER.debug("get_profile_details")
    profile_object = None
    (access_token, refresh_token, profile_response) = geni_api_call(access_token, refresh_token, PROF_URL)
    if (profile_response):
        profile_object = get_profile_obj(profile_response.text)
    return access_token, refresh_token, profile_object

def get_other_profile(access_token, refresh_token, guid):
    """Retrieve the profile of the non-logged in user as specified"""
    LOGGER.info("get_other_profile")
    url = OTHERS_URL.replace('{guid}', guid)
    (access_token, refresh_token, profile_response) = geni_api_call(access_token, refresh_token, url)
    profile_text = None
    if (profile_response):
        profile_text = profile_response.text
    LOGGER.info('get_other_profile guid: %s returned: %s', guid, profile_text)
    return access_token, refresh_token, profile_text

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
    LOGGER.debug("get_geni_path_to")
    assert (source_id != target_id), "get_geni_path_to equal ids passed"
    path_object = {}
    if (source_id.isnumeric() and target_id.isnumeric() and source_id != target_id):
        url = PATH_TO_URL
        url = url.replace('{source}', source_id)
        url = url.replace('{target}', target_id)
        (access_token, refresh_token, path_response) = geni_api_call(access_token, refresh_token, url)
        if (path_response):
            path_object = get_path_obj(path_response.text)
            path_object['access_token'] = access_token
            path_object['refresh_token'] = refresh_token
    return path_object

def get_path_obj(path_response):
    """Parse the JSON path response and build return object"""
    LOGGER.debug("get_path_obj")
    data = {}
    try:
        data = json.loads(path_response)
    except ValueError:
        LOGGER.error("get_path_obj error decoding JSON: %s", path_response)
        data['status'] = 'API_ERROR'
        return data
    error = data.get('error', False)
    if error and data['error']['type'] == 'OAuthException':
        raise GeniOAuthError(jsoncontents['error']['message'])
    elif error != False:
        data['status'] = 'API_ERROR'

    return data

def get_geni_project_guids(access_token, refresh_token, project_id):
    """Get the guids for a given project number"""
    LOGGER.debug("get_geni_project_guids")
    page_number = 1
    total_count = 0
    guids = []
    project_name = None
    continue_flag = True
    url = PROJECT_NAME_URL
    url = url.replace('{project}', str(project_id))
    (access_token, refresh_token, project_response) = geni_api_call(access_token, refresh_token, url)
    if (project_response):
        try:
            data = json.loads(project_response.text)
            project_name = data.get('name')
            project_url = data.get('url')
        except ValueError:
            LOGGER.error("get_geni_project_guids error decoding JSON: %s", project_response)
    # Loop through and build guids
    retry_count = 0
    while continue_flag and retry_count < 5:
        data = {}
        url = PROJECT_URL
        url = url.replace('{page}', str(page_number))
        url = url.replace('{project}', str(project_id))
        (access_token, refresh_token, project_response) = geni_api_call(access_token, refresh_token, url)
        if (project_response):
            try:
                data = json.loads(project_response.text)
                total_count = data.get('total_count', 0)
                if (total_count > 0):
                    for result in data['results']:
                        if (len(guids) <= 200):
                            guids.append(result['guid'])
                    if (len(guids) > 200 or len(guids) >= total_count):
                        continue_flag = False
                    else:
                        page_number = page_number + 1
                else:
                    continue_flag = False
            except ValueError:
                LOGGER.error("get_geni_project_guids error decoding JSON: %s", project_response)
                retry_count = retry_count + 1
                time.sleep(5)

    return access_token, refresh_token, project_name, project_url, guids

def geni_api_call(access_token, refresh_token, url):
    LOGGER.debug("geni_api_call")
    global GENI_API_SLEEP_REMAINING, GENI_API_SLEEP_WINDOW, GENI_API_SLEEP_LIMIT
    payload = {'access_token':access_token}
    if 0 == GENI_API_SLEEP_REMAINING:
        LOGGER.info('sleeping before geni api calling')
        time.sleep(GENI_API_SLEEP_WINDOW)
        GENI_API_SLEEP_REMAINING = GENI_API_SLEEP_LIMIT
    continue_flag = True
    response = None
    retry_count = 0
    while (continue_flag and retry_count < 30):
        try:
            LOGGER.info('geni_api_call with url: %s', url)
            response = requests.get(url, params=payload)
            LOGGER.debug("Header X-API-Rate-Limit: %s", response.headers['X-API-Rate-Limit'])
            LOGGER.debug("Header X-API-Rate-Remaining: %s", response.headers['X-API-Rate-Remaining'])
            LOGGER.debug("Header X-API-Rate-Window: %s", response.headers['X-API-Rate-Window'])
            GENI_API_SLEEP_LIMIT = int(response.headers['X-API-Rate-Limit'])
            GENI_API_SLEEP_REMAINING = int(response.headers['X-API-Rate-Remaining'])
            GENI_API_SLEEP_WINDOW = int(response.headers['X-API-Rate-Window'])
            # check return to be 200 with no rate limiting
            if (response.status_code == 200 or response.status_code == 403):
                continue_flag = False
            elif (response.status_code == 429):
                time.sleep(10)
            else:
                try:
                    data = json.loads(response.text)
                    retry_count = retry_count + 1
                    if (data.get('error', False) and data['error']['message'] == 'Rate limit exceeded.'):
                        time.sleep(10)
                    elif (data['error']['type'] == 'ApiException'):
                        LOGGER.info('ApiException URL:%s message: %s', url, data['error']['message'])
                        continue_flag = False
                except ValueError:
                    LOGGER.error("geni_api_call error decoding JSON: %s", project_response)
                    continue_flag = False

        except GeniOAuthError as goae:
            LOGGER.error('Geni oauth error - %s', goae)
            token_text = get_refreshed_token(refresh_token)
            LOGGER.info('get_refreshed_token returned: %s', token_text)
            token_response = json.loads(token_text)
            access_token =  token_response['access_token']
            refresh_token  = token_response['refresh_token']
            payload = {'access_token':access_token}
            retry_count = retry_count + 1
            time.sleep(5)
        except requests.exceptions.HTTPError as err:
            LOGGER.exception('Geni api error %s ', err)
            retry_count = retry_count + 1
            time.sleep(5)
        except Exception as err:     #Catch all errors
            LOGGER.exception('Geni api connection error...retrying: %s', err)
            retry_count = retry_count + 1
            time.sleep(5)
    return access_token, refresh_token, response

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
