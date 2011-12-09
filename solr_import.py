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

# Straßenverzeichnis
STREETS_FILE = '../../data/strassen.txt'

# Silbentrennungs-Datei
HYPHENATION = 'synonyms_hyphenation.txt'

# Ende der Konfiguration

import sys
import os
import re
from datastore import DataStore
import solr

def unique(list): 
   # Not order preserving 
   keys = {} 
   for e in list: 
       keys[e] = True 
   return keys.keys()

def strip_tags(text):
	if text is None:
		return text
	text = ''.join(c for c in text if ord(c) >= 32)
	text = re.sub(r'<[^>]+?>', ' ', text)
	text = re.sub(r'&#[0-9]+;', ' ', text)
	text = re.sub(r"-\n", '-', text)
	text = re.sub(r'\s{2,}', ' ', text)
	text = re.sub(r'[[:cntrl:]]+', '', text)
	text = text.strip()
	return text

def fix_hyphenation(text, synonyms):
	for syn in synonyms:
		text = text.replace(syn, synponyms[syn])
	return text

def load_hyphenation_map(path):
	f = open(path, 'r')
	lines = f.read().split()
	synonyms = {}
	for line in lines:
		parts = line.decode('utf-8').split(' => ')
		if parts is not None and len(parts) == 2:
			synonyms[parts[0]] = parts[1]
	f.close()
	return synonyms

def load_streets(path):
	return open(path, 'r').read().strip().split("\n")

def match_streets(streets, text):
	text = text.replace('str.', 'straße')
	text = text.replace('Str.', 'Straße')
	text = text.replace('pl.', 'platz')
	results = []
	for street in streets:
		if text.find(street) != -1:
			results.append(street)
	if len(results) == 0:
		return None
	return results

def normalize_doctype(dtype):
	mapping = {
		'Stellungnahme zu e. Antrag (Ausschuss)': 'Mitteilung',
		'Antrag nach § 3 der GeschO des Rates': 'Antrag',
		'Dringlichkeitsvorlage Rat': 'Dringlichkeitsvorlage',
		'Dringlichkeitsvorlage Bezirksvertretung': 'Dringlichkeitsvorlage',
		'Stellungnahme zu einem Antrag (Rat)': 'Mitteilung',
		'Dringlichkeitsvorlage Hauptausschuss': 'Dringlichkeitsvorlage',
		'Beantwortung einer Anfrage (Rat)': 'Mitteilung',
		'Antrag auf eine Aktuelle Stunde nach § 5': 'Antrag',
		'Stellungnahme zu einem Antrag (BV)': 'Mitteilung',
		'Beantwortung einer mündl. Anfrage (BV)': 'Mitteilung',
		'Antrag nach § 12 (Dringlichkeitsantrag)': 'Dringlichkeitsantrag',
		'Dringlichkeitsvorlage BV': 'Dringlichkeitsvorlage',
		'Beantwortung einer Anfrage (Ausschuss)': 'Mitteilung',
		'Beantwortung e. mündl. Anfrage (Auss.)': 'Mitteilung',
		'Beantwortung einer Anfrage (BV)': 'Mitteilung',
		'Dringlichkeitsvorlage Ausschuss': 'Dringlichkeitsvorlage',
		'Dringlichkeitsvorlage Hauptauss. /Rat A': 'Dringlichkeitsvorlage',
		'Anfrage nach § 4': 'Anfrage',
		'Beschlussvorlage Rat bzw. Hauptausschuss': 'Beschlussvorlage',
		'Antrag nach § 3': 'Antrag',
		'Anfrage nach § 4 der GeschO des Rates': 'Anfrage',
		'Stellungnahme/Beantwortung - Rat': 'Mitteilung',
		'Mitteilung BV': 'Mitteilung',
		'Antrag nach § 3 der GeschO des Rates': 'Antrag',
		'Mitteilung Ausschuss': 'Mitteilung',
		'Beschlussvorlage Bezirksvertretung': 'Beschlussvorlage',
		'Beschlussvorlage Rat / Hauptausschuss': 'Beschlussvorlage',
		'Beschlussvorlage Ausschuss': 'Beschlussvorlage',
		'Mitteilung/Beantwortung - BV': 'Mitteilung',
		'Mitteilung/Beantwortung - Ausschuss': 'Mitteilung',
	}
	if dtype in mapping:
		return mapping[dtype]
	else:
		return dtype

