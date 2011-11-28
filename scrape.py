#!/usr/bin/env python
# encoding: utf-8
"""
scrape.py

Created by Marian Steinbach on 2011-11-23.
"""

### Configuration

# Database
DBHOST = 'localhost'
DBUSER = 'root'
DBPASS = ''
DBNAME = 'cologne-ris'

# Base URL
BASEURL = 'http://ratsinformation.stadt-koeln.de/'

### End of configuration

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
			sql = 'INSERT IGNORE INTO ' + table +' ('+ ', '.join(thedict.keys()) +')'
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
				sql3 = ' ON DUPLICATE KEY UPDATE '
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
				if len(updates) > 0:
					sql3 += ", ".join(updates)
					sql += sql3
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
		u'unge\xe4ndert beschlossen': 'BESCHLOSSEN_UNVERAENDERT',
		u'ge\xe4ndert beschlossen': 'BESCHLOSSEN_GEAENDERT',
		u'Alternative beschlossen': 'BESCHLOSSEN_ALTERNATIVE',
		u'unter Vorbehalt beschlossen': 'BESCHLOSSEN_VORBEHALT',
		u'unge\xe4ndert empfohlen': 'EMPFOHLEN_UNVERAENDERT',
		u'Kenntnis genommen': 'KENNTNISNAHME',
		u'zur\xfcckgestellt': 'ZURUECKGESTELLT',
		u'Sache ist erledigt': 'ERLEDIGT',
		u'zur weiteren Bearbeitung in die Verwaltung \xfcberwiesen': 'UEBERWIESEN_VERWALTUNG',
		u'im ersten Durchgang verwiesen': 'UEBERWIESEN_ERSTERDURCHGANG',
		u'ohne Votum in nachfolgende Gremien': 'UEBERWIESEN_GREMIEN_OHNEVOTUM',
		u'verwiesen in nachfolgende Gremien (ohne R\xfccklauf)': 'UEBERWIESEN_GREMIEN_OHNERUECKLAUF',
		u'verwiesen in nachfolgende Gremien': 'UEBERWIESEN_GREMIEN',
		u'ohne Votum verwiesen mit erneuter Wiedervorlage': 'UEBERWIESEN_WIEDERVORLAGE_OHNEVOTUM',
		u'abgelehnt (in der Vorberatung)': 'ABGELEHNT_VORBERATUNG',
		u'endg\xfcltig abgelehnt': 'ABGELEHNT_ENTGUELTIG',
		u'endg\xfcltig zur\xfcckgezogen': 'ZURUECKGEZOGEN_ENTGUELTIG',
		u'\xdcbergang zum n\xe4chsten Tagesordnungspunkt': 'NAECHSTER_TAGESORDNUNGSPUNKT',
		u'mit \xc4nderungen empfohlen': 'EMPFOHLEN_GAENDERT',
	}
	if string in types:
		return types[string]
	print "ERROR: Unknown result type string", [string]
	sys.exit()

def attachment_role_string(string):
	"""
		Returns the correct normalized attachment role category
	"""
	types = {
		u'Abstimmung': 'ABSTIMMUNG',
		u'Mitteilung/Beantwortung Ausschuss': 'MITTEILUNG_AUSSCHUSS',
		u'Mitteilung / Beantwortung Ausschuss': 'MITTEILUNG_AUSSCHUSS',
		u'Mitteilung BV': 'MITTEILUNG_BV',
		u'Beantwortung einer m\xfcndl. Anfrage Ausschuss': 'MITTEILUNG_AUSSCHUSS',
		u'Mitteilung/Beantwortung BV': 'MITTEILUNG_BV',
		u'Mitteilung/Beantwortung Rat': 'MITTEILUNG_RAT',
		u'Mitteilung Ausschuss': 'MITTEILUNG_AUSSCHUSS',
		u'Mitteilungsvorlage': 'MITTEILUNGSVORLAGE',
		u'Beschlussvorlage': 'BESCHLUSSVORLAGE',
		u'Beschlussvorlage Rat': 'BESCHLUSSVORLAGE_RAT',
		u'Beschlussvorlage Ausschuss': 'BESCHLUSSVORLAGE_AUSSCHUSS',
		u'Beschlussvorlage Bezirksvertretung': 'BESCHLUSSVORLAGE_BEZIRKSVERTRETUNG',
		u'Antrag BV': 'ANTRAG_BV',
		u'Anfrage BV': 'ANFRAGE_BV',
		u'Dringlichkeitsvorlage Rat und Hauptausschuss': 'DRINGLICHKEITSVORLAGE_RAT_HAUPTAUSSCHUSS',
	}
	if string in types:
		return types[string]
	print "WARN: Unknown attachment type string", [string]
	return string

