#!/usr/bin/env python
# encoding: utf-8
"""
Scraper für das Kölner Ratsinformationssystem

Copyright (c) 2012 Marian Steinbach

Hiermit wird unentgeltlich jeder Person, die eine Kopie der Software und
der zugehörigen Dokumentationen (die "Software") erhält, die Erlaubnis
erteilt, sie uneingeschränkt zu benutzen, inklusive und ohne Ausnahme, dem
Recht, sie zu verwenden, kopieren, ändern, fusionieren, verlegen
verbreiten, unterlizenzieren und/oder zu verkaufen, und Personen, die diese
Software erhalten, diese Rechte zu geben, unter den folgenden Bedingungen:

Der obige Urheberrechtsvermerk und dieser Erlaubnisvermerk sind in allen
Kopien oder Teilkopien der Software beizulegen.

Die Software wird ohne jede ausdrückliche oder implizierte Garantie
bereitgestellt, einschließlich der Garantie zur Benutzung für den
vorgesehenen oder einen bestimmten Zweck sowie jeglicher Rechtsverletzung,
jedoch nicht darauf beschränkt. In keinem Fall sind die Autoren oder
Copyrightinhaber für jeglichen Schaden oder sonstige Ansprüche haftbar zu
machen, ob infolge der Erfüllung eines Vertrages, eines Delikts oder anders
im Zusammenhang mit der Software oder sonstiger Verwendung der Software
entstanden.
"""

import config
import sys
import os
import random
import re
import urllib2
from scrapemark import scrape
import mechanize
from datastore import DataStore
from queue import Queue
import subprocess
from optparse import OptionParser
import datetime
import hashlib
import json


def shuffle(l):
    """Randomizes list order and return list"""
    randomly_tagged_list = [(random.random(), x) for x in l]
    randomly_tagged_list.sort()
    return [x for (r, x) in randomly_tagged_list]


def result_string(string):
    """
    Gibt für die vielen vorhandenen Schreibweisen für das Resultat eines
    Antrags, einer Anfrage etc. einen normalisierten String aus.
    Der übergebene Parameter muss ein Unicode-String sein.
    Ist für den übergebenen String keine Schreibweise hinterlegt, wird
    das Programm mit einer Fehlermeldung abgebrochen.
    """
    if string is not None and string != '':
        return config.RESULT_TYPES[string]


def cleanup_identifier_string(string):
    """Bereinigt eine Dokumenten-ID und gibt sie zurück."""
    if string is None:
        return string
    return string.replace(' ', '')


def parse_formname(formname):
    """
    Extrahiert aus einem Formularnamen wie 'pdf12345' den Teil 'pdf' und
    '12345' und gibt beide Teile als Tupel zurück
    """
    if formname is not None:
        matches = re.match(r'^([a-z]+)([0-9]+)$', formname)
        if matches is not None:
            return (matches.group(1), int(matches.group(2)))
    return None


def get_committee_id_by_name(cname):
    """
    Holt ein Gremium anhand des Namens aus der Datenbank und gibt die ID zurück
    """
    global db
    result = db.get_rows('SELECT committee_id FROM committees WHERE committee_title="%s"' % cname)
    if len(result) == 1:
        return result[0]['committee_id']


def get_session_ids(year, month):
    """
    Scrapet alle publizierten Sitzungen zum gegebenen Monat des gegebenen
    Jahres und gibt die Sitzungs-IDs als Liste zurück.
    """
    ids = []
    url = config.BASEURL + (config.URI_CALENDAR % (month, year))
    print "Lade Sitzungen für Jahr", year, ", Monat", month
    data = scrape("""
    {*
        <td><a href="to0040.asp?__ksinr={{ [ksinr]|int }}"></a></td>
    *}
    """, url=url)
    for item in data['ksinr']:
        ids.append(item)
    if options.verbose:
        print "Anzahl gefundene Sitzungen:", len(ids)
    return ids