if __name__ == '__main__':
	s = solr.SolrConnection('http://127.0.0.1:8983/solr')
	db = DataStore(DBNAME, DBHOST, DBUSER, DBPASS)
	
	streets = load_streets(STREETS_FILE)
	
	hyphenation_map = load_hyphenation_map(HYPHENATION)
	
	num_docs = 0
	
	hyphenated = {}
	
	# Anträge abrufen
	s.delete(queries=['id:request*'])
	requests = db.get_requests()
	num_requests = len(requests)
	
	# Vorlagen abfragen
	s.delete(queries=['id:submission*'])
	submissions = db.get_submissions()
	num_submissions = len(submissions)
	
	num_overall = num_requests + num_submissions
	
	for request in requests:
		
		num_docs += 1
		
		solr_body = ''
		solr_attachments = {}
		solr_attachment_bodies = {}
		solr_agendaitem_subjects = {}
		solr_sessions = {}
		solr_committees = {}
		solr_people = {}
		solr_streets = {}
		
		print "%d von %d" % (num_docs, num_overall)
		print "Antrag:", request['request_identifier'], request['request_date']
		print "Thema:", request['request_subject']
		print ""
		
		# Verknüpfte Tagesordnungspunkte
		agendaitems = db.get_agendaitems_by_request_id(request['request_id'])
		for agendaitem in agendaitems:
			if agendaitem['session_id'] is not None:
				if agendaitem['session_identifier'] is not None:
					solr_sessions[agendaitem['session_id']] = str(agendaitem['session_id']) + ' ' + agendaitem['session_identifier'].decode('utf-8')
				if agendaitem['committee_id'] is not None:
					result = ''
					solr_committees[agendaitem['committee_id']] = str(agendaitem['committee_id']) + ' ' + agendaitem['committee_title'].decode('utf-8') + result
					if agendaitem['agendaitem_subject'] is not None:
						solr_agendaitem_subjects[int(agendaitem['agendaitem_id'])] = agendaitem['agendaitem_subject'].decode('utf-8')
						if agendaitem['agendaitem_result'] is not None:
							solr_agendaitem_subjects[int(agendaitem['agendaitem_id'])] += ' '+ agendaitem['agendaitem_result'].decode('utf-8')
						# match streeets
						matching_streets_subjects = match_streets(streets, agendaitem['agendaitem_subject'])
						if matching_streets_subjects is not None:
							for street in matching_streets_subjects:
								solr_streets[street.decode('utf-8')] = True
		
		# Verknüpfte Anhänge
		attachments = db.get_attachments_by_request_id(request['request_id'])
		for attachment in attachments:
			#print "###### Anhang:", attachment['attachment_role'], attachment['attachment_filename']
			if attachment['attachment_content'] is not None:
				dehyphenated = fix_hyphenation(strip_tags(attachment['attachment_content'].decode('utf-8')), hyphenation_map)
				solr_attachment_bodies[int(attachment['attachment_id'])] = dehyphenated
				solr_attachments[attachment['attachment_id']] = str(attachment['attachment_id']) + ' ' + attachment['attachment_role'].decode('utf-8')
				matching_streets_attachments = match_streets(streets, dehyphenated.encode('utf-8'))
				if matching_streets_attachments is not None:
					for street in matching_streets_attachments:
						solr_streets[street.decode('utf-8')] = True
		
		# Verknuepfte Personen
		people = db.get_attending_people_by_request_id(request['request_id'])
		if people is not None:
			for person in people:
				if person['person_name'] is not None:
					personstring = str(person['person_id']) + ' ' + person['person_name'].decode('utf-8')
					if person['person_organization'] is not None:
						personstring += ' ('+ person['person_organization'].decode('utf-8') +')'
					solr_people[person['person_id']] = personstring
					
					
		s.add(id='request' + str(request['request_id']), 
			betreff=request['request_subject'].decode('utf-8'),
			aktenzeichen=request['request_identifier'].decode('utf-8'),
			typ='Antrag',
			datum=request['request_date'],
			anhang=solr_attachments.values(),
			sitzung=solr_sessions.values(),
			gremium=solr_committees.values(),
			strasse=unique(solr_streets.keys()),
			person=solr_people.values(),
			inhalt=solr_body + " " + " ".join(solr_attachment_bodies.values()) + " ".join(solr_agendaitem_subjects.values())
			)
		
	for submission in submissions:
		
		num_docs += 1
		
		solr_body = ''
		solr_attachments = {}
		solr_attachment_bodies = {}
		solr_agendaitem_subjects = {}
		solr_sessions = {}
		solr_committees = {}
		solr_people = {}
		solr_streets = {}
		
		print "%d von %d" % (num_docs, num_overall)
		print "Vorlage:", submission['submission_identifier'], submission['submission_date']
		print "Thema:", submission['submission_subject']
		print ""
		
		# Verknüpfte Tagesordnungspunkte
		agendaitems = db.get_agendaitems_by_submission_id(submission['submission_id'])
		for agendaitem in agendaitems:
			if agendaitem['session_id'] is not None:
				if agendaitem['session_identifier'] is not None:
					solr_sessions[agendaitem['session_id']] = str(agendaitem['session_id']) + ' ' + agendaitem['session_identifier'].decode('utf-8')
				if agendaitem['committee_id'] is not None:
					solr_committees[agendaitem['committee_id']] = str(agendaitem['committee_id']) + ' ' + agendaitem['committee_title'].decode('utf-8')
					if agendaitem['agendaitem_subject'] is not None:
						solr_agendaitem_subjects[int(agendaitem['agendaitem_id'])] = agendaitem['agendaitem_subject'].decode('utf-8')
						# match streeets
						matching_streets_subjects = match_streets(streets, agendaitem['agendaitem_subject'])
						if matching_streets_subjects is not None:
							for street in matching_streets_subjects:
								solr_streets[street.decode('utf-8')] = True
		
		# Verknüpfte Anhänge
		attachments = db.get_attachments_by_submission_id(submission['submission_id'])
		for attachment in attachments:
			#print "###### Anhang:", attachment['attachment_role'], attachment['attachment_filename']
			if attachment['attachment_content'] is not None:
				dehyphenated = fix_hyphenation(strip_tags(attachment['attachment_content'].decode('utf-8')), hyphenation_map)
				solr_attachment_bodies[int(attachment['attachment_id'])] = dehyphenated
				solr_attachments[attachment['attachment_id']] = str(attachment['attachment_id']) + ' ' + attachment['attachment_role'].decode('utf-8')
				matching_streets_attachments = match_streets(streets, dehyphenated.encode('utf-8'))
				if matching_streets_attachments is not None:
					for street in matching_streets_attachments:
						solr_streets[street.decode('utf-8')] = True
		
		# Verknuepfte Personen
		people = db.get_attending_people_by_submission_id(int(submission['submission_id']))
		if people is not None:
			for person in people:
				if person['person_name'] is not None:
					personstring = str(person['person_id']) + ' ' + person['person_name'].decode('utf-8')
					if person['person_organization'] is not None:
						personstring += ' ('+ person['person_organization'].decode('utf-8') +')'
					solr_people[person['person_id']] = personstring
		
		s.add(id='submission' + str(submission['submission_id']), 
			betreff=submission['submission_subject'].decode('utf-8'),
			aktenzeichen=submission['submission_identifier'].decode('utf-8'),
			anhang=solr_attachments.values(),
			sitzung=solr_sessions.values(),
			gremium=solr_committees.values(),
			strasse=unique(solr_streets.keys()),
			person=solr_people.values(),
			datum=submission['submission_date'],
			inhalt=solr_body + " " + " ".join(solr_attachment_bodies.values()) + " ".join(solr_agendaitem_subjects.values()),
			typ=normalize_doctype(submission['submission_type'])
			)
		
	s.commit(wait_flush=True, wait_searcher=False)
	s.optimize()
	print num_docs, "Dokumente geschrieben"
	
	