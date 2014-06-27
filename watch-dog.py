#!/usr/bin/env python
# coding:utf-8
# by Samuel Chen 

import sys
import os
import time
import subprocess
from cStringIO import StringIO
import pycurl
import urllib
import json

from email import Email


emails = [
	#'sqlmonitoring@gagein.com',
        'wchen@gagein.com',
]


# check point & parameters

_HTTP = {
	'urls':['http://www.gagein.com', 'https://www.gagein.com/about']
}
_WEB = {
	'urls':['https://www.gagein.com/challenge',
		'https://www.gagein.com/challenge?Name=IBM',
		]
}
_CACHE = {}
_SOLR = {
	'queries': [
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/contactac/select?q=*:*&rows=0&wt=json','contactac'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/contacts/select?q=*:*&rows=0&wt=json','contacts'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/core_agents/select?q=*:*&rows=0&wt=json','core_agents'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/core_orgevents/select?q=*:*&rows=0&wt=json','core_orgevents'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/core_personevents/select?q=*:*&rows=0&wt=json','core_personevents'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/core_updates/select?q=*:*&rows=0&wt=json','core_updates'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/followed_contacts/select?q=*:*&rows=0&wt=json','followed_contacts'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/followed_orgs/select?q=*:*&rows=0&wt=json','followed_orgs'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/member/select?q=*:*&rows=0&wt=json','member'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/org_location/select?q=*:*&rows=0&wt=json','org_location'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/org_name_mapping/select?q=*:*&rows=0&wt=json','org_name_mapping'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/orgac/select?q=*:*&rows=0&wt=json','orgac'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/organization/select?q=*:*&rows=0&wt=json','organization'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/search_keywords/select?q=*:*&rows=0&wt=json','search_keywords'),
		('http://ec2-54-209-120-195.compute-1.amazonaws.com:3033/gagein/updates/select?q=*:*&rows=0&wt=json','updates'),
	]
}


# list apis in order to get required value.
# api list has 3 field: 1 is api url, 2 is api name, 3 is api args map
# access_token will be passed to each api after 'login' called. so login must be in first one.
# retrived value can set when validate_api() calling. The value can be used if specifed in args map with $.
#
# e.g. ('https://www.gagein.com/svc/func1', 'func1', {'referral_by':'$memid'}
# here the $memid will be replaced by _API['memid'] automatically.

_API = {
	'apis':[
		('https://www.gagein.com/svc/login', 'login', {'mem_email':'wchen@gagein.com', 'mem_password':'123456'}),
		('https://www.gagein.com/svc/member/me/company/get_followed', 'get_followed', {'page':'1'}),
		('https://www.gagein.com/svc/company/website', 'company_website', {'org_name':'$orgname'}),
		],	
	'token':'',
	'memid':'',
	'orgname': 'Google',
}
_JOB = {}
_DMS = {}

_UA = 'GageinIn Watch Dog/1.0'
_TIMEOUTS = [5, 15, 60] 	# timeout for retry (second)
_TIMEOUT_ERRORS = [6, 28]	# error codes for timeout
_SUCCEED_CODE = [200, ]

_REPORTS = {
	'http': [],
	'web': [],
	'cache': [],
	'solr': [],
	'api': [],
	'job': [],
	'dms': [],
}


def check_web():
	all_succeed = True
	all_fail = False
	reports = _REPORTS['web']
	reports.append('')
	reports.append('========== WEB APP Check ===========')
	urls = _WEB['urls']
	for url in urls:
		reports.append('')
		succeed = check_url(url, reports)
		all_succeed = all_succeed and succeed
		all_fail = all_fail or succeed
		# alert if required
		print succeed and 'Succeed' or 'Fail'
	reports.append('========== WEB APP END  ===========')
	
	# if not all_succeed, alert

	return all_succeed


def check_http():
	all_succeed = True
	all_fail = False
	reports = _REPORTS['http']
	reports.append('')
	reports.append('========== HTTP Check ===========')
	urls = _HTTP['urls']
	for url in urls:
		reports.append('')
		succeed = check_url(url, reports)
		all_succeed = all_succeed and succeed
		all_fail = all_fail or succeed
		# alert if required
		print succeed and 'Succeed' or 'Fail'
	reports.append('========== HTTP END  ===========')
	
	# if not all_succeed, alert

	return all_succeed

def check_url(url, reports, resp_callback=None, data={}):
	'''
		url: url to request
		reports: reports array to append 
		data: data to POST. if specified, will use POST
		resp_callback: callback function to validat result. taks 1 argument of reponse test.
	'''
	succeed = False
	if not reports:
		reports = _REPORTS['http']
	ti = 0 				# timeout index
	ti_max = len(_TIMEOUTS)
	retries = 0			# retry count

	print '>>>>> checking %s' % url
	reports.append('check %s' % url)
	
	rc = None
	while not succeed:
		if ti >= ti_max: break

		timeout = _TIMEOUTS[ti]
		rc = request(url, timeout, data=data)
		#print rc
		error = rc['error']
		errstr = rc['errstr']
		if error != 0:
			retries += 1
			if error in _TIMEOUT_ERRORS:
				ti += 1
				msg = 'Retry %d. %s' % (retries, errstr)
				reports.append(msg)
				print (msg)
		else:
			succeed = True
			break

	reports.append('Finished. http-code:%d  time-used:%2f' % (rc['code'], rc['time']))

	if succeed and not rc['code'] in _SUCCEED_CODE:
		succeed = False

	if succeed and None != resp_callback:
		succeed = resp_callback(rc['response'])
	
	reports.append(succeed and '*** SUCCEED ***' or '*** FAIL ***') 

	return succeed


