#!/usr/bin/env python
#! coding: utf-8
# by Samuel Chen <samuel.net@gmail.com>

import sys
import os
import sendgrid

__all__ = ['Email']

class Email(object):
	sg = None
	sender='Gagein <noreply@gagein.com>'
	pwd_file = '/root/samuel/passwd'

	def __init__(self):
		name, passwd = self.read_password()
		self.sg = sendgrid.SendGridClient(name, passwd)
		
	def read_password(self):
		f = open(self.pwd_file)
		buf = ''
		while not buf.startswith('[sendgrid]'):
			buf = f.readline()
		name = f.readline()[:-1]
		pwd = f.readline()[:-1]
		f.close()
		return name, pwd

	def send(self, to_list, subject, text, html='', attachments=[], bcc_list=[]):

		message = sendgrid.Mail()
		for to in to_list: 
			message.add_to(to)
		message.set_subject(subject)
		if text:
			message.set_text(text)
		else:
			message.set_html(html)
		for atta in attachments:
			message.add_attachment(atta[0], atta[1])
		message.set_from(self.sender)
		for bcc in bcc_list:
			message.add_bcc(bcc)
		status, msg = self.sg.send(message)
		print status, msg

if __name__ == '__main__':
	if len(sys.argv) > 4:
		exit(-1)

	sender = 'Gagein <noreply@gagein.com>'
	to = sys.argv[1]
	subject = sys.argv[2]
	attachment = ''
	atta_name = ''
	body = ''

	if len(sys.argv) > 3:
		body = 'Please check the attahment.'
		attachment = sys.argv[3]
		atta_name = os.path.split(attachment)[-1]
	else:
		body = sys.stdin.read()
	
	email = Email()
	email.sender = sender
	email.send([to], subject, '', body, [(atta_name, attachment),])
	
