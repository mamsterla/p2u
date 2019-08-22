# pylint: disable=line-too-long
"""P2U - Geni path to your
    For a given profile, calculate the path to your profile
    Save and recall top profiles
    """

from setenvs import set_configs
import os, logging, logging.config, time

set_configs()

from flask import Flask, redirect, request, session, url_for, jsonify, send_file
import json
from geni_client import build_auth_url, get_new_token, get_other_profile, \
    get_profile_details, invalidate_token, get_geni_path_to, get_geni_project_guids
from simplekv.memory import DictStore
from flask_kvsession import KVSessionExtension
from db import \
    get_top_profiles, get_top10_profiles, save_geni_profile, get_top50_profiles, setup_db
from sets import Set
from mail import sendEmail, sendErrorEmail, sendSetsEmail
from rq import Queue
from worker import CONN, get_redis_url
from rq_dashboard import RQDashboard
from operator import itemgetter

APP = Flask(__name__)
"""LOGGER = logging.getLogger(__name__)"""
LOGGER = APP.logger
HOST = None
PORT = None
Q = Queue("p2u_default", connection=CONN)
PQ = Queue("p2u_high", connection=CONN)
LOGGER.info("Running as app %s", __name__)

president_guids = ['6000000008211776777', '6000000012593135757', '6000000003849466047', '4438583119100069835', '4239120304610034677', '6000000002917823767', '6000000007059604501',
                    '353493399110004524', '6000000002040323796', '6000000000426801888', '6000000002926000992', '6000000002143404336', '6000000010299714607', '6000000010589552846',
                    '6000000000742096365', '6000000002686627053', '361204095530004567', '6000000012923720786', '6000000002617389863', '6000000003044154591', '6000000004087964040',
                    '6000000000351053834', '6000000004133198123', '6000000000351053834', '6000000002262321210', '4042234486350129799', '6000000002138844534', '6000000002388958269',
                    '6000000002530536418', '6000000003076423522', '6000000013608925106', '6000000000264958780', '6000000003055068438', '6000000002880912606', '6000000002045454764',
                    '6000000002957513435', '6000000002584729654', '6000000001962458192', '6000000010283870415', '296439762670005461', '6000000001961474289', '6000000000516320779',
                    '6000000010349180549','6000000007106626344'
]

monarch_guids =   ['376469227150012924' ,'6000000046928936821' ,'6000000002244407514' ,'6000000010983151777' ,'6000000096531817900' ,'6000000009200877593' ,'6000000002003739635' ,
                    '6000000028694257409' ,'6000000009776107873' ,'6000000055865581117' ,'6000000009796535956' ,'6000000001366324136' ,'6000000018714406121' ,
                    '6000000008736158916' ,'6000000014308244289' ,'6000000003957630238' ,'6000000000703639356' ,'6000000003492745606' ,'6000000000712079092' ,'6000000002886788191' ,
                    '4201022950330035661' ,'6000000002879557044' ,'6000000001217955606' ,'6000000013507467631' ,'6000000008735105389' ,'6000000005624696139' ,
                    '6000000000632031531' ,'6000000001783830969' ,'6000000012534792374' ,'6000000012432122615' ,'3949637710330122319' ,'6000000003365888478' ,
                    '6000000002143472001' ,'6000000002960326411' ,'6000000013756978156' ,'6000000025456521044' ,'6000000003369518706' ,'4776617482540033704' ,
                    '6000000004869028809' ,'6000000020545989912' ,'6000000024639052039' ,'6000000003276428962' ,'6000000001099160102' ,'6000000003230065968' ,
                    '6000000070154971835' ,'6000000003204158413' ,'6000000000703639356' ,'6000000003624346796' ,'6000000021871287431' ,'6000000013239216812', '4111915' ,
                    '6000000005624474269' ,'6000000018329195630' ,'6000000042048536302' ,'6000000008603456920' ,'6000000003075071669' ,'6000000019819086151' ,'6000000004655146716' ,
                    '6000000003203951187', '6000000002457013227', '6000000007442241030', '4215208366090031541', '6000000000350860821', '6000000002119283341', '6000000001336717255',
                    '6000000001336815278', '6000000000842131607', '311779792230007083', '5319372978170089688', '6000000008852088113', '6000000005599137513', '6000000007875679261',
                    '6000000003897579982', '6000000000112649355', '375784306260002721', '6000000000722248117', '4793654215250024782', '6000000001095643277'
]

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,  # this fixes the problem

    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level':'INFO',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        }
    }
})