def get_committee_id_by_name(name):
	global db
	result = db.get_rows('SELECT committee_id FROM committees WHERE committee_title=%s' % name)
	if len(result) == 1:
		return result[0]['committee_id']

def get_session_ids(year, month):
	"""
		Get ids of all currently available sessions (Sitzungen)
	"""
	ids = []
	url = BASEURL + 'si0040.asp?__cmonat='+str(month)+'&__cjahr='+str(year)
	data = scrape("""
	{*
		<td><a href="to0040.asp?__ksinr={{ [ksinr]|int }}"></a></td>
	*}
	""", url=url)
	for item in data['ksinr']:
		ids.append(item)
	return ids

def get_session_detail_url(session_id):
	return BASEURL + 'to0040.asp?__ksinr=' + str(session_id)

def get_session_details(id):
	"""
		Get detail information on a session (Sitzung)
	"""
	global db
	url = get_session_detail_url(id)
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
	# TODO: Prüfe, ob das Gremium schon vollständig in der Datenbank ist und scrape nur bei Bedarf
	#if data['committee_id'] is not None and data['committee_id'] is not '':
	#	get_committee_details(data['committee_id'])
	get_agenda(id, html)

def get_agenda(session_id, html):
	"""
		Reads agenda items from session detail page HTML.

		We parse the HTML several times to get all details.
		- first, all agenda table rows are parsed to "all"
		- second, all agenda items with detail links
		  are captured to "linked"
		- third, all attachments are gatherd in "files"
		Then the structures are merged by agenda item number.
	"""
	global db
	html = html.replace('&nbsp;', ' ')
	html = html.replace('<br>', '; ')
	
	# 1. Öffentlichen Tagesordnungspunkte mit ID auslesen (immer zwei aufeinander folgende Tabellenzeilen)
	publicto = scrape('''
	{*
		<tr id="smc_contol_to_1_{{ [agendaitem].id|int }}">
			<td>{{ [agendaitem].f1 }}</td>
			<td>{{ [agendaitem].f2 }}</td>
			<td>{{ [agendaitem].f3 }}</td>
		</tr>
		<tr>
			<td>{{ [agendaitem].f4 }}</td>
			<td>{{ [agendaitem].f5 }}</td>
			<td>{{ [agendaitem].f6 }}</td>
		</tr>
	*}
	''', html)
	all_items_by_id = {}
	if 'agendaitem' in publicto and isinstance(publicto['agendaitem'], list):
		# Bereinigung
		for entry in publicto['agendaitem']:
			if 'id' not in entry:
				continue
			all_items_by_id[entry['id']] = { 
				'agendaitem_id': entry['id'],
				'agendaitem_public': 1,
				'agendaitem_identifier': None,
				'session_id': session_id,
				'agendaitem_result': None
			}
			if 'f1' in entry and entry['f1'] != '':
				all_items_by_id[entry['id']]['agendaitem_identifier'] = entry['f1']
			if 'f2' in entry and entry['f2'] != '':
				all_items_by_id[entry['id']]['agendaitem_subject'] = entry['f2']
			if 'f5' in entry and entry['f5'] != '' and entry['f5'].find('Ergebnis:') != -1:
				all_items_by_id[entry['id']]['agendaitem_result'] = result_string(entry['f5'].replace('Ergebnis: ', ''))
	
	# 2. Nichtöffentliche Tagesordnungspunkte mit ID lesen
	nonpublicto = scrape('''
	<h2 class="smc_h2">Nicht &ouml;ffentlicher Teil:</h2>
	{*
		<tr id="smc_contol_to_1_{{ [agendaitem].id|int }}">
			<td>{{ [agendaitem].f1 }}</td>
			<td>{{ [agendaitem].f2 }}</td>
		</tr>
	*}
	''', html)
	if nonpublicto is not None and ('agendaitem' in nonpublicto) and (nonpublicto['agendaitem'] is not None):
		if isinstance(nonpublicto['agendaitem'], list):
			for entry in nonpublicto['agendaitem']:
				if 'id' not in entry:
					continue
				all_items_by_id[entry['id']] = { 
					'agendaitem_id': entry['id'],
					'agendaitem_public': 0,
					'agendaitem_identifier': None,
					'session_id': session_id
				}
				if 'f1' in entry and entry['f1'] != '':
					all_items_by_id[entry['id']]['agendaitem_identifier'] = entry['f1']
				if 'f2' in entry and entry['f2'] != '':
					all_items_by_id[entry['id']]['agendaitem_subject'] = entry['f2']
	# Alle Tagesordnungspunkte in die Datenbank schreiben
	db.save_rows('agendaitems', all_items_by_id.values(), ['agendaitem_id'])
	
	# 3. Verlinkung zwischen Tagesordnungspunkten und Anträgen (requests) bzw. Vorlagen (submissions) auslesen
	linkedto = scrape('''
	{*
		<tr id="smc_contol_to_1_{{ [agendaitem].id|int }}">
			<td></td>
			<td>
				{*
					<a href="vo0050.asp?__kvonr={{ [agendaitem].[submissions].kvonr|int }}&amp;voselect={{ [agendaitem].[submissions].voselect|int }}">{{ [agendaitem].[submissions].subject }}</a>
				*}
				{*
					<a href="ag0050.asp?__kagnr={{ [agendaitem].[requests].kagnr|int }}&amp;voselect={{ [agendaitem].[requests].voselect|int }}">{{ [agendaitem].[requests].subject }}</a>
				*}
			</td>
		</tr>
	*}
	''', html)
	request_links = []
	submission_links = []
	if 'agendaitem' in linkedto and isinstance(linkedto['agendaitem'], list):
		for entry in linkedto['agendaitem']:
			if not 'id' in entry:
				continue
			if ('submissions' in entry and entry['submissions'] != []) or ('requests' in entry and entry['requests'] != []):
				if 'submissions' in entry:
					for doc in entry['submissions']:
						submission_links.append({'agendaitem_id': entry['id'], 'submission_id': doc['kvonr']})
				if 'requests' in entry:
					for doc in entry['requests']:
						request_links.append({'agendaitem_id': entry['id'], 'request_id': doc['kagnr']})
	# Alle Verknüfungen in die Datenbank schreiben
	db.save_rows('agendaitems2submissions', submission_links, ['agendaitem_id', 'submission_id'])
	db.save_rows('agendaitems2requests', request_links, ['agendaitem_id', 'request_id'])
	
	# 4. Links von Agendaitem-IDs zu Attachments auslesen
	attachmentto = scrape('''
	{*
		<tr id="smc_contol_to_1_{{ [agendaitem].id|int }}">
			<td/>
			<td/>
			<td>
				{*
					<a href="javascript:document.{{ [agendaitem].[docs1].formname }}.submit();">{{ [agendaitem].[docs1].linktitle }}</a>
				*}
			</td>
		</tr>
		<tr>
			<td/>
			<td/>
			<td>
				{*
					<a href="javascript:document.{{ [agendaitem].[docs2].formname }}.submit();">{{ [agendaitem].[docs2].linktitle }}</a>
				*}
			</td>
		</tr>
	*}
	''', html)
	attachements_by_id = {} # wird hier aufgefüllt
	if 'agendaitem' in attachmentto and isinstance(attachmentto['agendaitem'], list):
		# Bereinigung
		for entry in attachmentto['agendaitem']:
			if not 'id' in entry:
				continue
			if ('docs1' in entry and entry['docs1'] != []) or ('docs2' in entry and entry['docs2'] != []):
				attachements_by_id[entry['id']] = []
				if 'docs1' in entry:
					for doc in entry['docs1']:
						attachements_by_id[entry['id']].append(doc)
				if 'docs2' in entry:
					for doc in entry['docs2']:
						attachements_by_id[entry['id']].append(doc)
	new_attachment_formnames = []
	for id in attachements_by_id:
		for attachment in attachements_by_id[id]:
			#print id, attachment
			if 'formname' in attachment and 'linktitle' in attachment:
				role = attachment_role_string( re.sub(r'\s+\[[^\]]+\]', '', attachment['linktitle'])
				if role != 'Abstimmung':
					dataset = {
						'agendaitem_id': id,
						'attachment_id': int(attachment['formname'][3:]),
						'attachment_role': attachment['linktitle'])
					}
					db.save_rows('agendaitems2attachments', dataset, ['agendaitem_id', 'attachment_id'])
					if not is_attachment_in_db(int(attachment['formname'][3:])):
						new_attachment_formnames.append(attachment['formname'])
	if len(new_attachment_formnames) > 0:
		get_attachments(get_session_detail_url(session_id), new_attachment_formnames)
	# TODO: Attachments außerhalb der Tagesordnung erfassen (Einladung, Niederschrift)

	


