#!/usr/bin/env python
# encoding: utf-8

"""
Berechnet den Unterschied zwischen zwei Textdateien
anhand des Levenshtein-Algorithmus
"""

from optparse import OptionParser
import os
import sys
import re


def levenshtein(s1, s2):
    """
    Quelle: http://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
    """
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if not s1:
        return len(s2)
    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def read_file(path):
    if not os.path.exists(path):
        print >> sys.stderr, "Datei", path, "existiert nicht."
        return False
    f = open(path, 'r')
    content = f.read()
    f.close()
    return content


def normalized_text(text):
    text = text.lower()
    text = re.sub(r"[-_\.:!\?,;/\(\)„%<>\"\'»]", ' ', text)
    text = re.sub(r"\s+", ' ', text)
    return text


if __name__ == '__main__':
    parser = OptionParser()
    (options, args) = parser.parse_args()
    file_a = read_file(args[0])
    file_b = read_file(args[1])
    file_a_norm = normalized_text(file_a)
    file_b_norm = normalized_text(file_b)
    if file_a != False and file_b != False:
        laenge_norm = max(len(file_a_norm), len(file_b_norm))
        lev_norm = levenshtein(file_a_norm, file_b_norm)
        print "Differenz %d von %d Zeichen (%.1f%%)" % (
            lev_norm,
            laenge_norm,
            ((float(lev_norm) / float(laenge_norm)) * 100.0))
