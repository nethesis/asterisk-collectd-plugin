
#
# Copyright (C) 2019 Nethesis S.r.l.
# http://www.nethesis.it - nethserver@nethesis.it
#
# This script is part of NethServer.
#
# NethServer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License,
# or any later version.
#
# NethServer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NethServer.  If not, see COPYING.
#

import time
import json
import collectd
import subprocess
from asterisk.ami import AMIClient,SimpleAction,AutoReconnect
import socket

def log_debug(msg):
    global CONFIG
    if CONFIG['Debug'] == True:
        collectd.info('asterisk plugin: %s' % msg)

# This is called every time AMI event is emitted
def event_listener(source, event):
    global events
    # check if event id is in events dictionary
    if event.keys['ActionID'] in events:
        if event.name == 'QueueStatusComplete':
            # set event status to complete. It is now ready for dispatch
            events[event.keys['ActionID']]['status'] = 'complete'
        elif event.name == 'QueueParams':
            if not event.keys['Queue'] in events[event.keys['ActionID']]['queues']:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']] = {}
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['OnlineMembers'] = 0
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['PausedMembers'] = 0
            for key,value in event.keys.items():
                events[event.keys['ActionID']]['queues'][event.keys['Queue']][key] = event.keys[key]
        elif event.name == 'QueueMember':
            if not event.keys['Queue'] in events[event.keys['ActionID']]['queues']:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']] = {}
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['OnlineMembers'] = 0
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['PausedMembers'] = 0
            if int(event.keys['Paused']) == 0 and int(event.keys['Status']) != 5:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['OnlineMembers'] += 1
            else:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['PausedMembers'] += 1
        elif event.name == 'QueueEntry':
            if not event.keys['Queue'] in events[event.keys['ActionID']]['queues']:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']] = {}
            if not 'Callers' in events[event.keys['ActionID']]['queues'][event.keys['Queue']]:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['Callers'] = 1
            if not 'CallersMaxWait' in events[event.keys['ActionID']]['queues'][event.keys['Queue']]:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['CallersMaxWait'] = 0
            if int(event.keys['Wait']) > events[event.keys['ActionID']]['queues'][event.keys['Queue']]['CallersMaxWait']:
                events[event.keys['ActionID']]['queues'][event.keys['Queue']]['CallersMaxWait'] = int(event.keys['Wait'])
            events[event.keys['ActionID']]['queues'][event.keys['Queue']]['Callers'] += 1
        else :
            log_debug('Unknow event: '+ str(event))

def read_callback():
    global events
    global client
    global notifications
    global CONFIG

    timeid = time.time()
    # Request queue status
    actionid='queues'+str(timeid)
    action = 'QueueStatus'
    amirequest = SimpleAction(
        action,
        ActionID=actionid,
    )
    events[actionid] = {}
    events[actionid]['type'] = 'Queues'
    events[actionid]['queues'] = {}
    events[actionid]['status'] = 'waiting'
    events[actionid]['time'] = timeid
    try:
        future = client.send_action(amirequest)
    except Exception as err:
        collectd.info('AMI send action ERROR: %s' % str(err))
        ami_client_connect_and_login(address=CONFIG['Host'],port=CONFIG['Port'],username=CONFIG['Username'],secret=CONFIG['Secret'])
        future = client.send_action(amirequest)
    log_debug('AMI queues request sent')
 
    # get last event into events list
    for aid,event in events.items():
        if event['status'] == 'complete':
            if event['type'] == 'Queues' and 'queues' in event:
                # dispatch event
                log_debug('dispatch event '+str(aid))
                for queue,data in event['queues'].items():
                    if CONFIG['EnableGraphs']:
                        # Calls
                        try:
                            dispatch_value('queue '+queue,'calls', data['Calls'],'gauge','Calls')
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # Online Members
                        try:
                            dispatch_value('queue '+queue,'online_members',data['OnlineMembers'],'gauge','Online Members')
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # Holdtime
                        try:
                            dispatch_value('Holdtime','holdtime',data['Holdtime'],'duration',queue)
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # Calls per member
                        try:
                            if data['OnlineMembers'] == 0:
                                online_members = 1
                            else:
                                online_members = data['OnlineMembers']
                            dispatch_value('CallsPerMember'+queue,'callspermember',int(data['Calls'])/online_members,'gauge','Calls per Online Member')
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # TalkTime
                        try:
                            dispatch_value('TalkTime','talktime',data['TalkTime'],'duration',queue)
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # ServiceLevel
                        try:
                            dispatch_value('ServiceLevel','servicelevel',data['ServiceLevel'],'duration',queue)
                        except Exception as err:
                            collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))
                        # Paused Members
                        try:
                            dispatch_value('queue '+queue,'paused_members',data['PausedMembers'],'gauge','Paused Members')
                        except Exception as err:
                           collectd.info('ERROR dispatching Asterisk plugin data: %s' % str(err))

                    if CONFIG['EnableNotifications']:
                        #################
                        # Notifications #
                        ################# 
                        # Queue load
                        payload = {}
                        payload['type'] = 'queueload'
                        payload['type_instance'] = 'Queue'+queue
                        payload['message'] = 'Queue %s has %s calls with waiting time of %s seconds' % (queue, data['Calls'], data['Holdtime'])
                        if int(data['Calls']) > int(CONFIG['MaxCalls']) and int(data['Holdtime']) > int(CONFIG['MaxHoldtime']) :
                            payload['severity'] = 'warning'
                        else:
                            payload['severity'] = 'okay'
                        notify(payload)

                        # Caller Max Wait too high
                        payload = {}
                        payload['type'] = 'queuemaxwait'
                        payload['type_instance'] = 'Queue'+queue
                        if 'CallersMaxWait' in data:
                            payload['message'] = 'Queue %s first call has been waiting for %s seconds' % (queue, data['CallersMaxWait'])
                        else:
                            payload['message'] = 'Queue %s has no waiting call' % queue
                        if 'CallersMaxWait' in data and int(data['Calls']) > int(CONFIG['MaxCalls']) and int(data['CallersMaxWait']) > int(CONFIG['CallersMaxWait']) :
                            payload['severity'] = 'warning'
                        else:
                            payload['severity'] = 'okay'
                        notify(payload)

                        # too few operators logged in
                        payload = {}
                        payload['type'] = 'queuefewop'
                        payload['type_instance'] = 'Queue'+queue
                        payload['message'] = 'Queue %s has %s calls and %s online operators' % (queue, data['Calls'], data['OnlineMembers'])
                        if int(data['Calls']) > int(data['OnlineMembers']) * float(CONFIG['MaxCallPerOp']):
                            payload['severity'] = 'warning'
                        else:
                            payload['severity'] = 'okay'
                        notify(payload)

                        # Holdtime too high
                        payload = {}
                        payload['type'] = 'queueholdtime'
                        payload['type_instance'] = 'Queue'+queue
                        payload['message'] = 'Queue %s has a holdtime of %s' % (queue, data['Holdtime'])
                        if int(data['Holdtime']) > int(CONFIG['MaxHoldtime']) :
                            payload['severity'] = 'warning'
                        else:
                            payload['severity'] = 'okay'
                        notify(payload)

            # delete event
            log_debug('delete event '+str(aid))
            del events[aid]
            continue

        # delete events older than x seconds
        if float(event['time']) + 9 < float(timeid):
            log_debug('delete event '+str(aid))
            del events[aid]

