#!/usr/bin/env python
# encoding: utf-8
"""
scrape.py

Created by Marian Steinbach on 2011-11-23.
"""

DBHOST = 'localhost'
DBUSER = 'root'
DBPASS = ''
DBNAME = 'cologne-ris'


# End of configuration

import sys
import os
import random
import re
import urllib2
from StringIO import StringIO
from scrapemark import scrape
import mechanize
import MySQLdb
from pdfminer.pdfparser import PDFDocument, PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter, process_pdf
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams

class DataStore:
	def __init__(self, dbname, host='localhost', user='root', password=''):
		try:
			self.conn = MySQLdb.connect (host = host, user = user, passwd = password, db = dbname)
			self.cursor = self.conn.cursor(MySQLdb.cursors.DictCursor)
			self.cursor.execute("SET NAMES 'utf8'")
			self.cursor.execute("SET CHARACTER SET 'utf8'")
		except MySQLdb.Error, e:
			print "Error %d: %s" % (e.args[0], e.args[1])
			sys.exit (1)
	def get_rows(self, sql):
		try:
			self.cursor.execute(sql)
			rows = []
			while (1):
				row = self.cursor.fetchone()
				if row == None:
					break
				rows.append(row)
			return rows
		except MySQLdb.Error, e:
			print "Error %d: %s" % (e.args[0], e.args[1])
	def save_rows(self, table, data, unique_keys):
		if isinstance(data, list):
			pass
		else:
			data = [ data ]
		for thedict in data:
			values = []
			sql = 'INSERT INTO ' + table +' ('+ ', '.join(thedict.keys()) +')'
			sql2 = ' VALUES ('
			placeholders = []
			for el in thedict.keys():
				placeholders.append("%s")
				if thedict[el] is None:
					values.append(thedict[el])
				elif isinstance(thedict[el], int) or isinstance(thedict[el], long):
					values.append(thedict[el])
				else:
					values.append(thedict[el].encode('utf-8'))
			sql2 += ", ".join(placeholders) + ')'
			sql += sql2
			if unique_keys is not None and unique_keys != []:
				sql += ' ON DUPLICATE KEY UPDATE '
				updates = []
				for el in thedict.keys():
					if el not in unique_keys:
						updates.append(el + "=%s")
						if thedict[el] is None:
							values.append(thedict[el])
						elif isinstance(thedict[el], int) or isinstance(thedict[el], long):
							values.append(thedict[el])
						else:
							values.append(thedict[el].encode('utf-8'))
				sql += ", ".join(updates)
			#print sql
			self.cursor.execute(sql, values)

def shuffle(l):
	randomly_tagged_list = [(random.random(), x) for x in l]
	randomly_tagged_list.sort()
	return [x for (r, x) in randomly_tagged_list]

def result_string(string):
	"""
		Returns the correct normalized result string for things like u'ge\xe4ndert beschlossen'
		or returns the original unicode string if not available.
	"""
	types = {
		u'unge\xe4ndert beschlossen': 'DECIDED_UNCHANGED',
		u'ge\xe4ndert beschlossen': 'DECIDED_CHANGED',
		u'Kenntnis genommen': 'ACKNOWLEDGED',
		u'zur\xfcckgestellt': 'DEFERRED',
		u'Sache ist erledigt': 'COMPLETED'
	}
	if string in types:
		return types[string]
	return string

def get_session_ids(year, month):
	"""
		Get ids of all currently available sessions (Sitzungen)
	"""
	ids = []
	url = 'http://ratsinformation.stadt-koeln.de/si0040.asp?__cmonat='+str(month)+'&__cjahr='+str(year)
	data = scrape("""
	{*
		<td><a href="to0040.asp?__ksinr={{ [ksinr]|int }}"></a></td>
	*}
	""", url=url)
	for item in data['ksinr']:
		ids.append(item)
	return ids