def get_session_detail_url(session_id):
    """Gibt anhand einer Sitzungs-ID die Detail-URL zurück"""
    return config.BASEURL + (config.URI_SESSION_DETAILS % session_id)


def get_session_details(id):
    """
    Scrapet Details zur Sitzung mit der gegebenen ID
    und legt sie in der Datenbank ab.
    """
    global db
    url = get_session_detail_url(id)
    print "Lade Sitzung", id, url
    html = urllib2.urlopen(url).read()
    data = {}

    data['session_id'] = id
    data['session_title'] = scrape('<title>{{}}</title>', html)

    data['committee_id'] = scrape('<a href="kp0040.asp?__kgrnr={{}}"', html)

    data['session_identifier'] = cleanup_identifier_string(scrape('''
        <tr><td>Sitzung:</td><td>{{}}</td></tr>
        ''', html))

    data['session_location'] = scrape('''
        <tr><td>Raum:</td><td>{{}}</td></tr>
        ''', html)

    data['session_description'] = scrape('''
        <tr><td>Bezeichnung:</td><td>{{}}</td></tr>
        ''', html)

    date_time = scrape('''
        <tr><td>Datum und Uhrzeit:</td><td>{{ datum }}, {{zeit}}&nbsp;Uhr</td></tr>
        ''', html)

    if date_time['datum'] is not None:
        data['session_date'] = get_date(date_time['datum'].strip())
    else:
        print >> sys.stderr, "ERROR: No date found for Session " + str(id)
    (starttime, endtime) = get_start_end_time(date_time['zeit'])
    data['session_time_start'] = starttime
    data['session_time_end'] = endtime

    if (data['committee_id'] is not None) and (data['committee_id']
        is not '') and not (is_committee_in_db(data['committee_id'])):
        get_committee_details(data['committee_id'])
    get_agenda_and_attachments(id, html)
    get_session_attendants(id)
    if not options.simulate:
        db.save_rows('sessions', data, ['session_id'])


