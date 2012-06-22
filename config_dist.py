#!/bin/env python
# coding: utf-8

# Database settings
DBHOST = 'localhost'
DBUSER = 'risscraper'
DBPASS = 'risscraper'
DBNAME = 'cologne-ris'

# Basis-URL (mit / am Ende)
BASEURL = 'http://buergerinfo.halle.de/'

# URL-Format für Sitzungskalender
URI_CALENDAR = 'si0040.asp?__cmonat=%d&__cjahr=%d'
# URL-Format für Sitzungs-Detailseiten
URI_SESSION_DETAILS = 'to0040.asp?__ksinr=%d'
# URL-Format für Antrags-Detailseite
URI_REQUEST_DETAILS = 'ag0050.asp?__kagnr=%d'
# URL-Format für Vorlagen-Detailseite
URI_SUBMISSION_DETAILS = 'vo0050.asp?__kvonr=%d'
# URL-Format für Sitzungs-Teilnehmer
URI_ATTENDANTS = 'to0045.asp?__ctext=0&__ksinr=%d'
# URL-Format für Gremium-Details
URI_COMMITTEE = 'kp0040.asp?__kgrnr=%d'

# Verzeichnis für die Ablage von herunter geladenen Dateien
ATTACHMENTFOLDER = 'attachments'

# Verzeichnis für temporäre Dateien
TMP_FOLDER = 'tmp'

# Pfad zu pdftotext (xpdf)
PDFTOTEXT_CMD = '/usr/bin/pdftotext'

# Aufruf von file (fileutils) mit MimeType-Ausgabe
FILE_CMD = '/usr/bin/file -b --mime-type'

# Mapping von Schreibweisen zu normalisierten Ergebnis-Typen
RESULT_TYPES = {
    u'unge\xe4ndert beschlossen': 'BESCHLOSSEN_UNVERAENDERT',
    u'ge\xe4ndert beschlossen': 'BESCHLOSSEN_GEAENDERT',
    u'Alternative beschlossen': 'BESCHLOSSEN_ALTERNATIVE',
    u'unter Vorbehalt beschlossen': 'BESCHLOSSEN_VORBEHALT',
    u'unge\xe4ndert empfohlen': 'EMPFOHLEN_UNVERAENDERT',
    u'Kenntnis genommen': 'KENNTNISNAHME',
    u'zur\xfcckgestellt': 'ZURUECKGESTELLT',
    u'Sache ist erledigt': 'ERLEDIGT',
    u'zur weiteren Bearbeitung in die Verwaltung \xfcberwiesen':
        'UEBERWIESEN_VERWALTUNG',
    u'im ersten Durchgang verwiesen': 'UEBERWIESEN_ERSTERDURCHGANG',
    u'ohne Votum in nachfolgende Gremien': 'UEBERWIESEN_GREMIEN_OHNEVOTUM',
    u'verwiesen in nachfolgende Gremien (ohne R\xfccklauf)':
        'UEBERWIESEN_GREMIEN_OHNERUECKLAUF',
    u'verwiesen in nachfolgende Gremien': 'UEBERWIESEN_GREMIEN',
    u'ohne Votum verwiesen mit erneuter Wiedervorlage':
        'UEBERWIESEN_WIEDERVORLAGE_OHNEVOTUM',
    u'abgelehnt (in der Vorberatung)': 'ABGELEHNT_VORBERATUNG',
    u'endg\xfcltig abgelehnt': 'ABGELEHNT_ENDGUELTIG',
    u'endg\xfcltig zur\xfcckgezogen': 'ZURUECKGEZOGEN_ENDGUELTIG',
    u'\xdcbergang zum n\xe4chsten Tagesordnungspunkt':
        'NAECHSTER_TAGESORDNUNGSPUNKT',
    u'mit \xc4nderungen empfohlen': 'EMPFOHLEN_GEAENDERT',
}
