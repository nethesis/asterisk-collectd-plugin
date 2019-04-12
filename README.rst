=========================
asterisk-collectd-plugin
=========================

This Collectd Python plugin allows to monitor Asterisk queues and trigger Collectd notifications


Install
=========
- install https://github.com/ettoreleandrotognoli/python-ami
- Copy asterisk_monitor.py in python 2.7 path (probably /usr/lib/python2.7/site-packages)
- Copy asterisk.conf in collectd configuration directory (/etc/collectd.d/) and edit it
- restart collectd ::

    systemctl collectd restart

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

MaxCallPerOp : notification is triggered if there are more than MaxCallPerOp calls for each operator. Default: 2

MaxCalls: notification is triggered if there are more than MaxCalls waiting and holdtime is more than MaxHoldtime. Default 10

MaxHoldtime: notification is triggered if there are more than MaxCalls waiting and holdtime is more than MaxHoldtime. Default 120 

Debug: If enabled, debug information is logged in syslog. Default: False