def get_agenda_and_attachments(session_id, html):
    """
    Liest die Tagesordnungspunkte aus dem HTML der Sitzungs-
    Detailseite und speichert diese sowie die verlinkten Anhänge.
    Das HTML wird mehrmals geparst, um alle Details zu bekommen.
    - Beim ersten Mal werden alle öffentlichen Punkte der Tagesordnungs-
      Tabelle in "publicto" abgelegt.
    - Das gleiche geschieht mit den nicht-öffentlichen Punkten in "nonpublicto"
    - Beim nächsten Durchgang werden alle Zeilen, die einen Link
      enthalten, in "linkedto" gespeichert.
    - Beim dritten Durchgang werden alle Zeilen mit Dateianhängen
      in "files" gesammelt.
    Zuletzt werden die drei Strukturen anhand der Nummer des
    Tagesordnungspunktes vereint.

    Beispiel einer Sitzungs-Detailseite:
    http://ratsinformation.stadt-koeln.de/to0040.asp?__ksinr=8361
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
            if ('f5' in entry and entry['f5'] != ''
                and entry['f5'] is not None and
                entry['f5'].find('Ergebnis:') != -1):
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
    if not options.simulate:
        db.save_rows('agendaitems', all_items_by_id.values(), ['agendaitem_id'])

    submission_links = scrape('''
        {*
            <a href="vo0050.asp?__kvonr={{ []|int }}&amp;voselect=''' + str(session_id) + '''">
        *}
        ''', html)
    request_links = scrape('''
        {*
            <a href="vo0050.asp?__kagnr={{ []|int }}&amp;voselect=''' + str(session_id) + '''">
        *}
        ''', html)
    if options.verbose:
        print "Gefundene Vorlagen (" + str(len(submission_links)) + "):", submission_links
        print "Gefundene Anträge (" + str(len(request_links)) + "):", request_links

    # in Queue ablegen
    if submission_links is not None:
        for submission_id in submission_links:
            submission_queue.add(submission_id)
    if request_links is not None:
        for request_id in request_links:
            request_queue.add(request_id)
    if options.verbose:
        print "Vorlagen in Warteschlange:", len(submission_queue)
        print "Anträge in Warteschlange:", len(request_queue)

    # Attachments innerhalb der Tagesordnung erfassen,
    # nur um sie hier nicht zu scrapen
    attachments_to = scrape('''
        {*
        <table class="smccontenttable">
            {*
                <a href="javascript:document.{{ [] }}.submit();"></a>
            *}
        </table>
        *}
    ''', html)
    if options.verbose:
        print "Anhänge in Tagesordnung:", len(attachments_to)

    # 5. Alle Attachments finden, um Attachments außerhalb der Tagesordnung
    #    zu erfassen (Einladung, Niederschrift, Wortprotokoll)
    attachments_all = scrape('''
    {*
        <a href="javascript:document.{{ [].formname }}.submit();">{{ [].linktitle }}</a>
    *}
    ''', html)
    if options.verbose:
        print "Alle Anhänge:", len(attachments_all)
    attachments_queue = []
    if attachments_all is not None:
        for att in attachments_all:
            if att['formname'] not in attachments_to:
                # Attachment gehört zu keinem Tagesordnungspunkt, also abrufen
                attachments_queue.append(att['formname'])
                (doctype, docid) = parse_formname(att['formname'])
                dataset = {
                    'session_id': session_id,
                    'attachment_id': docid,
                    'attachment_role': att['linktitle']
                }
                if not options.simulate:
                    db.save_rows('sessions2attachments', dataset, ['session_id', 'attachment_id'])
        if len(attachments_queue) > 0:
            if options.verbose:
                print "Attachments zum Download von", get_session_detail_url(session_id), ":", attachments_queue
            get_attachments(get_session_detail_url(session_id), attachments_queue)


def is_document_complete(dtype, id):
    """
    Prüft, ob ein Dokument ("request"/"submission") in der Datenbank
    vorhanden ist und die entscheidenden Felder gesetzt sind.
    """
    global db
    sql = False
    if dtype == 'request':
        sql = '''SELECT request_id FROM requests
            WHERE request_id=%s
            AND committee_id IS NOT NULL
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
    Scrapet die Detailseite eines Antrags (request) oder einer
    Vorlage (submission)
    """
    if int(id) == 0:
        print >> sys.stderr, "Fehler: Dokumenten-ID ist 0."
        return
    data = {}
    prefix = ''
    if dtype == 'request':
        url = config.BASEURL + (config.URI_REQUEST_DETAILS % id)
        prefix = 'request_'
        print "Lade Antrag", id, url
    elif dtype == 'submission':
        url = config.BASEURL + (config.URI_SUBMISSION_DETAILS % id)
        prefix = 'submission_'
        print "Lade Vorlage", id, url
    data[prefix + 'id'] = id
    html = urllib2.urlopen(url).read()
    html = html.replace('<br>', '; ')
    data[prefix + 'identifier'] = cleanup_identifier_string(scrape('''
        <tr><td>Name:</td><td>{{}}</td></tr>
        ''', html))
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

    # Lade Anhänge oberhalb der Beratungen
    attachments = scrape('''
        <table class="smcdocbox">
        {*
            <a href="javascript:document.{{ [].formname }}.submit();">{{ [].linktitle }}</a>
        *}
        </table>
        ''', html)
    if options.verbose:
        print "Anhänge:", json.dumps(attachments, indent=4)
    if attachments is not None:
        forms = []
        for form in attachments:
            forms.append(form['formname'])
            (doctype, docid) = parse_formname(form['formname'])
            entry = {
                'attachment_id': docid,
                prefix + 'id': data[prefix + 'id'],
                'attachment_role': form['linktitle']
            }
            if not options.simulate:
                db.save_rows(dtype + 's2attachments', entry, ['attachment_id', prefix + 'id'])
        get_attachments(url, forms)

    # post-process
    if data[prefix + 'date'] is not None and data[prefix + 'date'] != '':
        data[prefix + 'date'] = get_date(data[prefix + 'date'])

    if dtype == 'request':
        if not options.simulate:
            db.save_rows('requests', data, ['request_id'])
    elif dtype == 'submission':
        if not options.simulate:
            db.save_rows('submissions', data, ['submission_id'])

    # Auslesen der bisherigen Beratungsfolge
    # Hier bekommen wir Informationen über die Verknüpfung zwischen diesem Dokument
    # und Tagesordnungspunkten, in denen es behandelt wurde (agendaitems2submissions bzw.
    # agendaitems2requests). Außerdem werden die Tagesordnungspunkte selbst angelegt.
    top_past = scrape('''
        {*
            <tr>
                <td><a href="to0040.asp?__ksinr={{ [].session_id|int }}&amp;toselect={{ [].agendaitem_id }}">{{ [].date }}</a></td>
                <td>{{ [].committee_name }}</td>
                <td>{{ [].agendaitem_identifier }}</td>
                <td>{{ [].role }}</td>
                <td>{{ [].agendaitem_result }}</td>
                <td/>
            </tr>
        *}
        ''', html)
    #debug
    if options.verbose:
        print "Beratungsfolge Vergangenheit: %d Eintraege: %s" % (len(top_past),
            json.dumps(top_past, indent=4, sort_keys=True))

    # Nachverarbeitung der Tagesordnungspunkte
    if top_past is not None and len(top_past) > 0:
        insert_tops = []
        for top in top_past:
            newtop = {
                'agendaitem_id': int(top['agendaitem_id']),
                'session_id': int(top['session_id']),
                'agendaitem_identifier': top['agendaitem_identifier'],
                'agendaitem_result': result_string(top['agendaitem_result'])
            }
            insert_tops.append(newtop)
        # Tagesordnungspunkte schreiben
        if not options.simulate:
            db.save_rows('agendaitems', insert_tops, ['agendaitem_id'])
        # Verknuepfungen schreiben
        table_name = 'agendaitems2%ss' % dtype  # agendaitems2submissions oder agendaitems2requests
        docid_field_name = '%s_id' % dtype      # submission_id oder request_id
        for top in insert_tops:
            dataset = {
                'agendaitem_id': int(top['agendaitem_id']),
                docid_field_name: id
            }
            if not options.simulate:
                db.save_rows(table_name, dataset, ['agendaitem_id', docid_field_name])