@APP.route('/')
def index():
    """Handle the index page"""
    LOGGER.debug("login")
    return send_file('templates/login.html')

@APP.route('/login')
def login():
    """Handle the login page"""
    LOGGER.debug("login")
    return redirect(build_auth_url())

@APP.route('/home')
def home():
    """Handle the redirected OAuth session and capture tokens"""
    LOGGER.debug("home")
    code = request.args.get('code')
    token_response = get_new_token(code)
    LOGGER.error('received token_response %s', token_response)
    set_tokens(token_response)
    print('home just saved into session access token: %s', session['access_token'])
    LOGGER.info('home just saved into session access token: %s', session['access_token'])
    session['current_step'] = 0
    return send_file('templates/index.html')

def set_tokens(token_response_text):
    """Save the OAuth tokens into the session object"""
    token_response = json.loads(token_response_text)
    LOGGER.error(token_response_text)
    session['access_token'] = token_response['access_token']
    session['refresh_token'] = token_response['refresh_token']
    session['tokenExpiration'] = token_response['expires_in']
    LOGGER.info('set_tokens access_token: %s', session['access_token'])

@APP.route('/getPath2User')
def get_path_to_user():
    """Call the Path2User functionality of Geni"""
    LOGGER.debug("get_path_to_user")
    email = request.args.get('email')
    my_profile_flag = request.args.get('myProfile')
    target_profile_id = request.args.get('targetProfile')
    other_id = request.args.get('otherId')
    if my_profile_flag == 'true':
        (session['access_token'], session['refresh_token'], profile_obj) = get_profile_details(session['access_token'], session['refresh_token'])
        LOGGER.info('getPath2User guid found: %s', profile_obj['guid'])
        return process_path_to_user(target_profile_id, profile_obj['guid'], email)
    else:
        #Other profiles
        (session['access_token'], session['refresh_token'], profile_data_text) = get_other_profile(session['access_token'], session['refresh_token'], other_id)
        profile_data = json.loads(profile_data_text)
        check_id = profile_data.get('id')
        if check_id == None:
            data = {}
            data['backgroundMessage'] = 'This profile access is denied.'
            return jsonify(data)
        return process_path_to_user(target_profile_id, profile_data['guid'], email)

def process_path_to_user(target_profile_id, profile_id, email):
    """process path2user call into Geni"""
    data = {}
    try:
        params = {}
        params['access_token'] = session['access_token']
        params['refresh_token'] = session['refresh_token']
        params['email'] = email
        params['other_id'] = profile_id
        params['target_profile_id'] = target_profile_id
        LOGGER.info('get_path_to_user creating background job email %s source %s target %s', email, str(profile_id), str(target_profile_id))
        Q.enqueue_call(func=create_p2u_background_job, args=(params,), timeout=604800)
        data = {}
        data['backgroundMessage'] = 'Background Job started. You will receive an e-mail with the results when they are ready. The process can take several minutes or more, so please be patient.'

        return jsonify(data)
    except:
        LOGGER.exception('get_unique_count error:')

    return jsonify(data)

def create_p2u_background_job(params):
    """Builds long running job"""
    global LOGGER
    if LOGGER == None:
        LOGGER = logging.getLogger()
    LOGGER.debug("create_p2u_background_job")

    LOGGER.info('process path to user calling get_geni_path_to with params: %s', params['other_id'])
    continue_flag = True
    data = {}
    if params['other_id'] != params['target_profile_id']:
        while continue_flag:
            data = get_geni_path_to(params['access_token'], params['refresh_token'], params['other_id'], params['target_profile_id'])
            LOGGER.info('Path data returned: %s', str(data))
            if (str(data.get('status')) != 'pending'):
                continue_flag = False
            else:
                time.sleep(10)
        data['source_id'] = params['other_id']
        data['target_id'] = params['target_profile_id']
        if (str(data.get('status')) == 'done'):
            params['access_token'] = data['access_token']
            params['refresh_token'] = data['refresh_token']
            # load source and target names
            (params['access_token'], params['refresh_token'], source_obj) = get_other_profile(params['access_token'], params['refresh_token'], params['other_id'])
            profile_data = json.loads(source_obj)
            LOGGER.info('Source profile data returned: %s', source_obj)
            data['source_name'] = profile_data.get('name', '(unknown)')
            data['source_url'] = profile_data['profile_url']
            (params['access_token'], params['refresh_token'], target_obj) = get_other_profile(params['access_token'], params['refresh_token'], params['target_profile_id'])
            profile_data = json.loads(target_obj)
            LOGGER.info('Target profile data returned: %s', target_obj)
            data['target_name'] = profile_data['name']
            data['target_url'] = profile_data['profile_url']
            # TODO - handle error case for API
            sendEmail(params['email'], data)
        else:
            if (not data.get('status')):
                data['status'] = 'API Error'
            sendErrorEmail(params['email'], data)
    else:
        data['status'] = 'Source and target profiles cannot be the same'
        data['source_id'] = params['other_id']
        data['target_id'] = params['target_profile_id']

