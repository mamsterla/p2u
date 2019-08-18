# pylint: disable=line-too-long, too-few-public-methods, too-many-public-methods
"""db.py handle all of the database serialization and deserialization functions"""

import peewee as pw
from peewee import Model, CharField, \
    IntegerField, PrimaryKeyField, DoesNotExist
import os, logging

LOGGER = logging.getLogger()
DB_HOST = os.getenv('GENI_DB_HOST', '')
DB_NAME = os.getenv('GENI_DB_NAME', '')
DB_USER = os.getenv('GENI_DB_USER', '')
DB_PASSWD = os.getenv('GENI_DB_PASSWD', '')
STEP_THRESHOLD = 50
MY_DB = pw.MySQLDatabase(
    DB_NAME,
    host=DB_HOST,
    port=3306,
    user=DB_USER,
    passwd=DB_PASSWD)



class TopProfiles(Model):
    """Database model for top profiles"""
    profileId = CharField(primary_key=True) #PrimaryKeyField()
    profileLink = CharField()
    steps = IntegerField()
    profiles = IntegerField()

    class Meta(object):
        """model meta information"""
        database = MY_DB
        db_table = 'geni_top_profiles'
        order_by = ('profiles',)

class GeniProfile(Model):
    """Database model for a Geni profile"""
    gid = PrimaryKeyField()
    profileId = CharField()
    profileName = CharField()
    profileLink = CharField()
    step = IntegerField()
    profiles = IntegerField()

    class Meta(object):
        """model meta information"""
        database = MY_DB
        db_table = 'geni_profiles'
        #primary_key = CompositeKey('profileId', 'step')
        indexes = (
            # create a unique index
            (('profileId', 'step'), True),
        )

class GeniJob(Model):
    """Database model for a currently running job"""
    jid = PrimaryKeyField()
    profileId = CharField()
    guid = CharField()
    apiKey = CharField()
    step = IntegerField()
    email = CharField()
    dbSave = CharField()
    status = IntegerField()

    class Meta(object):
        """model meta information"""
        database = MY_DB
        db_table = 'geni_job'

def save_geni_profile(step_data, name, guid, link):
    """serialize a geni profile"""
    LOGGER.debug("save_geni_profile name=%s, link=%s", name, link)

    MY_DB.connect()
    try:
        #Check if existing profile
        profile = GeniProfile.select().where(GeniProfile.profileId == guid,
                                             GeniProfile.step == step_data['step']).get()
        if profile != None:
            #existing record, update counts
            LOGGER.info("save_geni_profile update profileName = %s, profiles=%s, profileId=%s", name, step_data['total'], guid)
            query = GeniProfile.update(profiles=step_data['total'], profileName=name).where(
                GeniProfile.profileId == guid, GeniProfile.step == step_data['step'])
            query.execute()
    except DoesNotExist as exception:
        LOGGER.debug("save_geni_profile no profile, e=%s", exception)
        #No worries. new record
        LOGGER.info("save_geni_profile create profileName = %s, profiles=%s, profileId=%s link=%s", name, step_data['total'], guid, link)
        profile = GeniProfile.create(
            profileId=guid,
            profileName=name,
            profileLink=link,
            step=step_data['step'],
            profiles=step_data['total']
        )
        MY_DB.close()

def save_profile(record):
    """save a profile in the top profiles table"""
    LOGGER.debug("save_profile")
    try:
        MY_DB.connect()
        #Check if existing profile
        profile = TopProfiles.select().where(TopProfiles.profileId == record['profileId']).get()
        if profile.profiles < record['profiles']:
            #existing record, update counts
            query = TopProfiles.update(steps=record['steps'], profiles=record['profiles']).where(TopProfiles.profileId == record['profileId'])
            query.execute()
    except DoesNotExist:
        #No worries. new record
        profile = TopProfiles.create(
            profileId=record['profileId'],
            profileLink=record['profileLink'],
            steps=record['steps'],
            profiles=record['profiles']
        )
    MY_DB.close()