def is_document_complete(dtype, id):
	"""
		Checks whether the document (request or submission) with the given id
		is complete in the database or not
	"""
	global db
	sql = False
	if dtype == 'request':
		sql = '''SELECT request_id FROM requests 
			WHERE request_id=%s 
			AND committees IS NOT NULL
			AND request_date IS NOT NULL
			AND request_identifier IS NOT NULL
			AND request_subject IS NOT NULL'''
	if dtype == 'submission':
		sql = '''SELECT submission_id FROM submissions 
			WHERE submission_id=%s 
			AND submission_type IS NOT NULL
			AND submission_date IS NOT NULL
			AND submission_identifier IS NOT NULL
			AND submission_subject IS NOT NULL'''
	if sql:
		result = db.get_rows(sql % id)
		if len(result) == 1:
			return True
		return False

def get_document_details(dtype, id):
	"""
		Get details on a request (Antrag) or submission (Vorlage)
	"""
	global db
	data = {}
	prefix = ''
	if dtype == 'request':
		url = BASEURL + 'ag0050.asp?__kagnr=' + str(id)
		prefix = 'request_'
	elif dtype == 'submission':
		url = BASEURL + 'vo0050.asp?__kvonr=' + str(id)
		prefix = 'submission_'
	data[prefix + 'id'] = id
	html = urllib2.urlopen(url).read()

	html = html.replace('<br>', ' ')	

	data[prefix + 'identifier'] = scrape('''
		<tr><td>Name:</td><td>{{}}</td></tr>
		''', html)
	data[prefix + 'date'] = scrape('''
		<tr><td>Datum:</td><td>{{}}</td></tr>
		''', html)
	data[prefix + 'subject'] = scrape('''
		<tr><td>Betreff:</td><td>{{}}</td></tr>
		''', html)
	if dtype == 'request':
		committee = scrape('''
			<tr><td>Gremien:</td><td>{{}}</td></tr>
			''', html)
		committee_id = get_committee_id_by_name(committee)
		if committee_id is not None:
			data['committee_id'] = committee_id
	else:
		data[prefix + 'type'] = scrape('''
			<tr><td>Art:</td><td>{{}}</td></tr>
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
		content = None
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
				if content is not None and content is not False:
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
	try:
		parser.set_document(doc)
	except:
		# occurs for example if document is encrypted
		return False
	try:
		doc.set_parser(parser)
	except:
		return False
	try:
		doc.initialize('')
	except:
		return False
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
	url = BASEURL + 'to0045.asp?__ctext=0&__ksinr=' + str(id)
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
	url = BASEURL + 'kp0040.asp?__kgrnr=' + str(id)
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
		Returns true if the attachment with a given numeric ID is in the database
	"""
	global db
	result = db.get_rows('SELECT attachment_id FROM attachments WHERE attachment_id=%d' % id)
	if len(result) > 0:
		return True
	return False

def scrape_incomplete_datasets():
	global db
	# get submission document details for entries created before
	docs = db.get_rows('SELECT * FROM submissions WHERE submission_identifier IS NULL OR submission_identifier = "" ORDER BY RAND()')
	for doc in docs:
		if not is_document_complete('submission', doc['submission_id']):
			get_document_details('submission', doc['submission_id'])
	# get request document details
	requests = db.get_rows('SELECT * FROM requests WHERE request_identifier IS NULL OR request_identifier = "" ORDER BY RAND()')
	for request in requests:
		if not is_document_complete('request', request['request_id']):
			get_document_details('request', request['request_id'])

def scrape_new_sessions():
	years = [2011, 2012, 2008, 2009, 2010]
	#years = shuffle([2008, 2009, 2010, 2011, 2012])
	months = shuffle(range(1,13))
	for year in years:
		for month in months:
			session_ids = get_session_ids(year, month)
			for session_id in session_ids:
				#if not is_session_in_db(session_id):
					print "Jahr", year, ", Monat", month, ", Session " + str(session_id)
					get_session_details(session_id)
					get_session_attendants(session_id)

def scrape_all_sessions():
	years = [2011, 2010, 2009, 2008, 2012]
	#years = shuffle([2008, 2009, 2010, 2011, 2012])
	months = shuffle(range(1,13))
	for year in years:
		for month in months:
			session_ids = get_session_ids(year, month)
			for session_id in session_ids:
				print "Jahr", year, ", Monat", month, ", Session " + str(session_id)
				get_session_details(session_id)
				get_session_attendants(session_id)


if __name__ == '__main__':
	db = DataStore(DBNAME, DBHOST, DBUSER, DBPASS)
	
	scrape_all_sessions()
	
	# Clean leftovers from last run
	scrape_incomplete_datasets()
	
	# Get new datasets
	scrape_new_sessions()
	
	# Clean up again
	scrape_incomplete_datasets()