def get_session_details(id):
	"""
		Get detail information on a session (Sitzung)
	"""
	global db
	url = 'http://ratsinformation.stadt-koeln.de/to0040.asp?__ksinr=' + str(id)
	html = urllib2.urlopen(url).read()
	data = {}

	data['session_id'] = id
	data['session_title'] = scrape('''
		<title>{{}}</title>
		''', html)

	data['committee_id'] = scrape('''
		<a href="kp0040.asp?__kgrnr={{}}"
		''', html)

	data['session_identifier'] = scrape('''
		<tr><td>Sitzung:</td><td>{{}}</td></tr>
		''', html)

	data['session_location'] = scrape('''
		<tr><td>Raum:</td><td>{{}}</td></tr>
		''', html)

	data['session_description'] = scrape('''
		<tr><td>Bezeichnung:</td><td>{{}}</td></tr>
		''', html)

	datetime = scrape('''
		<tr><td>Datum und Uhrzeit:</td><td>{{ datum }}, {{zeit}}&nbsp;Uhr</td></tr>
		''', html)

	if datetime['datum'] is not None:
		data['session_date'] = get_date(datetime['datum'].strip())
	else:
		print "ERROR: No date found for Session " + str(id)
	(starttime, endtime) = get_start_end_time(datetime['zeit'])
	data['session_time_start'] = starttime
	data['session_time_end'] = endtime

	db.save_rows('sessions', data, ['session_id'])
	if data['committee_id'] is not None and data['committee_id'] is not '':
		get_committee_details(data['committee_id'])
	agenda = get_agenda(html)


def get_agenda(html):
	"""
		Reads agenda items from session detail page HTML.

		We parse the HTML several times to get all details.
		- first, all agenda table rows are parsed to "all"
		- second, all agenda items with detail links
		  are captured to "linked"
		- third, all attachments are gatherd in "files"
		Then the structures are merged by agenda item number.
	"""
	# 1. Alle Agendaeinträge mit Nummer, Beschreibung und Ergebnis auslesen
	all = scrape('''
	{*
		<tr class="smcrow{{ [agendaitem].rowtype|int }}">
			<td>{{ [agendaitem].nr }}</td>
			<td>{{ [agendaitem].beschreibung }}</td>
			<td>{{ [agendaitem].more }}</td>
		</tr>
	*}
	''', html)
	# TODO: obiges Pattern erfasst nicht die Agenda-Einträge, die am Ende der Liste als
	# nicht-öffentliche Punkte mit nur zwei Tabellenspalten hängen.

	agenda = {}
	current_number = '0'
	agenda[current_number] = { 'inhalt': [], 'docs': []}
	if 'agendaitem' in all:
		for item in all['agendaitem']:
			if 'nr' in item and item['nr'] != '':
				current_number = item['nr']
				agenda[current_number] = { 'inhalt': [], 'docs': []}
			if 'beschreibung' in item and item['beschreibung'] is not None and item['beschreibung'] != '':
				if item['beschreibung'].find('Ergebnis: ') == 0:
					agenda[current_number]['ergebnis'] = result_string(item['beschreibung'][10:])
				else:
					agenda[current_number]['inhalt'].append({'beschreibung': item['beschreibung']})
			if 'more' in item and item['more'] != '':
				agenda[current_number]['docs'].append(item['more'])
	for nr in agenda:
		if agenda[nr]['docs'] == []:
			del agenda[nr]['docs']
		if agenda[nr]['inhalt'] == []:
			del agenda[nr]['inhalt']
		#print nr, agenda[nr]
	#print len(agenda), 'Tagesordnungspunkte'

	# 2. Verlinkte Vorlagen auslesen
	vorlagen = scrape('''
	{*
		<a href="vo0050.asp?__kvonr={{ [agendaitem].kvonr|int }}&amp;voselect={{ [agendaitem].voselect|int }}">{{ [agendaitem].inhalt }}</a>
	*}
	''', html)
	linked_vorlagen = {}
	if 'agendaitem' in vorlagen:
		for row in vorlagen['agendaitem']:
			linked_vorlagen[row['inhalt']] = {'vorlage_id': row['kvonr']}
			get_document_details('submission', row['kvonr'])

	# 3. Verlinkte Antraege auslesen
	antraege = scrape('''
	{*
		<a href="ag0050.asp?__kagnr={{ [agendaitem].kagnr|int }}&amp;voselect={{ [agendaitem].voselect|int }}">{{ [agendaitem].inhalt }}</a>
	*}
	''', html)
	linked_antraege = {}
	if 'agendaitem' in antraege:
		for row in antraege['agendaitem']:
			linked_antraege[row['inhalt']] = {'antrag_id': row['kagnr']}
			get_document_details('request', row['kagnr'])

	# Tagesordnungspunkte und Vorlagen/Antraege zusammenbringen
	for nr in agenda:
		#print "Agendaitem:", nr
		if 'inhalt' in agenda[nr]:
			for i in range(0, len(agenda[nr]['inhalt'])):
				#print i, agenda[nr]['inhalt'][i]
				if agenda[nr]['inhalt'][i]['beschreibung'] in linked_vorlagen:
					if 'vorlage_id' in linked_vorlagen[agenda[nr]['inhalt'][i]['beschreibung']]:
						agenda[nr]['inhalt'][i]['vorlage_id'] = linked_vorlagen[agenda[nr]['inhalt'][i]['beschreibung']]['vorlage_id']
				elif agenda[nr]['inhalt'][i]['beschreibung'] in linked_antraege:
					if 'antrag_id' in linked_antraege[agenda[nr]['inhalt'][i]['beschreibung']]:
						agenda[nr]['inhalt'][i]['antrag_id'] = linked_antraege[agenda[nr]['inhalt'][i]['beschreibung']]['antrag_id']
				#else:
				#	print "### Kein passender Antrag und keine passende Vorlage hierzu"
	return agenda

