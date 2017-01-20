import os
import json
from threading import Thread, current_thread
import time
from time import sleep
from flask import Flask, json, render_template, request
import redis
from collections import OrderedDict
import requests
from Queue import Queue
import sys
from signal import *


REGISTRAR_URL = 'http://' + os.getenv("dashboard") + '/update'
DASHBOARD_URL = 'http://' + os.getenv("dashboard") + '?a=dashboard'

app = Flask(__name__)
port = int(os.getenv("PORT"))
vcap = json.loads(os.environ['VCAP_SERVICES'])
cloud = os.getenv("cloud")
kill_queue = Queue()

# for a local CF (not pivotol web services) change this next bit to svc = vcap['p-redis'][0]['credentials']
svc = ""
try:
    svc = vcap['rediscloud'][0]['credentials']
except:
    svc = vcap['p-redis'][0]['credentials']


# for a local CF (not pivotal web services) change this next bit to
db = ""
try:
    db = redis.StrictRedis(host=svc["hostname"], port=svc["port"], password=svc["password"],db=0)
except:
    db = redis.StrictRedis(host=svc["host"], port=svc["port"], password=svc["password"],db=0)

application_name = json.loads(os.environ['VCAP_APPLICATION'])['application_uris'][0]

class Producer(Thread):
    """
    Background thread for fetching instance info
    """
    def __init__(self,queue,killqueue):
        """
        Constructor
        """
        Thread.__init__(self)
        self.queue = queue
        self.killqueue = killqueue

    def run(self):
        print '%s - Producer thread starting now' % (current_thread())

        """
        This is the run implementation of the background thread , which fetches the instance info.
        """
        self.runFlag = True
        while self.runFlag :
            try:
                if self.killqueue.empty()==False:
                    print '%s - Producer thread will exit.' % (current_thread())
                    self.runFlag = False
                    break

                instance_id = os.getenv("CF_INSTANCE_INDEX")
                mydict = db.hgetall(application_name)
                if instance_id not in mydict :
                    self.queue.put(instance_id)
                time.sleep(1)
            except :
                pass
            finally:
                pass
        print '%s - Producer thread exit now' % (current_thread())

class Consumer(Thread):
    """
    Background thread for fetching from Queue and updating redis
    """
    def __init__(self,queue):
        """
        Constructor
        """
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        """
        Run method for background thread which updates redis
        """
        while True :
            try :
                instance_id = self.queue.get() # blocks until queue is not empty
                db.hset(application_name,instance_id,1)
                time.sleep(1)
            except:
                pass
            finally:
                pass

class MasterUpdater(Thread):
    """
    This background thread will update the aggregator/registrar app at provided url
    """
    def __init__(self,db,appname,cloud):
        """
        Constructor
        """
        Thread.__init__(self)
        self.db = db
        self.appname = appname
        self.cloud = cloud
    def run(self):
        """
        Run implementation of background thread which updates the aggregator
        """
        while True :
            try:
                appinfo = self.db.hgetall(self.appname)
                appinfo_str = json.dumps(appinfo)
                data = {'applicationname':self.appname,'appinfo':appinfo_str, 'cloud':self.cloud}
                response = requests.post(REGISTRAR_URL, data=data)
                time.sleep(2)
            except :
                pass
def init_workers():
    """
    This method is for starting all worker threads.
    We are using three workers right now .
    1. One for fetching latest instances info and adds to Queue
    2. One for fetching from Queue and updating Redis
    3. For updating the aggregator app , about this applications info.
    All are deamon threads.
    """
    party_queue = Queue()
    p = Producer(party_queue,kill_queue)
    p.daemon = True
    c = Consumer(party_queue)
    c.deamon= True
    m = MasterUpdater(db,application_name,cloud)
    m.deamon = True
    p.start()
    c.start()
    m.start()

