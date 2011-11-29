#!/usr/bin/env python
# encoding: utf-8
"""
	Dieses Script ist ein Beispiel, das zeigt, wie Daten zusammenhängend
	aus der Datenbank abgerufen werden können
"""

# Datenbank-Konfiguration
DBHOST = 'localhost'
DBUSER = 'root'
DBPASS = ''
DBNAME = 'cologne-ris'

# Ende der Konfiguration

import sys
import os
import re
from datastore import DataStore

def unique(list): 
   # Not order preserving 
   keys = {} 
   for e in list: 
       keys[e] = True 
   return keys.keys()

def strip_tags(text):
	if text is None:
		return text
	text = re.sub(r'<[^>]+?>', ' ', text)
	text = re.sub(r'\s{2,}', ' ', text)
	return text

if __name__ == '__main__':
	db = DataStore(DBNAME, DBHOST, DBUSER, DBPASS)
	
	# Vorlagen abfragen
	submissions = db.get_submissions()
	
	related_sessions_histogram = {}
	related_attachments_histogram = {}
	
	for submission in submissions:
		
		related_sessions = []
		related_attachments = []
		
		print "###"
		print "### Vorlage:", submission['submission_identifier'], submission['submission_date'], submission['submission_subject']
		print "### Art:", submission['submission_type']
		print "### Thema:", submission['submission_subject']
		print "###"
		
		# Verknüpfte Tagesordnungspunkte
		agendaitems = db.get_agendaitems_by_submission_id(submission['submission_id'])
		for agendaitem in agendaitems:
			if agendaitem['session_id'] is not None:
				related_sessions.append(int(agendaitem['session_id']))
			print "###### Sitzung:", agendaitem['session_identifier'], "vom", agendaitem['session_date']
			print "######", agendaitem['session_description']
			print "###### TOP:", agendaitem['agendaitem_identifier'], agendaitem['agendaitem_subject']
			print "######"
		
		# Verknüpfte Anhänge
		attachments = db.get_attachments_by_submission_id(submission['submission_id'])
		for attachment in attachments:
			related_attachments.append(int(attachment['attachment_id']))
			#print "###### Anhang:", attachment['attachment_id'], attachment['attachment_filename']
			print "###### Anhang:", attachment['attachment_role'], attachment['attachment_filename']
			if attachment['attachment_content'] is not None:
				print "######", len(strip_tags(attachment['attachment_content'])), "Zeichen"
			print "######"
			if attachment['session_id'] is not None:
				related_sessions.append(int(attachment['session_id']))
				print "######### Sitzung:", attachment['session_identifier'], "vom", attachment['session_date']
				print "#########", attachment['session_description']
				print "######### TOP:", attachment['agendaitem_identifier'], attachment['agendaitem_subject']
				print "#########"
		
		related_sessions = unique(related_sessions)
		related_attachments = unique(related_attachments)
				
		print "### Verknüpfte Sitzungen:", unique(related_sessions)
		print "### Verknüpfte Anhänge:", unique(related_attachments)
		print "###"
		
		related_sessions_histogram[len(related_sessions)] = related_sessions_histogram.get(len(related_sessions), 0) + 1
		related_attachments_histogram[len(related_attachments)] = related_attachments_histogram.get(len(related_attachments), 0) + 1

	print "Verknüpfte Sessions Histogramm:", related_sessions_histogram
	print "Verknüpfte Anhänge Histogramm:", related_attachments_histogram