def get_document_details(dtype, id):
	"""
		Get details on a request (Antrag) or submission (Vorlage)
	"""
	global db
	data = {}
	prefix = ''
	if dtype == 'request':
		url = 'http://ratsinformation.stadt-koeln.de/ag0050.asp?__kagnr=' + str(id)
		prefix = 'request_'
	elif dtype == 'submission':
		url = 'http://ratsinformation.stadt-koeln.de/vo0050.asp?__kvonr=' + str(id)
		prefix = 'submission_'
	data[prefix + 'id'] = id
	html = urllib2.urlopen(url).read()

	html = html.replace('<br>', ' ')	

	data[prefix + 'identifier'] = scrape('''
		<tr><td>Name:</td><td>{{}}</td></tr>
		''', html)
	data[prefix + 'type'] = scrape('''
		<tr><td>Art:</td><td>{{}}</td></tr>
		''', html)
	data[prefix + 'date'] = scrape('''
		<tr><td>Datum:</td><td>{{}}</td></tr>
		''', html)
	data[prefix + 'subject'] = scrape('''
		<tr><td>Betreff:</td><td>{{}}</td></tr>
		''', html)
	if dtype == 'request':
		data['committees'] = scrape('''
			<tr><td>Gremien:</td><td>{{}}</td></tr>
			''', html)

	# Get PDFs
	attachments = scrape('''
		{*
		<form  action="ydocstart.asp" method="post"  target="_blank" name="{{ [form].name }}">
		*}
		''', html)
	if 'form' in attachments:
		forms = []
		for form in attachments['form']:
			forms.append(form['name'])
		docs = get_attachments(url, forms)
		if len(docs) > 0:
			attachment_ids = docs.keys()
			attachment_id_strings = []
			for aid in attachment_ids:
				attachment_id_strings.append(str(aid))
			data['attachment_ids'] = ' '.join(attachment_id_strings)


	# post-process
	if data[prefix + 'date'] is not None and data[prefix + 'date'] != '':
		data[prefix + 'date'] = get_date(data[prefix + 'date'])

	if dtype == 'request':
		print "New request", data[prefix + 'id']
		db.save_rows('requests', data, ['request_id'])
	elif dtype == 'submission':
		print "New submission", data[prefix + 'id']
		db.save_rows('submissions', data, ['submission_id'])

def get_attachments(url, forms_list):
	"""
		Get all attachments for the page given by url,
		only the forms with name in forms_list are submitted.
	"""
	ret = {}
	br = mechanize.Browser()
	br.open(url)
	for form in forms_list:
		attachment_id = int(form[3:])
		if not is_attachment_in_db(int(form[3:])):
			print "New attachment: " + form
			br.select_form(name=form)
			response = br.submit()
			data = response.read()
			headers = response.info()
			ret[attachment_id] = {
				'attachment_id': attachment_id,
				'attachment_mimetype': headers['content-type'].lower().decode('utf-8'),
				'attachment_size': len(data),
			}
			if 'Content-Disposition' in headers:
				ret[attachment_id]['attachment_filename'] = headers['Content-Disposition'].split('filename=')[1].decode('utf-8')
			if 'content-type' in headers and headers['content-type'].lower() == 'application/pdf':
				content = get_text_from_pdfdata(data)
			if content is None or (content is not None and content is not False):
				if content is not None and content is not False
					ret[attachment_id]['attachment_content'] = content
				db.save_rows('attachments', ret[attachment_id], ['attachment_id'])
			br.back()
	return ret

def get_text_from_pdfdata(data):
	fp = StringIO(data)
	outfp = StringIO()
	rsrc = PDFResourceManager()
	#device = TextConverter(rsrc, outfp, codec="utf-8")
	device = TagExtractor(rsrc, outfp, codec="latin-1")
	doc = PDFDocument()
	#fp = open(inputbuffer, 'rb')
	parser = PDFParser(fp)
	parser.set_document(doc)
	try:
		doc.set_parser(parser)
	except:
		return False
	doc.initialize('')
	#interpreter = PDFPageInterpreter(rsrc, device)
	interpreter = PDFPageInterpreter(rsrc, device)
	for i, page in enumerate(doc.get_pages()):
		try:
			interpreter.process_page(page)
		except:
			print "Cancelling PDF extraction due to Error"
			return False
	device.close()
	fp.close()
	return outfp.getvalue().decode("latin-1")

