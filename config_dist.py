#!/bin/env python
# coding: utf-8

# Database settings
DBHOST = 'localhost'
DBUSER = 'risscraper'
DBPASS = 'risscraper'
DBNAME = 'cologne-ris'

# Basis-URL (mit / am Ende)
BASEURL = 'http://buergerinfo.halle.de/'

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