def ami_client_connect_and_login(address,port,username,secret):
    global client
    try:
        client = AMIClient(address=CONFIG['Host'],port=CONFIG['Port'])
        #AutoReconnect(client)
        client.login(username=CONFIG['Username'],secret=CONFIG['Secret'])
        client.add_event_listener(event_listener, white_list=['QueueParams','QueueStatusComplete','QueueMember','QueueEntry'])
        log_debug('AMI client connected')
    except Exception as err:
        collectd.info('AMI client ERROR: ' % str(err))

# configure callback is called at startup
def configure_callback(conf):
    global CONFIG
    for node in conf.children:
        if node.key in CONFIG:
            CONFIG[node.key] = node.values[0]
    CONFIG['Port'] = int(CONFIG['Port'])
    for key in ['Debug','EnableNotifications','EnableGraphs']:
        if CONFIG[key].lower() == 'true':
            CONFIG[key] = True
        else :
            CONFIG[key] = False

    log_debug('plugin configured')
    ami_client_connect_and_login(address=CONFIG['Host'],port=CONFIG['Port'],username=CONFIG['Username'],secret=CONFIG['Secret'])

# Send values to collectd
def dispatch_value(prefix, key, value, type, type_instance=None):
    if not type_instance:
        type_instance = key
        log_debug('Sending value: %s/%s=%s' % (prefix, type_instance, value))
        if value is None:
            return
    try:
        value = int(value)
    except ValueError:
        value = float(value)

    val               = collectd.Values(plugin='asterisk', plugin_instance=prefix)
    val.type          = type
    val.type_instance = type_instance
    val.values        = [value]
    val.dispatch()

def notify(payload):
    global CONFIG
    global notifications

    if payload['type']+payload['type_instance'] in notifications and notifications[payload['type']+payload['type_instance']] == payload['severity']:
        # Notification already sent
        return True
    message = 'PUTNOTIF host=%s type=%s type_instance=%s severity=%s time=%s message="%s"' % (CONFIG['Hostname'],payload['type'],payload['type_instance'],payload['severity'],time.time(),payload['message'])
    log_debug(message)
    try :
        p = subprocess.Popen(["/usr/bin/nc","-U",CONFIG['CollectdSocket']], stdin=subprocess.PIPE)
        p.communicate(message)
        if p.returncode != 0 :
            raise Exception('error %s writing to collectd socket' % str(p.returncode))
        notifications[payload['type']+payload['type_instance']] = payload['severity']
    except Exception as err:
        collectd.error('Error sending notification %s : %s' % (message,str(err)))


# Initialize default configuration
CONFIG = {
    'Host': 'localhost',
    'Hostname': socket.gethostname(),
    'Port': '5038',
    'CollectdSocket': '/var/run/collectd.sock',
    'Username': '',
    'Secret': '',
    'MaxCallPerOp' : 2,
    'MaxCalls': 10,
    'MaxHoldtime': 120, 
    'CallersMaxWait' : 250,
    'Debug' : 'False',
    'EnableGraphs': 'True',
    'EnableNotifications': 'True',
}

# Events dictionary will hold all eventrs before they are dispatched to collectd
events = {}

# Notifications dictionary
notifications = {}

# register collectd callbacks
collectd.register_read(read_callback)
collectd.register_config(configure_callback)

