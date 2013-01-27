#!/usr/bin/env python
# encoding: utf-8

"""
Berechnet den Unterschied zwischen zwei Textdateien
zur Qualitätskontrolle von OCR-Software im Vergleich
mit einem manuell erstellten Referenz-Dokument
"""

from optparse import *
import os
import sys
import re
import math


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


def calculate_difference(path1, path2):
    """
    Returns tuple of (length, diff) where
    length is the larger file's length and diff
    is the number of characters editing difference
    according to the levenshtein distance.
    """
    file_a = read_file(path1)
    file_b = read_file(path2)
    file_a_norm = normalized_text(file_a)
    file_b_norm = normalized_text(file_b)
    idstring = path1.rsplit(os.sep, 1)[1].split('.')[0]
    sys.stdout.write(idstring + ": ")
    if file_a != False and file_b != False:
        length = max(len(file_a_norm), len(file_b_norm))
        lev_norm = levenshtein(file_a_norm, file_b_norm)
        return (length, lev_norm)


def single_result_display(length, levenshtein_distance):
    print "%d von %d Zeichen - %.1f %%" % (
        levenshtein_distance,
        length,
        ((float(levenshtein_distance) / float(length)) * 100.0))


def common_textfiles(dir1, dir2):
    """
    Returns a list of file names which exist both in dir1 and dir2
    """
    list1 = os.listdir(dir1)
    list2 = os.listdir(dir2)
    both = list(set(list1).intersection(list2))
    qualified = []
    for filename in both:
        if '.txt' in filename:
            qualified.append(filename)
    qualified.sort()
    return qualified


def average(values):
    return float(sum(values)) / len(values)


def average_stdev(values):
    """
    Returns a tuple of average and stdev of all values
    """
    avg = float(sum(values)) / len(values)
    variance = map(lambda x: (x - avg) ** 2, values)
    stddev = math.sqrt(average(variance))
    return (avg, stddev)


if __name__ == '__main__':
    parser = OptionParser()
    (options, args) = parser.parse_args()
    # if arguments are files, individual files are compared.
    # if arguments are folders, all .txt files in these are compared.
    if os.path.isfile(args[0]) and os.path.isfile(args[1]):
        (length, difference) = calculate_difference(args[0], args[1])
        single_result_display(length, difference)
    elif os.path.isdir(args[0]) and os.path.isdir(args[1]):
        files = common_textfiles(args[0], args[1])
        results = []
        for filename in files:
            path1 = args[0] + os.sep + filename
            path2 = args[1] + os.sep + filename
            (length, difference) = calculate_difference(path1, path2)
            results.append(float(difference) / float(length))
            single_result_display(length, difference)
        (avg, std) = average_stdev(results)
        print "--------------------------------------------------------"
        print "Mittelwert: %.1f %%\nStandardabweichung: %.1f" % (
            avg * 100.0,
            std * 100.0)
    else:
        raise OptionValueError("Gib entweder zwei Dateien oder zwei Ordner als Agumente an.")