def get_top10_profiles():
    """retrieve the top 10 profiles from the datbase"""
    LOGGER.debug("get_top10_profiles")
    steps = []
    last_count = 0
    try:
        MY_DB.connect()
        for i in range(1, 11):
            rows = GeniProfile.select().where(GeniProfile.step == i).order_by(GeniProfile.profiles.desc())
            current_row = 1
            for row in rows:
                if (current_row == 1) or (current_row > 1 and last_count == row.profiles):
                    steps.append({
                        'profileId':row.profileId,
                        'profileName':row.profileName,
                        'profileLink':row.profileLink,
                        'step':row.step,
                        'profiles':row.profiles
                    })
                else:
                    break
                current_row = current_row + 1
                last_count = row.profiles
    except DoesNotExist:
        LOGGER.exception("get top10 exception:")
    MY_DB.close()
    data = {}
    data['top50'] = steps
    return steps

def get_top50_profiles(step_count):
    """retrieve the top 50 profiles from the datbase"""
    LOGGER.debug("get_top50_profiles")
    steps = []
    try:
        MY_DB.connect()
        rows = GeniProfile.select().where(GeniProfile.step == step_count).order_by(GeniProfile.profiles.desc()).limit(STEP_THRESHOLD)
        for row in rows:
            steps.append({
                'profileId':row.profileId,
                'profileName':row.profileName,
                'profileLink':row.profileLink,
                'step':row.step,
                'profiles':row.profiles
            })
    except DoesNotExist:
        LOGGER.exception("get top 50 error: ")
    MY_DB.close()
    #data = {}
    #data['top50'] = steps
    #print data
    return steps

def get_top50_step_profiles(step):
    """retrieve the top 50 step profiles from the datbase"""
    LOGGER.debug("get_top50_step_profiles")
    steps = []
    try:
        MY_DB.connect()
        top = GeniProfile.select(GeniProfile.step == step).order_by(GeniProfile.profiles.desc()).limit(STEP_THRESHOLD)
        for top_row in top:
            steps.append({
                'profileId':top_row.profileId,
                'profileLink':top_row.profileLink,
                'step':top_row.step,
                'profiles':top_row.profiles
            })
    except DoesNotExist:
        LOGGER.exception("get top 50 step profiles does not exist error: ")
    except:
        LOGGER.exception("get top 50 step profiles general error: ")

    MY_DB.close()
    return steps

def get_jobs():
    """get all running jobs from the database"""
    LOGGER.debug("get_jobs")
    jobs = None
    try:
        MY_DB.connect()
        jobs = GeniJob.select(GeniJob.status == 'N')
    except DoesNotExist:
        LOGGER.exception("get_job empty jobs not found")
    except:
        LOGGER.exception("get_job general exception")
    MY_DB.close()
    return jobs

def update_job(jid):
    """update a currently running job in the database"""
    LOGGER.debug("update_job")
    try:
        MY_DB.connect()
        query = GeniJob.update(status='Y').where(GeniJob.jid == jid)
        query.execute()
    except DoesNotExist:
        LOGGER.exception("update_job empty jobs not found")
    except:
        LOGGER.exception("update_job general exception")
    MY_DB.close()

def get_top_profiles():
    """retrieve the top profiles from the database"""
    LOGGER.debug("get_top_profiles")
    steps = []
    try:
        MY_DB.connect()
        top = TopProfiles.select().order_by(TopProfiles.profiles.desc()).limit(50)
        for top_row in top:
            steps.append({
                'profileId':top_row.profileId,
                'profileLink':top_row.profileLink,
                'steps':top_row.steps,
                'profiles':top_row.profiles
            })
    except DoesNotExist:
        LOGGER.exception("get_top_profiles does not exist")
    except:
        LOGGER.exception("get_top_profiles general exception")
    MY_DB.close()
    return steps

def setup_db():
    global MY_DB
    MY_DB.connect()
    TopProfiles.create_table(True)
    GeniProfile.create_table(True)
    GeniJob.create_table(True)
    MY_DB.close()
    LOGGER = logging.getLogger()
    LOGGER.info('db connect and tables created')
