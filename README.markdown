#Scraper für das Ratsinformationssystem von Köln

Dies ist ein Scraper für die Daten im Ratsinformationssystem (RIS) der Stadt Köln.

Das RIS der Stadt Köln ist unter http://ratsinformation.stadt-koeln.de erreichbar.

Ein Ratsinformationssystem bietet üblicherweise Zugriff auf Informationen zu Sitzungen der Gremien 
(wie z.B. des Stadtrats), die darin behandelten Tagesordnungspunkte, die Anträge 
und Beschlüsse und mehr.

Das Kölner RIS basiert auf der Software SessionNet, die bei vielen Gemeinden, Landkreisen und anderen 
Körperschaften im Einsatz ist. Daher sollte sich dieser Scraper mit leichten Anpassungen auch für andere
SessionNet Instanzen einsetzen lassen.

##Gruppe/Mailingliste

Wenn Du den Scraper in Deiner Gegend einsetzen willst, tritt bitte dieser Gruppe bei:

https://groups.google.com/forum/#!forum/ris-oeffner

Dort solltest Du Ansprechpartner finden, die ähnliches vorhaben wie Du.


##FAQ

###Was ist ein Scraper?

Ein Scraper ist ein Programm, dass die Daten aus einer Website extrahiert und in strukturierter Form speichert.

###Welchen Entwicklungsstand hat der Scraper?

Der Scraper kann noch nicht als "fertig" bezeichnet werden.

* Es werden noch nicht alle wesentlichen Daten erfasst.
* Anhänge mit Texten, z.B. TIF-Scans (Faxe) werden nur gespeichert, Volltexte werden jedoch nicht extrahiert.

###Welche Programmiersprache nutzt das Programm?

Der Scraper ist in Python geschrieben.

###Welche Python-Version wird benötigt?

Bisher wurde der Scraper nur mit Python 2.7 getestet.

###Welche Python-Module werden benötigt?

* urllib2
* scrapemark
* mechanize
* MySQLdb

###Was wird außerdem benötigt?

Zum Speichern der Daten wird aktuell ein MySQL-Server benötigt.

###Wie funktioniert die Installation?

Zunächst muss geklärt werden, ob Python und MySQL vorhanden sind.

1. Benötigte Python-Module installieren
2. Leere MySQL-Datenbank anlegen und einen Nutzer
3. Die Datei setup_mysql.sql in der neuen Datenbank ausführen. Damit werden die benötigten Tabellen angelegt.
4. Die Konfigurationsdatei config_dist.py zu config.py kopieren. Dann config.py anpassen.

Danach sollte sich der Scraper mit dem Kommando "python scrape.py" an der Kommandozeile starten lassen.

Auf einem leeren Debian 6 kann die benötigte Software wie folgt installiert werden (als root):

    apt-get update
    apt-get install mysql-server
    apt-get install git
    apt-get install python-mysqldb
    apt-get install python-mechanize
    wget http://arshaw.com/scrapemark/downloads/scrapemark-0.9.tar.gz
    tar xzf scrapemark-0.9.tar.gz
    cd scrapemark-0.9/
    python setup.py install
    cd ..

Danach können die folgenden Schritte unter normalen Nutzerrechten ausgeführt werden:

    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS risscraper;"
    mysql -u root -p -e "CREATE USER 'risscraper'@'localhost' IDENTIFIED BY 'risscraper';"
    mysql -u root -p -e "GRANT ALL ON risscraper.* TO 'risscraper'@'localhost';"
    mysql -u root -p -e "FLUSH PRIVILEGES;"
    git clone https://github.com/marians/cologne-ris-scraper.git
    mkdir attachments
    mkdir tmp

###Sind die Daten selbst irgendwo verfügbar?

Die Daten aus dem Kölner RIS sind vollständig über die API von Offenes Köln zugänglich. Weiteres Scrapen des Kölner RIS
ist also nicht nötig und nicht sinnvoll. Informationen unter

http://offeneskoeln.de/api/

###Unter welcher Lizenz steht der Quellcode?

Unter der folgenden, MIT-ähnlichen Lizenz:

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
    
