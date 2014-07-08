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
from collections import namedtuple
from sqlalchemy import create_engine

from email import Email

import setting_watch_dog as setting

os.chdir(setting._WORKDIR)

ALL_FAIL_NOTIFICATIONS = setting.ALL_FAIL_NOTIFICATIONS
ONE_FAIL_NOTIFICATIONS = setting.ONE_FAIL_NOTIFICATIONS

ALL_FAIL_ALERTS = []
ONE_FAIL_ALERTS = []


# check point & parameters

_HTTP = setting._HTTP
_WEB = setting._WEB
_CACHE = setting._CACHE
_SOLR = setting._SOLR
_DB_CHECK_KEY = setting._DB_CHECK_KEY
_DB_CHECK_VALUE = setting._DB_CHECK_VALUE
_DB = setting._DB
_API = setting._API
_JOB = setting._JOB
_DMS = setting._DMS

_UA = setting._UA
_TIMEOUTS = setting._TIMEOUTS
_TIMEOUT_ERRORS = setting._TIMEOUT_ERRORS
_SUCCEED_CODE = setting._SUCCEED_CODE

_REPORTS = {
    'http': [],
    'web': [],
    'cache': [],
    'solr': [],
    'api': [],
    'db': [],
    'job': [],
    'dms': [],
}



def check_web():
    all_succeed = True
    all_fail = True
    reports = _REPORTS['web']
    reports.append('')
    reports.append('========== WEB APP Check ===========')
    urls = _WEB['urls']
    for url in urls:
        reports.append('')
        succeed = check_url(url, reports)
        all_succeed = all_succeed and succeed
        if succeed: all_fail = False
        # alert if required
        print succeed and 'Succeed' or 'Fail'
    reports.append('========== WEB APP END  ===========')

    # alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for WEB APP')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for WEB APP')


    return all_succeed


def check_http():
    all_succeed = True
    all_fail = True
    reports = _REPORTS['http']
    reports.append('')
    reports.append('========== HTTP Check ===========')
    urls = _HTTP['urls']
    for url in urls:
        reports.append('')
        succeed = check_url(url, reports)
        all_succeed = all_succeed and succeed
        if succeed: all_fail = False
        # alert if required
        print succeed and 'Succeed' or 'Fail'
    reports.append('========== HTTP END  ===========')

    # alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for HTTP access')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for HTTP access')

    return all_succeed