def save_temp_file(data):
    """
    Speichert die übergebenen Daten in einer temporären Datei
    und gibt den Pfad zurück
    """
    sha = hashlib.sha1(data).hexdigest()
    if not os.path.exists(config.TMP_FOLDER):
        os.makedirs(config.TMP_FOLDER)
    path = config.TMP_FOLDER + os.sep + sha
    f = open(path, 'w')
    f.write(data)
    f.close()
    #print "save_temp_file(): Abgelegt in", path
    return path


def file_sha1(path):
    """
    Erzeugt SHA1 Prüfsumme der Datei
    """
    sha = hashlib.sha1()
    content = open(path, 'r').read()
    sha.update(content)
    hexdig = sha.hexdigest()
    return hexdig


def file_type(path):
    """
    Gibt den Dateityp (MIME Type) zurück, den fileutils
    zum Inhalt der Datei feststellen.
    """
    cmd = config.FILE_CMD + ' ' + path
    output, error = subprocess.Popen(
            cmd.split(' '), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE).communicate()
    if error != '':
        print >> sys.stderr, "Fehler: get_filetype()", error
    return output.strip()


def get_attachments(url, forms_list):
    """
    Scrapet von der Seite mit der gegebenen URL alle Dokumente, die
    über die übergebene Formular-Liste gekennzeichnet werden.
    """
    ret = {}
    br = mechanize.Browser()
    try:
        br.open(url)
    except:
        print >> sys.stderr, "Fehler: URL", url, " konnte nicht geoeffnet werden."
        return None
    if options.verbose:
        print "Anzahl Anhänge zu laden:", len(forms_list)
    for form in forms_list:
        print "Lade Anhang " + form
        (doctype, attachment_id) = parse_formname(form)
        content = None
        br.select_form(name=form)
        response = br.submit()
        data = response.read()
        STATS['bytes_loaded'] += len(data)
        headers = response.info()
        if response.code == 200:
            # Dict für die Datenbank
            ret[attachment_id] = {
                'attachment_id': attachment_id,
                'attachment_mimetype': headers['content-type'].lower().decode('utf-8'),
                'attachment_size': len(data),
                'attachment_lastmod': datetime.datetime.utcnow().isoformat(' '),
            }
            if 'Content-Disposition' in headers:
                ret[attachment_id]['attachment_filename'] = headers['Content-Disposition'].split('filename=')[1].decode('utf-8')
            STATS['attachments_loaded'] += 1
            # Datei erst mal temporaer ablegen
            temp_path = save_temp_file(data)
            ret[attachment_id]['sha1_checksum'] = file_sha1(temp_path)
            # Datei prüfen
            ftype = file_type(temp_path)
            if ftype != ret[attachment_id]['attachment_mimetype']:
                print >> sys.stderr, "Fehler: MIME-Type der geladenen Datei entspricht nicht dem HTTP-Header", ret[attachment_id]['attachment_mimetype']
            # TODO: file_type mit doctype abgleichen
            # Feststellen, ob Datei schon existiert
            folder = get_cache_path(form)
            full_filepath = folder + os.sep + form + '.' + doctype
            overwrite = True
            if os.path.exists(full_filepath):
                # Datei nicht austauschen, wenn identisch
                old_stat = os.stat(full_filepath)
                new_stat = os.stat(temp_path)
                if old_stat.st_size == new_stat.st_size:
                    if ret[attachment_id]['sha1_checksum'] == file_sha1(full_filepath):
                        overwrite = False
                        if options.verbose:
                            print "Datei", full_filepath, "bleibt unverändert"
                    else:
                        if options.verbose:
                            print "Datei", full_filepath, "wird überschrieben (verschiedene Prüfsumme)"
                        STATS['attachments_replaced'] += 1
                else:
                    if options.verbose:
                        print "Datei", full_filepath, "wird überschrieben (verschiedene Dateigröße)"
                    STATS['attachments_replaced'] += 1
            else:
                if options.verbose:
                    print "Datei", full_filepath, "ist neu"
                STATS['attachments_new'] += 1
            if overwrite:
                # Temp-Datei an ihren endgültigen Ort bewegen
                if not os.path.exists(folder):
                    os.makedirs(folder)
                if not options.simulate:
                    os.rename(temp_path, full_filepath)
                else:
                    os.remove(temp_path)
            if os.path.exists(temp_path):
                os.remove(temp_path)
                if ret[attachment_id]['attachment_mimetype'] == 'application/pdf':
                    # PDF-Inhalt auslesen
                    content = get_text_from_pdf(full_filepath)
                    if content is not None and content is not False:
                        ret[attachment_id]['attachment_content'] = content
                # Objekt in die Datenbank schreiben
                if not options.simulate:
                    db.execute("DELETE FROM attachments WHERE attachment_id=%s", [attachment_id])
                    if options.verbose:
                        print "Schreibe Eintrag attachment_id=%d in Tabelle 'attachments'" % attachment_id
                    db.save_rows('attachments', ret[attachment_id], ['attachment_id'])
        else:
            print >> (sys.stderr, "Fehler: Fehlerhafter HTTP Antwortcode",
                response.code)
        try:
            br.back()
        except:
            print >> sys.stderr, "Fehler: br.back()"
            return None
    return ret