def get_date(string):
	"""
		'1. Februar 2010' => '2010-02-01'
	"""
	months = {'Januar':1, 'Februar':2, 'März':3, 'April':4, 'Mai':5, 'Juni':6, 'Juli':7, 'August':8, 'September':9, 'Oktober':10, 'November':11, 'Dezember':12,
		'Jan':1, 'Feb':2, 'Mrz':3, 'Apr':4, 'Mai':5, 'Jun':6, 'Jul':7, 'Aug':8, 'Sep':9, 'Okt':10, 'Nov':11, 'Dez':12}
	result = re.match(r'([0-9]+)\.\s+([^\s]+)\s+([0-9]{4})', string)
	if result is not None:
		day = int(result.group(1))
		month = months[result.group(2).encode('utf-8')]
		year = int(result.group(3))
		return "%d-%02d-%02d" % (year, month, day)

def get_start_end_time(string):
	"""
		'15 bis 16:25' => ('15:00', '16:25')
	"""
	parts = string.split(" bis ")
	if len(parts[0]) == 2:
		parts[0] += ':00'
	if 1 not in parts:
		parts.append(None)
	return (parts[0], parts[1])

def get_session_attendants(id):
	"""
		Get list of people who have attended a session
	"""
	global db
	url = 'http://ratsinformation.stadt-koeln.de/to0045.asp?__ctext=0&__ksinr=' + str(id)
	html = urllib2.urlopen(url).read()
	data = scrape("""
	{*
		<tr>
			<td><a href="kp0050.asp?__kpenr={{ [attendee].id|int }}&amp;grnr={{ [attendee].grnr|int }}">{{ [attendee].name }}</a></td>
			<td>{{ [attendee].organization }}</td>
			<td>{{ [attendee].function }}</td>
		</tr>
	*}
	""", html)
	persons = []
	attendants = []
	for row in data['attendee']:
		persons.append({
			'person_id': row['id'],
			'person_name': row['name'],
			'person_organization': row['organization']
		})
		attendants.append({
			'session_id': id,
			'person_id': row['id'],
			'attendance_function': row['function']
		})
	db.save_rows('people', persons, ['person_id'])
	db.save_rows('attendance', attendants, ['session_id', 'person_id'])

def get_committee_details(id):
	"""
		Get detail information on a committee (Sitzung)
	"""
	global db
	url = 'http://ratsinformation.stadt-koeln.de/kp0040.asp?__kgrnr=' + str(id)
	html = urllib2.urlopen(url).read()
	data = {}

	data['committee_title'] = scrape('''
		<h1 class="smc_h1">{{}}</h1>
		''', html)
	data['committee_id'] = int(id)
	db.save_rows('committees', data, ['committee_id'])

def is_session_in_db(id):
	global db
	result = db.get_rows('SELECT session_id FROM sessions WHERE session_id=%d' % id)
	if len(result) > 0:
		return True
	return False

def is_attachment_in_db(id):
	"""
		Returns true if the attachment with a given numeric ID is already in the database
	"""
	global db
	result = db.get_rows('SELECT attachment_id FROM attachments WHERE attachment_id=%d' % id)
	if len(result) > 0:
		return True
	return False


if __name__ == '__main__':
	db = DataStore(DBNAME, DBHOST, DBUSER, DBPASS)
	# get submission document details
	docs = db.get_rows('SELECT * FROM submissions WHERE submission_identifier IS NULL OR submission_identifier = "" ORDER BY RAND()')
	for doc in docs:
		get_document_details('submission', doc['submission_id'])

	# get request document details
	requests = db.get_rows('SELECT * FROM requests WHERE request_identifier IS NULL OR request_identifier = "" ORDER BY RAND()')
	for request in requests:
		get_document_details('request', request['request_id'])

	sys.exit()

	years = [2011, 2012, 2008, 2009, 2010]
	#years = shuffle([2008, 2009, 2010, 2011, 2012])
	months = shuffle(range(1,13))

	for year in years:
		for month in months:
			session_ids = get_session_ids(year, month)
			for session_id in session_ids:
				if not is_session_in_db(session_id):
					print "Jahr", year, ", Monat", month, ", Session " + str(session_id)
					get_session_details(session_id)
					get_session_attendants(session_id)

