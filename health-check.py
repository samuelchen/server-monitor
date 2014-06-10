#!/usr/bin/env python
# coding:utf-8
# by Samuel Chen <samuel.net@gmail.com>

import sys
import os
import time
import subprocess
from cStringIO import StringIO
import sendgrid
from email import Email

emails = [
	#'sqlmonitoring@gagein.com',
        'wchen@gagein.com',
]

def parse(obj, st):
	''' parse x:y:z=n style statment to map object '''

	#print '---', st

	if ':' in st:
		kv = st.split(':', 1)
		o = kv[0] in obj and obj[kv[0]] or {}
		#print '=====', kv, '>>>', o
		parse(o, kv[1])
		obj[kv[0]] = o
	elif '=' in st:
		kv = st.split('=', 1)
		#print '***', kv
		obj[kv[0]] = float(kv[1])

	#print '### RETURN', obj

	return obj

def check():
	status = {}
	p = subprocess.Popen(['tsar','-C'], stdout=subprocess.PIPE)
	statics = p.stdout.read().split()
	for st in statics[2:]:
		parse(status, st)

	status['server'] = statics[0]
	
	alerts = []
	subjects = []
	if status['cpu']['util'] > 70:
		alert_cpu_load = False
		for load in status['load']:
			if status['load'][load] > 8:
				alert_cpu_load = True
				subjects.append('load')
				alerts.append('load:%s=%.1f' % (load, status['load'][load]))
		if alert_cpu_load:
			subjects.append('cpu')
			alerts.append('cpu:util=%.1f' % status['cpu']['util'])
	if status['mem']['util'] > 70:
		subjects.append('mem')
		alerts.append('mem:util=%.1f' % status['mem']['util'])
	for hd in status['io']:
		if status['io'][hd]['util'] > 70: 
			subjects.append('io')
			alerts.append('io:%s:util=%.1f' % (hd, status['io'][hd]['util']))
			break

	print len(alerts)

	if len(alerts) > 0:
		alerts.insert(0, ','.join(subjects))
		os.system('ps aux | unix2dos > ps-aux.txt')
		os.system('top -b -n1 | unix2dos > top.txt')
		attachments = []
		attachments.append(('ps-aux.txt','./ps-aux.txt'))
		attachments.append(('top.txt','./top.txt'))
		sendalert(alerts, statics[0], attachments)
	
	return status

def sendalert(alerts, hostname, attachments=[]):
	email = Email()

	report = StringIO()
	report.writelines(['\t\t Server Performance Alert [%s]\r\n' % hostname, '\r\n\r\n'])
	for x in alerts[1:]:
		print x
		report.writelines([x, '\r\n\r\n']);	
	body = report.getvalue()
	report.close()

	subject = 'Server Performance Alert [%s] [%s] - %s' % (alerts[0], hostname, time.ctime())	
	
	email.sender = 'Gagein <noreply@gagein.com>'
	email.send(emails, subject, body, '', attachments)


if __name__ == '__main__':
	check()