def check_cache():
	pass

def check_solr():
	all_succeed = True
	all_fail = False
	reports = _REPORTS['solr']
	reports.append('')
	reports.append('========== Solr Check ===========')
	queries = _SOLR['queries']

	def validate_solr(resp, core):
		succeed = True
		print 'validating result ... '
		try:
			result = json.loads(resp)
			num = result['response']['numFound']
			print 'Found %d results in %s' % (num, core)
			reports.append('Found %d results in %s' % (num, core))
			if num < 10:
				succeed = False
		except Exception, ex:
			print ex
			succeed = False
		
		print succeed and 'Succeed validation' or 'Fail validation'
		return succeed
		

	for url, core in queries:
		reports.append('')
		reports.append('*** CORE %s ***' % core)
		succeed = check_url(url, reports, lambda resp: validate_result(resp, core))
		all_succeed = all_succeed and succeed
		all_fail = all_fail or succeed
		# alert if required
	reports.append('========== SOLR END  ===========')
	
	# if not all_succeed, alert

	return all_succeed


def check_api():
	all_succeed = True
	all_fail = False
	reports = _REPORTS['api']
	reports.append('')
	reports.append('========== API Check ===========')
	apis = _API['apis']

	def validate_api(resp, api):
		succeed = True
		print 'validating result ... '
		try:
			result = json.loads(resp)
			print result
			status = result['status']
			msg = result['msg']
			print 'API %s got result status:%s  msg:%s' % (api, status, msg)
			if api == 'login':
				token = result['data']['access_token']
				memid = result['data']['memid']
				_API['token'] = token
				_API['memid'] = memid
				print 'Logged-in as %s. token:%s' % (memid, token)
			elif api == 'get_followed':
				orgid = result['data']['info'][0]['org_id']
				orgname = result['data']['info'][0]['org_name']
				_API['orgid'] = orgid
				_API['orgname'] = orgname
				print 'Get 1st followed organization "%s".' % org_name
				
			reports.append('API %s got result status:%s  msg:%s' % (api, status, msg))
		except Exception, ex:
			print ex
			succeed = False
		
		print succeed and 'Succeed validation' or 'Fail validation'
		return succeed
		

	for url, api, data in apis:
		for k, v in data.items():
			if v.startswith('$'):
				data[k] = _API[v[1:]]
				print k, data[k]
		data['access_token'] = _API['token']

		reports.append('')
		reports.append('*** API %s ***' % api)
		succeed = check_url(url, reports, lambda resp: validate_api(resp, api), data=data)
		all_succeed = all_succeed and succeed
		all_fail = all_fail or succeed
		# alert if required
	reports.append('========== API END  ===========')
	
	# if not all_succeed, alert

	return all_succeed



def check_job():
	pass


def check_dms():
	pass


def check():
	#print check_http() and '@@@  HTTP SUCCEED' or '@@@ HTTP FAIL'
	#print check_web() and '@@@ WEB SUCCEED' or '@@@ WEB FAIL'
	#print check_solr() and '@@@ SOLR SUCCEED' or '@@@ SOLR FAIL'
	print check_api() and '@@@ API SUCCEED' or '@@@ API FAIL'

	for rep in _REPORTS.values(): 
		for r in rep: print r

#	if len(alerts) > 0:
#		alerts.insert(0, ','.join(subjects))
#		os.system('ps aux | unix2dos > ps-aux.txt')
#		os.system('top -b -n1 | unix2dos > top.txt')
#		attachments = []
#		attachments.append(('ps-aux.txt','./ps-aux.txt'))
#		attachments.append(('top.txt','./top.txt'))
#		sendalert(alerts, statics[0], attachments)
#	
#	return status

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


def request(url, timeout, data={}, **options):
	rc = {'error':0}
	buf = StringIO()
	curl = pycurl.Curl()
	curl.setopt(pycurl.URL, url)
	curl.setopt(pycurl.USERAGENT, _UA)
	curl.setopt(pycurl.FOLLOWLOCATION, 1)
	curl.setopt(pycurl.MAXREDIRS, 5)
	#curl.setopt(pycurl.CONNECTTIMEOUT, 30)
	curl.setopt(pycurl.TIMEOUT, timeout)
	curl.setopt(pycurl.WRITEFUNCTION, buf.write)
		
	if (data):
		curl.setopt(curl.POSTFIELDS, urllib.urlencode(data))

	try:
		for k,v in options.items():
			curl.setopt(k, v) 
	except:
		pass	
	
	try:
		curl.perform()
	except Exception, ex:
		rc['error'] = ex[0]	
		#print ex

	rc['errstr'] = curl.errstr()
	rc['code'] = curl.getinfo(curl.HTTP_CODE)
	rc['time'] = curl.getinfo(curl.TOTAL_TIME)
	rc['response'] = buf.getvalue()
	#print rc['response']
	
	
	buf.close()
	curl.close()
	return rc
	

if __name__ == '__main__':
	check() 