def get_date(string):
    """
    Normalisiert Datumsangaben wie '1. Februar 2010' zu
    ISO-Schreibweise '2010-02-01'
    """
    months = {'Januar': 1, 'Februar': 2, 'März': 3, u'M\xe4rz': 3, 'April': 4, 'Mai': 5,
        'Juni': 6, 'Juli': 7, 'August': 8, 'September': 9, 'Oktober': 10,
        'November': 11, 'Dezember': 12, 'Jan': 1, 'Feb': 2, 'Mrz': 3,
        'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10,
        'Nov': 11, 'Dez': 12}
    result = re.match(r'([0-9]+)\.\s+([^\s]+)\s+([0-9]{4})', string)
    if result is not None:
        day = int(result.group(1))
        mkey = result.group(2).encode('utf-8')
        if mkey in months:
            month = months[result.group(2).encode('utf-8')]
        else:
            print >> sys.stderr, "Fehler: Falsches Datumsformat:", string
            return None
        year = int(result.group(3))
        return "%d-%02d-%02d" % (year, month, day)


def get_start_end_time(string):
    """
    Normalisiert Anfangs- und End-Zeitangabe zu ISO-Zeit-Tupel.
    Z.B. '15 bis 16:25' => ('15:00', '16:25')
    """
    parts = string.split(" bis ")
    if len(parts[0]) == 2:
        parts[0] += ':00'
    if 1 not in parts:
        parts.append(None)
    return (parts[0], parts[1])


