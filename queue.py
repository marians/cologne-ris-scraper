# encoding: utf-8

"""
Modul für Scraper-Warteschlangen

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


class Queue(object):
    """Abstrakte Warteschlange, die zum Abarbeiten von Sitzungen,
    Dokumenten etc. benutzt wird. Bereits verarbeitete Elemente
    werden weiterhin gespeichert und können nicht erneut hinzugefügt
    werden."""

    def __init__(self):
        self.fresh_elements = set()
        self.used_elements = set()

    def has_next(self):
        """Gibt True zurück, wenn Elemente in der Warteschlange sind."""
        if len(self.fresh_elements) > 0:
            return True
        return False

    def add(self, element):
        """Fügt ein Element zur Wartecshlange hinzu. Wenn das Element schon
        in der Warteschlange ist, wird es nicht noch mal hinzugefügt, jedoch
        kein Fehler erzeugt. Sollte das Element schon mal hinzugefügt und
        bereits verarbeitet worden sein, wird ebenfalls kein Fehler erzeugt."""
        if element not in self.used_elements:
            self.fresh_elements.add(element)

    def get(self):
        """Gibt das nächste Element aus der Warteschlange zurück und entfernt
        es aus der Warteshlange. Wenn kein Element mehr vorhangen ist, wird
        ein KeyError geworfen."""
        el = self.fresh_elements.pop()
        self.used_elements.add(el)
        return el

    def __len__(self):
        """Gibt die Anzahl der noch nicht bearbeiten Elemente zurück"""
        return len(self.fresh_elements)

if __name__ == '__main__':
    """Tests"""
    q = Queue()
    print "Queue has elements:", q.has_next()
    q.add(1)
    print "Queue has elements:", q.has_next()
    q.add(1)
    q.add(2)
    q.add(3)
    print "Queue has num elements:", len(q)
    print "Getting queue item:", q.get()
    print "Queue has num elements:", len(q)
    print "Getting queue item:", q.get()
    print "Queue has num elements:", len(q)
    print "Getting queue item:", q.get()
    print "Queue has elements:", q.has_next()