def check_url(url, reports, resp_callback=None, data={}, method='GET'):
    '''
        url: url to request
        reports: reports array to append
        data: data to POST. if specified, will use POST
        resp_callback: callback function to validat result. taks 1 argument of reponse test.
    '''
    succeed = False
    if not reports:
        reports = _REPORTS['http']
    ti = 0                 # timeout index
    ti_max = len(_TIMEOUTS)
    retries = 0            # retry count

    print '>>>>> checking %s' % url
    reports.append('check %s' % url)

    rc = None
    while not succeed:
        if ti >= ti_max: break

        timeout = _TIMEOUTS[ti]
        rc = request(url, timeout, data=data, method=method)
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
    all_succeed = True
    all_fail = False
    succeed = False

    checker = _CACHE['checker']
    workpath = _CACHE['workpath']
    servers = _CACHE['cluster']
    user = _CACHE['name']
    passwd = _CACHE['passwd']

    reports = _REPORTS['cache']
    reports.append('')


    reports.append('========== CACHE Check ===========')
    p = subprocess.Popen([checker, servers, user, passwd], cwd=workpath, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rep = p.stdout.readlines()
    log = p.stderr.read()

    print log

    if rep[-1].startswith('SUCCEED'): succeed = True
    all_succeed = all_succeed and succeed
    if not succeed: all_fail = True

    reports.extend(rep)
    reports.append('========== CACHE END  ===========')


    # if not all_succeed, alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for CACHE service')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for CACHE service')

    return all_succeed

def check_solr():
    all_succeed = True
    all_fail = True
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
            print 'Expected exception:', ex
            succeed = False

        print succeed and 'Succeed validation' or 'Fail validation'
        return succeed


    for url, core in queries:
        reports.append('')
        reports.append('*** CORE %s ***' % core)
        succeed = check_url(url, reports, lambda resp: validate_solr(resp, core))
        all_succeed = all_succeed and succeed
        if succeed: all_fail = False
        # alert if required
    reports.append('========== SOLR END  ===========')

    # alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for SOLR service')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for SOLR service')

    return all_succeed


def check_api():
    all_succeed = True
    all_fail = True
    reports = _REPORTS['api']
    reports.append('')
    reports.append('========== API Check ===========')
    apis = _API['apis']

    def validate_api(resp, api):
        succeed = True
        print 'validating result ... '
        try:
            result = json.loads(resp)
            #print result
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
            print 'Expected exception:', ex
            succeed = False

        print succeed and 'Succeed validation' or 'Fail validation'
        return succeed


    for api, method, url, data in apis:
        print method, api
        for k, v in data.items():
            if v.startswith('$'):
                data[k] = _API[v[1:]]
                print k, data[k]
        data['access_token'] = _API['token']
        print data['access_token']

        reports.append('')
        reports.append('*** API %s ***' % api)
        succeed = check_url(url, reports, lambda resp: validate_api(resp, api), data=data, method=method)
        all_succeed = all_succeed and succeed
        if succeed: all_fail = False
        # alert if required
    reports.append('========== API END  ===========')

    # if not all_succeed, alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for API service')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for API service')

    return all_succeed



def check_db():
    all_succeed = True
    all_fail = True
    reports = _REPORTS['db']
    reports.append('')
    reports.append('========== DB Check ===========')
    connections = _DB['connections']
    queries = _DB['queries']

    def validate_query(query):
        succeed = True

        q = query.strip().split()
        if len(q) < 2:
            print 'Warn: query is too short.'
            #return False

        msg = ''
        cmd = q[0].upper()
        if cmd == 'SELECT':
            if not query.upper().find(' LIMIT '):
                print ('No "LIMIT" clause found in "SELECT".')
                reports.append('No "LIMIT" clause found in "SELECT".')
                succeed = False
        elif cmd == 'INSERT':
            if not query.upper().find(' WHERE '):
                print ('No "WHERE" clause found in "INSERT".')
                reports.append('No "WHERE" clause found in "INSERT".')
                succeed = False
        elif cmd == 'UPDATE':
            if not query.upper().find(' WHERE '):
                print ('No "WHERE" clause found in "UPDATE".')
                reports.append('No "WHERE" clause found in "UPDATE".')
                succeed = False
        elif cmd == 'DELETE':
            if not query.upper().find(' WHERE '):
                print ('No "WHERE" clause found in "DELETE".')
                reports.append('No "WHERE" clause found in "DELETE".')
                succeed = False
        elif cmd == 'SHOW':
            msg = 'No error'
            pass
        else:
            msg = 'No error'
            pass

        print succeed and 'Succeed validating query' or 'Fail validating query'
        return succeed


    for dbconf, desc, query, expected_rowcount, expected_values in queries:
        reports.append('')
        reports.append('*** DB %s - %s ***' % (dbconf, desc))
        succeed = True

        conn = None
        try:
            engine = create_engine(connections[dbconf])
            conn = engine.connect()
            print '>> validating %s on "%s"... ' % (desc, dbconf)
            succeed = validate_query(query)

            rs = conn.execute(query)
            if expected_rowcount >= 0 and rs.rowcount != expected_rowcount:
                reports.append('Expected effecting %d row(s) but got %d row(s)' % (expected_rowcount, rs.rowcount))
                succeed = False

            if expected_values:
                for k, v in expected_values.items():
                    if rs[k] != v:
                        reports.append('col "%s" is expected "%s" but got "%s"' % (k, str(v), str(rs[k])))
                        succeed = False

            print succeed and 'Succeed validating result' or 'Fail validating result'
            reports.append(succeed and 'SUCCEED' or 'SUCCEED')
        except Exception,ex:
            succeed = False
            reports.append('Exception: %s' % ex)
            print 'Exception:', ex
        finally:
            if conn: conn.close()

        all_succeed = all_succeed and succeed
        if succeed: all_fail = False
        # alert if required

    reports.append('========== DB END  ===========')

    # if not all_succeed, alert
    if all_fail:
        ALL_FAIL_ALERTS.append('All tests FAILED for DB service')
    elif not all_succeed:
        ONE_FAIL_ALERTS.append('At least one test FAILED for DB service')

    return all_succeed


def check_job():
    pass


def check_dms():
    pass


def check():
    t1 = time.time()
    print check_http() and '@@@  HTTP SUCCEED' or '@@@ HTTP FAIL'
    print check_web() and '@@@ WEB SUCCEED' or '@@@ WEB FAIL'
    print check_solr() and '@@@ SOLR SUCCEED' or '@@@ SOLR FAIL'
    print check_api() and '@@@ API SUCCEED' or '@@@ API FAIL'
    print check_db() and '@@@ DB SUCCEED' or '@@@ DB FAIL'
    print check_cache() and '@@@ CACHE SUCCEED' or '@@@ CACHE FAIL'
    t2 = time.time()
    print "Used %d seconds" % (t2-t1)

    f = open('watch-dog-report.txt', 'w')
    for rep in _REPORTS.values():
        for line in rep:
            f.write(line)
            f.write('\r\n')
    f.close()

    attachments = []
    attachments.append(('report.txt','./watch-dog-report.txt'))

    if  len(ALL_FAIL_ALERTS) > 0:
        print 'sending ALL_FAIL_ALERT ...'
        sendalert(ALL_FAIL_ALERTS, attachments, is_all_fail=True)
    if  len(ONE_FAIL_ALERTS) > 0:
        print 'sending ONE_FAIL_ALERT ...'
        sendalert(ONE_FAIL_ALERTS, attachments, is_all_fail=False)

    return

def sendalert(alerts, attachments=[], is_all_fail=False):
    email = Email()

    emails = ONE_FAIL_NOTIFICATIONS['emails']
    if is_all_fail:
        emails = ALL_FAIL_NOTIFICATIONS['emails']

    p = subprocess.Popen(['hostname'], cwd=workpath, stdout=subprocess.PIPE)
    hostname = p.stdout.read()

    report = StringIO()
    for x in alerts:
        print x
        report.writelines([x, '\r\n\r\n']);
    body = report.getvalue()
    report.close()

    subject = '[WARN] At least one tested failed - %s - %s' % (hostname, time.ctime())
    if is_all_fail:
        subject = '[SERVE] All TEST FAILED for a service - %s - %s' % (hostname, time.ctime())

    email.sender = 'Gagein <noreply@gagein.com>'
    retries = 3
    while retries > 0:
        try:
            email.send(emails, subject, body, '', attachments)
            retries = 0
        except Exception, ex:
            retries = retries - 1
            print '... Retry due to exception: ', ex


def request(url, timeout, data={}, method='GET', **options):
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

    if data:
        curl.setopt(curl.POSTFIELDS, urllib.urlencode(data))

    if method == 'GET':
        curl.setopt(curl.HTTPGET, 1)
    elif method == 'POST':
        curl.setopt(curl.POST, 1)
    elif method == 'PUT':
        curl.setopt(curl.PUT, 1)
    else:
        rc['error'] = -1
        rc['errstr'] = 'HTTP method "%s" is not supported yet' % method
        print 'ERROR: %s' % rc['errstr']
        return rc


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