def get_session_attendants(id):
    """
    Scrapet die Liste der (eingeladenen) Teilnehmer einer Sitzung
    """
    global db
    url = config.BASEURL + (config.URI_ATTENDANTS % id)
    print "Lade Anwesenheitsliste", url
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
    if not options.simulate:
        db.save_rows('people', persons, ['person_id'])
        db.save_rows('attendance', attendants, ['session_id', 'person_id'])


def is_committee_in_db(committee_id):
    """Prüft, ob das Gremium mit der ID in der Datenbank vorhanden ist."""
    global db
    result = db.get_rows('SELECT committee_id FROM committees WHERE committee_id=%d' % int(committee_id))
    if len(result) > 0:
        return True
    return False


def get_committee_details(id):
    """
    Scrapet Details zu einem Gremium
    """
    global db
    url = config.BASEURL + (config.URI_COMMITTEE % int(id))
    print "Lade Gremium", url
    html = urllib2.urlopen(url).read()
    data = {}

    data['committee_title'] = scrape('''
        <h1 class="smc_h1">{{}}</h1>
        ''', html)
    data['committee_id'] = int(id)
    if not options.simulate:
        db.save_rows('committees', data, ['committee_id'])


def is_session_in_db(id):
    """Prüft, ob die Sitzung in der Datenbank vorhanden ist."""
    global db
    result = db.get_rows('SELECT session_id FROM sessions WHERE session_id=%d' % id)
    if len(result) > 0:
        return True
    return False


def is_attachment_in_db(id):
    """Prüft, ob das Attachment in der Datenbank ist."""
    global db
    result = db.get_rows('SELECT attachment_id FROM attachments WHERE attachment_id=%d' % id)
    if len(result) > 0:
        return True
    return False


def get_cache_path(formname):
    """
    Ermittelt anhand des Formularnamens wie "pdf12345" den Pfad
    des Ordners zum Speichern der Datei
    """
    firstfolder = formname[-1]     # letzte Ziffer
    secondfolder = formname[-2:-1]  # vorletzte Ziffer
    ret = (config.ATTACHMENTFOLDER + os.sep + str(firstfolder) + os.sep +
        str(secondfolder))
    return ret


def get_text_from_pdf(path):
    """Extrahiere den Text aus einer PDF-Datei"""
    text = ''
    cmd = config.PDFTOTEXT_CMD + ' -enc UTF-8 ' + path + ' -'
    text, error = subprocess.Popen(
        cmd.split(' '), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE).communicate()
    if error is not None and error != '':
        print >> sys.stderr, "FEHLER bei get_text_from_pdf()", path
        print >> sys.stderr, error
    if text == '':
        return None
    text = text.strip()
    text = text.decode('utf-8')
    return text