@APP.route('/getProfile', methods=['GET'])
def get_profile():
    """Handle web navigation to process a profile"""
    LOGGER.debug("get_profile")
    access_token = session['access_token']
    refresh_token = session['refresh_token']
    profile_id = request.args.get('profile_id')
    profile_data = ''
    if not access_token:
        redirect(url_for('login'))
    #Load from session if already there.
    try:
        if session[profile_id] != None:
            profile_data = session[profile_id]
            return jsonify(profile_data)
    except KeyError:
        pass

    try:
        (session['access_token'], session['refresh_token'], profile_data) = get_profile_details(access_token, refresh_token, profile_id, 0)
        if profile_id == None:
            session['loginProfileId'] = profile_data['id']
        if profile_data != None:
            session[profile_data['id']] = profile_data
    except:
        LOGGER.exception('top50 error:')
    return jsonify(profile_data)

@APP.route('/getPath2Presidents')
def get_path_to_presidents():
    """Call the Path2User functionality of Geni for list of Presidents"""
    LOGGER.debug("get_path_to_presidents")
    email = request.args.get('email')
    my_presidents_flag = request.args.get('myPresidents')
    other_id = request.args.get('otherId')
    return handleSet(email, my_presidents_flag, other_id, president_guids, "Presidents", False)

@APP.route('/getPath2Monarchs')
def get_path_to_monarchs():
    """Call the Path2User functionality of Geni for list of Monarchs"""
    LOGGER.debug("get_path_to_monarchs")
    email = request.args.get('email')
    my_monarchs_flag = request.args.get('myMonarchs')
    other_id = request.args.get('otherId')
    return handleSet(email, my_monarchs_flag, other_id, monarch_guids, "Monarchs", True)

@APP.route('/getPath2Projects')
def get_path_to_projects():
    """Call the Path2User functionality of Geni for list based on a project"""
    LOGGER.debug("get_path_to_monarchs")
    email = request.args.get('email')
    other_id = request.args.get('otherId')
    my_projects_flag = request.args.get('myProjects')
    project_id = request.args.get('project_id')
    (session['access_token'], session['refresh_token'], project_name, guids) = get_geni_project_guids(session['access_token'], session['refresh_token'], project_id)
    return handleSet(email, my_projects_flag, other_id, guids, project_name, True)

def handleSet(email, my_flag, other_id, guids, set_name, sort_by_steps):
    # handle case where we are implicit
    if my_flag == 'true':
        (session['access_token'], session['refresh_token'], profile_obj) = get_profile_details(session['access_token'], session['refresh_token'])
        LOGGER.info('handleSet guid found: %s', profile_obj['guid'])
        profile_id = profile_obj['guid']
    else:
        #Other profiles
        (session['access_token'], session['refresh_token'], profile_data_text) = get_other_profile(session['access_token'], session['refresh_token'], other_id)
        profile_data = json.loads(profile_data_text)
        check_id = profile_data.get('id')
        if check_id == None:
            data = {}
            data['backgroundMessage'] = 'This profile access is denied.'
            return jsonify(data)
            profile_id = profile_data['guid']

    data = {}
    try:
        params = {}
        params['access_token'] = session['access_token']
        params['refresh_token'] = session['refresh_token']
        params['email'] = email
        params['other_id'] = profile_id
        params['set_name'] = set_name
        params['guids'] = guids
        params['sort_by_steps'] = sort_by_steps
        LOGGER.info('handleSet creating background job email %s source %s', email, str(profile_id))
        Q.enqueue_call(func=create_sets_background_job, args=(params,), timeout=604800)
        data = {}
        data['backgroundMessage'] = 'Background Job started. You will receive an e-mail with the results when they are ready. Make sure to check your SPAM folder. The process can take several minutes or more, so please be patient.'

        return jsonify(data)
    except Exception as err:
        LOGGER.exception('handle_sets error: %s', err)

    return jsonify(data)

