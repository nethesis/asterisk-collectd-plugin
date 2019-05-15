=========================
asterisk-collectd-plugin
=========================

This Collectd Python plugin allows to monitor Asterisk queues and trigger Collectd notifications


Install
=========
- install https://github.com/ettoreleandrotognoli/python-ami
- Copy asterisk_monitor.py in python 2.7 path (probably /usr/lib/python2.7/site-packages)
- Copy asterisk_monitor.conf in collectd configuration directory (/etc/collectd.d/) and edit it
- restart collectd ::

    systemctl restart collectd

Configuration options
======================

Host: AMI host. Default: localhost

Hostname: Hostname used in collectd data. Default is socket.gethostname() result

Port: AMI port. Default: 5038

CollectdSocket: collectd socket, used to send notifications. Default: /var/run/collectd.sock

Username: AMI username

Secret: AMI secret

EnableGraphs: save data to collectd .rrd db. Default True

EnableNotifications: send notifications to collectd. Default True

MaxCallPerOp : queuefewop notification is triggered if there are more than MaxCallPerOp calls for each operator. Default: 2

MaxCalls: queuemaxwait notification is triggered if there are more than MaxCalls waiting and the first call waiting time is more than CallersMaxWait. Default 10

MaxHoldtime: queueload notification is triggered if there are more than MaxCalls waiting and holdtime is more than MaxHoldtime. Also queueholdtime notification is triggered if holdtime is > than MaxHoldtime Default 120 

CallersMaxWait: queuemaxwait notification is triggered if there are more than MaxCalls waiting and the first call waiting time is more than CallersMaxWait. Default 250 seconds.

Debug: If enabled, debug information is logged in syslog. Default: False