def scrape_incomplete_datasets():
    """
    Diese Funktion soll dazu dienen, unvollständige Datensätze in der Datenbank
    zu vervollständigen.
    """
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


def scrape_sessions(years, months):
    """
    Mit dieser Funktion werden gezielt die Sitzungen aus einem bestimmten
    Zeitraum gescrapet. Der erste Parameter ist eine Liste mit Jahren,
    der zweite eine Liste mit Monaten (jeweils in Zahlen).
    """
    print "Scrape Jahr(e)", years, ", Monate", months
    for year in years:
        for month in months:
            session_ids = get_session_ids(year, month)
            for session_id in session_ids:
                if options.verbose:
                    print "Jahr", year, ", Monat", month, ", Session " + str(session_id)
                get_session_details(session_id)


def scrape_from_queue():
    """
    Arbeitet die session_queue, submission_queue, request_queue ab. Damit
    werden Dokumente und Sitzungen, die zuvor in die Warteschlange gelegt wurden,
    gescrapet.
    """
    while session_queue.has_next():
        session_id = session_queue.get()
        get_session_details(session_id)
    while submission_queue.has_next():
        submission_id = submission_queue.get()
        if options.verbose:
            print "Scrape Vorlage aus Warteschlange:", submission_id, ", verbleiben", len(submission_queue)
        get_document_details('submission', submission_id)
    while request_queue.has_next():
        request_id = request_queue.get()
        if options.verbose:
            print "Scrape Antrag aus Warteschlange:", request_id, ", verbleiben", len(request_queue)
        get_document_details('request', request_id)


def list_option(s):
    """Gibt string als Liste zurück. Seperator: Komma"""
    if s is None or s is '':
        return []
    return s.split(',')


def print_stats():
    """
    Simple Statistik-Ausgabe
    """
    for k in STATS.keys():
        print k, ': ', STATS[k]

if __name__ == '__main__':

    # Hier drin werden Statistiken gesammelt
    STATS = {
        'bytes_loaded': 0,
        'attachments_loaded': 0,
        'attachments_new': 0,
        'attachments_replaced': 0
    }

    # Queue für abzurufende Vorlagen, Anträge und Sessions
    submission_queue = Queue()
    request_queue = Queue()
    session_queue = Queue()

    parser = OptionParser()
    parser.add_option("-y", "--years", dest="years",
                      default=str(datetime.date.today().year),
                      help="Jahre, getrennt durch Komma")
    parser.add_option("-m", "--months", dest="months",
                      default=str(datetime.date.today().month),
                      help="Monate, getrennt durch Komma")
    parser.add_option("-s", "--simulate", dest="simulate", default=False,
                      action="store_true", help="nur simulieren, keine Daten schreiben")
    parser.add_option("-v", "--verbose", action="store_true", default=False,
                      help="Ausfuehrliche Ausgabe", dest="verbose")
    parser.add_option("--session", help="Numerische ID einer einzelnen Sitzung, die gescraped werden soll",
                      dest="session_id", type="int")
    parser.add_option("--submission", help="Numerische ID einer einzelnen Vorlage, die gescraped werden soll",
                      dest="submission_id", type="int")
    parser.add_option("--request", help="Numerische ID eines einzelnen Antrags, der gescraped werden soll",
                      dest="request_id", type="int")
    parser.add_option("--database", help="Name der zu verwendenden Datenbank", dest="database")
    (options, args) = parser.parse_args()

    # Monate und Jahre in Listen umwandeln
    years = list_option(options.years)
    months = list_option(options.months)

    dbname = config.DBNAME
    if options.database:
        dbname = options.database
    db = DataStore(dbname, config.DBHOST, config.DBUSER, config.DBPASS)

    if options.session_id:
        get_session_details(options.session_id)
    elif options.submission_id:
        get_document_details('submission', options.submission_id)
    elif options.request_id:
        get_document_details('request', options.request_id)
    else:
        scrape_sessions(years, months)

    scrape_from_queue()
    print_stats()
