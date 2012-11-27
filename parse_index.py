# -*- coding: utf-8 -*-
import string, re
import os, os.path
import codecs
from stemming.porter2 import stem
from copy import copy

def format_pages(page_set):
	page_ranges = list()
	last_page = -100
	start_page = None

	page_list = map(int, page_set)
	page_list.sort()

	if len(page_list) == 1:
		return unicode(list(page_list)[0])
	else:
		i = 0
		done = False
		while not(done):
			start_page = page_list[i]
			end_page = page_list[i]
			j = i + 1
			while j < len(page_list) and page_list[j-1] + 1 == page_list[j]:
				end_page = page_list[j]
				j += 1

			if start_page == end_page:
				page_ranges.append(str(start_page))
			else:
				page_ranges.append(str(start_page) + "-" + str(end_page))

			i = j
			if not(i < len(page_list)):
				done = True

	return u", ".join(page_ranges)

def parse_index(load_from):
	in_file = codecs.open(load_from, "r", "utf-8")

	current_page = None
	words = dict()
	for (i, line) in enumerate(in_file):
		page_mark = re.findall("===([0-9]+)===", line)
		if page_mark:
			print page_mark[0]
			current_page = int(page_mark[0])
		else:
			word = line.strip().lower()
			for punct in u':;,.?!()"‘':
				word = word.replace(punct,"")
			if word != u"":
				if not(words.has_key(word)):
					#print u"\t" + word
					words[word] = set()
				words[word].add(current_page)

	in_file.close()

	stem_exceptions = ["whale", "wester", "aim", "after", "cruise", "drug", "drive"]
	stemmed_dict = dict()
	for i, word in enumerate(words.keys()):
		split_word = word.split("-")
		if len(split_word) > 1:
			stemmed = stem(split_word[0]).lower().strip()
		else:
			stemmed = stem(word).lower().strip()
		for exc_stem in stem_exceptions:
			if stemmed.startswith(exc_stem):
				stemmed = exc_stem
				break

		if not(stemmed_dict.has_key(stemmed)):
			stemmed_dict[stemmed] = dict()
		stemmed_dict[stemmed][word] = word

	(path, filename) = os.path.split(load_from)
	(filename, ext) = os.path.splitext(filename)
	index_out_path = os.path.join(path, filename + "_formatted" + ".txt")
	out = open(index_out_path, "w")

	stemmed_list = list(stemmed_dict.keys())
	stemmed_list.sort()
	for stemmed in stemmed_list:
		if len(stemmed_dict[stemmed].keys()) == 1:
			orig_word = stemmed_dict[stemmed].values()[0]
			pages = format_pages(words[orig_word])
			out.write(("%s, %s\n" % (stemmed_dict[stemmed].keys()[0], pages)).encode("utf-8"))
			print ("%s, %s" % (stemmed_dict[stemmed].keys()[0], pages)).encode("utf-8")
		else:
			all_words = stemmed_dict[stemmed].values()
			all_words.sort(key=len, reverse=False)
			shortest = all_words[0]

			pages = format_pages(words[shortest])
			print ("%s, %s" % (shortest, pages)).encode("utf-8")
			out.write(("%s, %s\n" % (shortest, pages)).encode("utf-8"))

			for word in all_words[1:]:
				pages = ", ".join(map(str, words[word]))
				print ("\t%s, %s" % (word, pages)).encode("utf-8")
				out.write(("\t%s, %s\n" % (word, pages)).encode("utf-8"))

	out.close()

orig_index = "/Users/Scott/Documents/alpha/index_pages.txt"
parse_index(orig_index)

#print "\t" + format_pages([100])
#print "\t" + format_pages([100,101,102])
#print "\t" + format_pages([100,101,102, 106, 107, 108, 120])