def create_sets_background_job(params):
    """Builds long running job for sets"""
    global LOGGER
    if LOGGER == None:
        LOGGER = logging.getLogger()
    LOGGER.debug("create_sets_background_job")

    data = {}
    data['source_id'] = params['other_id']
    (params['access_token'], params['refresh_token'], source_obj) = get_other_profile(params['access_token'], params['refresh_token'], params['other_id'])
    profile_data = json.loads(source_obj)
    LOGGER.info('Source profile data returned: %s', source_obj)
    data['source_name'] = profile_data.get('name', '(unknown)')
    data['source_url'] = profile_data['profile_url']
    data['set_data'] = []
    guids = params['guids']
    jobs = []
    for guid in guids:
        params['guid'] = guid
        job = PQ.enqueue_call(func=create_single_path_background_job, args=(params,), timeout=6000)
        jobs.append(job)
    continue_flag = True
    # TODO handle error cases like not found paths, etc below
    while continue_flag:
        not_finished_count = 0
        for job in jobs:
            if not job.is_finished:
                not_finished_count = not_finished_count + 1
        if (not_finished_count > 0):
            time.sleep(10)
        else:
            continue_flag = False
    for job in jobs:
        data['set_data'].append(job.result)

    # check whether to sort results
    if (params['sort_by_steps']):
        data['set_data'] = sorted(data['set_data'], key=itemgetter('step_count'))
    data['set_name'] = params['set_name']
    # send results of this set
    sendSetsEmail(params['email'], data)

def create_single_path_background_job(params):
    """Builds job to run one path on a worker"""
    global LOGGER
    if LOGGER == None:
        LOGGER = logging.getLogger()
    LOGGER.debug("create_single_path_background_job")

    continue_flag = True
    set_data = {}
    while continue_flag:
        set_data = get_geni_path_to(params['access_token'], params['refresh_token'], params['other_id'], params['guid'])
        LOGGER.info('Path data returned: %s', str(set_data))
        if (set_data.get('status') and str(set_data['status']) != 'pending'):
            continue_flag = False
        else:
            time.sleep(10)
    (params['access_token'], params['refresh_token'], target_text) = get_other_profile(params['access_token'], params['refresh_token'], params['guid'])
    profile_data = json.loads(target_text)
    LOGGER.info('Target profile data returned: %s', target_text)
    set_data['target_name'] = profile_data['name']
    set_data['target_url'] = profile_data['profile_url']
    if (str(set_data['status']) != 'not found' and str(set_data['status']) != 'done'):
        set_data['source_id'] = params['other_id']
        set_data['target_id'] = params['guid']
        set_data['step_count'] = 1000
        sendErrorEmail(params['email'], set_data)

    if (not set_data.get('step_count')):
        set_data['step_count'] = 1000
    return set_data

@APP.route('/logout')
def logout():
    """Handle navigation to logout of application"""
    access_token = session['access_token']
    invalidate_token(access_token)
    session.clear()
    return send_file('templates/login.html')

@APP.errorhandler(500)
def page_not_found(error):
    """Handle navigation for page not found error"""
    print error
    return 'This page does not exist', 500

def setup_app(app):
    """Do general app setup so we can run from gunicorn or command line"""
    global HOST, PORT
    setup_db()

    app.config['SESSION_TYPE'] = 'redis'
    app.config['SECRET_KEY'] = '12345abcdf'
    app.config['REDIS_URL'] = get_redis_url()

    # a DictStore will store everything in memory
    STORE = DictStore()
    # this will replace the app's session handling
    KVSessionExtension(STORE, APP)

    PORT = int(os.environ.get('PORT', 5050))
    HOST = os.environ.get('HOST', 'localhost')
    LOGGER.info("Starting application on PORT=%d", PORT)
    # Bind to PORT if defined, otherwise default to 5050.
    app.debug = False
    #APP.testing = True
    app.secret_key = '12345abcdf'
    RQDashboard(app)

setup_app(APP)

if __name__ == '__main__':
    APP.run(host=HOST, port=PORT)