@app.route('/addfella')
def addfella():
    """
        This endpoint is for adding fellas to the application.
        Loadbalancer decids to go for which instances and based on that fella is added to it.
    """
    instance_id = os.getenv("CF_INSTANCE_INDEX")
    print 'Instance Id ****************%s'%instance_id
    fella_count = int(db.hget(application_name,instance_id))
    message = 'success'
    if fella_count<9:
        fella_count+=1
        print 'fellacount ****************%s'%fella_count
        result = db.hset(application_name,str(instance_id),str(fella_count))
        print 'HSET result %s'%result
        print db.hgetall(application_name)
    else:
        message = 'failed - no more fellas for instance %s'%instance_id
        print message

    return json.dumps({'message':message})

@app.route('/deletefella')
def deletefella():
    """
        This endpoint is for deleting fellas to the application.
    """
    instance_id = os.getenv("CF_INSTANCE_INDEX")
    print 'Instance Id **************%s'%instance_id
    fella_count = int(db.hget(application_name,instance_id))
    message = 'success'
    if fella_count>1:
        fella_count-=1
        db.hset(application_name,instance_id,fella_count)
    else:
        message = 'failed - must have at least one fellas for instance %s'%instance_id
        print message

    return json.dumps({'message':message})

@app.route('/update',methods=['POST'])
def update():
    """
    This is the entry point for updating the aggregator info
    Each of the invidividual apps will call this endpoint with their latest info
    """
    appname = request.form['applicationname']
    appdetails = request.form['appinfo']
    appcloud = request.form['cloud']

    obj = json.loads(appdetails)
    if appname and obj:
        db.hset('applications', appname, appdetails)
        db.hset('clouds', appname, appcloud)

    return json.dumps({'message':'success'})

@app.route('/clearDashboard')
def cleardashboard():
    """
    This endpoint clears the redis dashboard so it will show only currently connected clients
    """
    appdicts = db.hgetall('applications')
    for appname in sorted(appdicts):
        db.hdel('applications', appname)

    clouddicts = db.hgetall('clouds')
    for appname in sorted(clouddicts):
        db.hdel('clouds', appname)

    print 'cleared the dashboard'
    return json.dumps({'message':'success'})


@app.route('/dashboard')
def applicationsdetails():
    """
    This is the endpoint for providing all info about the applications
    This is an internal method for registrator through which index.html loads all info
    """
    appdicts = db.hgetall('applications')
    finaldict = OrderedDict()
    for appname in sorted(appdicts):
        instances = json.loads(appdicts.get(appname))
        instance_map = OrderedDict()
        for key in sorted(instances):
            instance_map.__setitem__(key,instances.get(key))
        finaldict.__setitem__(appname,instance_map)

    clouddicts = db.hgetall('clouds')
    finalcloud = OrderedDict()
    for appname in sorted(clouddicts):
        finalcloud.__setitem__(appname, clouddicts.get(appname))
    return render_template('animals_squared.html', appdicts=finaldict, clouddicts=finalcloud)

@app.route('/instances')
def instances():
    """
        This will list out all the instances and fellas per application.
        An application can see only it's fellas and instances.
    """
    mydict = db.hgetall(application_name)
    ordered = OrderedDict()
    for key in sorted(mydict):
        ordered.__setitem__(key,mydict.get(key))
    mylist = []
    return render_template('animals.html', mydict=ordered, cloud=cloud, appname=application_name, dashboard=DASHBOARD_URL)


@app.route('/')
def index():
    """
    Main entry point
    """
    return render_template('index.html')


def handle_cleanup(*args):
    print 'Application exit'
    kill_queue.put('stop')
    instance_id = os.getenv("CF_INSTANCE_INDEX")
    result = db.hdel(application_name,instance_id)
    left = db.hlen(application_name)
    print 'Instance %s Removed, Result=%s, Left=%d' % (instance_id, result, left)
    time.sleep(1)
    os._exit(0)


def main():
    for sig in (SIGABRT, SIGINT, SIGTERM):
        signal(sig, handle_cleanup)

    init_workers()
    app.run(host='0.0.0.0', port=port)

if __name__=='__main__':
    main()
