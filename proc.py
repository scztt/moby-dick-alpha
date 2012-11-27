import sys
# -*- coding: utf-8 -*-
import string, re
import os, os.path
import codecs
import subprocess
import string
import shutil
import xml.dom.minidom
from subprocess import Popen
from glob import glob
from copy import copy
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
from collections import deque

all_tags = set()
class Tag():
	def __init__(self, name):
		global all_tags
		self.name = name
		self.attributes = dict()
		all_tags.add(self)

	def add_attribute(self, attrib):
		self.attributes[attrib[0]] = attrib[1]

	def __hash__(self):
		hash_tuple = (self.name,) + tuple(self.attributes)
		return hash(hash_tuple)

	def __eq__(self, other):
		return (self.name == other.name) and (self.attributes == other.attributes)

class EPUBParser(HTMLParser):
	delete_tags = ["title"]
	ignore_tags = ["a", "html", "body", "head", "meta", "link"] + delete_tags
	inside_of_deleted_tag = False
	#just_style_tags = ["p"]

	actual_word_chars = (string.letters + string.digits 
		+ u"æéè"
		+ "-"
		+ unichr(339)	# œ
		+ unichr(237)	# í
		+ unichr(249)	# ù
		+ unichr(338)	# Œ
		+ "".join(map(unichr, range(1490,1520))) 	# random hebrew
		+ "".join(map(unichr, range(940,970))))		# random greek

	dash_characters = (
		unichr(8211) 	#–		
		+ unichr(8212))	#—

	word_chars = (actual_word_chars + u"$',"
		+ unichr(8216) 	#‘
		+ unichr(163))	#£

	preserved_punctuation = u";:.?!'"
	stripped_punctuation = u" \n\r\t()&[]{}\"“”“*" + u'\xa0' + unichr(8201) + dash_characters
	word_end_chars = stripped_punctuation + preserved_punctuation

	word_position = 0
	letters = deque(maxlen=20)
	words = list()
	current_word = list()
	word_is_ending = False
	current_tags = list()
	word_tags = list()
	all_tags = set()
	current_file = ""

	def set_file(self, current_file):
		self.current_file = current_file

	def strip_word(self, word):
		to_remove = self.stripped_punctuation
		for char in to_remove:
			word = word.replace(char, u"")
		if word and word[-1] == u"—":
			word = word[0:-1]
		if word and word[0] == u"—":
			word = word[1:]
		return word

	def add_word(self, word, tags=[]):
		contains_actual_letters = False
		for c in self.actual_word_chars:
			if c in word:
				contains_actual_letters = True
				break

		if contains_actual_letters:
			dash_split = re.split("[%s]" % self.dash_characters, word)
			if len(dash_split) > 1:
				print word.encode("utf-8")
			word_obj = Word(word, self.word_position)
			self.word_position += 1
			word_obj.set_tags(copy(tags))
			word_obj.file = self.current_file
			self.words.append(word_obj)
			return word_obj
		else:
			try:
				pass
				#print u"'%s' is not an actual word!" % word.decode("utf-8")
			except UnicodeEncodeError:
				print u"______ is not an actual word!"
			return None

	def word_finished(self):
		word = "".join(self.current_word)
		word = self.strip_word(word)
		if word:
			word_obj = self.add_word(word, self.word_tags)

		# reset
		self.word_is_ending = False
		self.current_word = list()
		self.word_tags = copy(self.current_tags)

	def clean_up(self):
		if self.current_word:
			self.word_finished()

	def parse_character(self, letter):
		if self.inside_of_deleted_tag:
			self.word_is_ending = True
			return

		if letter in self.word_chars:
			if self.word_is_ending:
				hyphen_after_newline = (letter == "-" and self.letters[-1] == "\n")
				if hyphen_after_newline:
					self.word_is_ending = False
				else:
					self.word_finished() 
			self.current_word.append(letter)
		elif letter in self.word_end_chars:
			self.word_is_ending = True
			self.current_word.append(letter)
		else:
			print u"???? " + str(self.current_word)
			try:
				print unicode(letter.decode("utf-8"))
			except Exception:
				try:
					print unicode(letter.encode("utf-8"))
				except Exception:
					print ord(letter)
			if self.word_is_ending:
				self.word_finished() 
			self.current_word.append(letter)

		self.letters.append(letter)

	def handle_starttag(self, tag, attrs):
		if not(tag in self.ignore_tags):
			tag_obj = Tag(tag)
			for attr in attrs:
				tag_obj.add_attribute(attr)
			self.current_tags.append(tag_obj)
			self.word_tags.append(tag_obj)
		if tag in self.delete_tags:
			self.inside_of_deleted_tag = True

	def handle_endtag(self, end_tag):
		reversed_tags = copy(self.current_tags)
		reversed_tags.reverse()
		for tag in reversed_tags:
			if end_tag == tag.name:
				self.current_tags.remove(tag)
				break
		if end_tag == "p" or end_tag == "br":
			self.parse_character(u" ")
		if end_tag in self.delete_tags:
			self.inside_of_deleted_tag = False


	def handle_data(self, data):
		try:
			data = unicode(data)
		except Exception:
			data = unicode(data.decode("utf-8"))
		for character in data:
			self.parse_character(character)

	def handle_entityref(self, name):
		c = unichr(name2codepoint[name])
		self.parse_character(c)

	def handle_charref(self, name):
		if name.startswith('x'):
			c = unichr(int(name[1:], 16))
		else:
			c = unichr(int(name))
		print u"Num ent  :", c
		self.parse_character(c)

	def handle_decl(self, data):
		print u"Decl     :", data

last_chapter = 0
global_position = 0
class Word:
	tag_replacements = {
		"em": ["<em>", "</em>"],
		"strong": ['<span style="font-variant: small-caps;">', "</span>"],
		"small": ["", ""],
		"title": ['<span style="text-transform: uppercase; font-size: 1.2em; font-weight:bold; ">', '</span>'],
		"subtitle": ['<span style="text-transform: uppercase; font-weight:bold; ">', '</span>'],
		"firstword": ['<span style="font-variant: small-caps;">', '</span>'],
		"speaker": ['<span style="text-transform: uppercase; font-size: 0.8em;">', '</span>'],
		"smallcaps": ['<span style="font-variant: small-caps;">','</span>']
	}

	class_to_metatag = {
		"big": "firstword",
		"cn": "title",
		"ct": "subtitle",
		"tx": None,
		"cotx1": None,
		"spk": "speaker",
		"sd": "em",
		"tx1": "smallcaps",
		"extv": "speaker",
		"cepi": None,
		"ceps": "em",
		"cepiv": None,
		"title":"title",
		"subtitle":"subtitle"
	}
	
	file = ""

	def __init__(self, wordString, position=None):
		global global_position
		self.wordString = wordString
		self.sortWordString = wordString.lower().strip()
		self.tags = []

		for char in u" !?,.;:'‘":
			self.sortWordString = self.sortWordString.replace(char,u"")
		self.sortWordString = self.sortWordString.replace(u"æ", "ae")

		try:
			to_keep = string.digits + ".-"
			comma_removed = filter(lambda x: x in to_keep, self.sortWordString)
			asInteger = int(comma_removed)
			self.sortWordString = asInteger
		except ValueError, e:
			pass

		if position == None:
			self.position = global_position
			global_position += 1
		else:
			self.position = position

	def __repr__(self):
		return repr((self.wordString, self.position))

	def __cmp__(self, other):
		result = cmp(self.sortWordString, other.sortWordString)
		if result == 0:
			return cmp(self.position, other.position)
		else:
			return result

	def get_metatags(self):
		meta_tags = set()
		for tag in self.tags:
			if tag.name == "div" or tag.name == "span" or tag.name == "p":
				if tag.attributes.has_key("class"):
					class_name = tag.attributes["class"]
					if self.class_to_metatag.has_key(class_name):
						if self.class_to_metatag[class_name]:
							meta_tags.add(self.class_to_metatag[class_name])
					else:
						print "Unknown class: " + class_name
			elif tag.name == "small":
				meta_tags.add("small")
			elif tag.name == "em":
				meta_tags.add("em")
			elif tag.name == "strong":
				meta_tags.add("strong")
		return meta_tags

	def get_finalized_from_metatags():
		return

	def set_tags(self, tags):
		self.tags = tags

	def display_string(self):
		tag_names = map(lambda x: x.name, self.tags)
		dstring = u"%s (%s) (%s) (%s)" % (self.wordString, u", ".join(self.get_metatags()), self.position, self.file)
		return dstring

	def finalized(self):
		meta_tags = self.get_metatags()
		final_string = self.wordString

		for tag in meta_tags:
			if self.tag_replacements.has_key(tag):
				in_tag = self.tag_replacements[tag][0]
				out_tag = self.tag_replacements[tag][1]
			else:
				in_tag = (u"<%s>" % tag)
				out_tag = (u"</%s>" % tag)
			final_string = in_tag + final_string + out_tag

		return final_string

def finalize(words, name, root_folder):
	list_file = os.path.join(root_folder, name + "_wordlist.txt")
	html_file = os.path.join(root_folder, name + "_final.html")

	(root, filename) = os.path.split(list_file)
	(filename, ext) = os.path.splitext(filename)
	old_list_file = os.path.join(root, filename + "_old" + ext)

	(root, filename) = os.path.split(html_file)
	(filename, ext) = os.path.splitext(filename)
	old_html_file = os.path.join(root, filename + "_old" + ext)
	
	if os.path.exists(list_file):
		shutil.copyfile(list_file, old_list_file)
	if os.path.exists(html_file):
		shutil.copyfile(html_file, old_html_file)

	# word list
	string = "\n".join(map(lambda x: x.display_string(), words))
	out = codecs.open(list_file, "w", "utf-8")
	out.write(string)
	out.close

	# html
	string = " ".join(map(lambda x: x.finalized(), words))
	out = codecs.open(html_file, "w", "utf-8")
	out.write("<html><body align='justify'><font face='Adobe Garamond Pro' size:'12'>\n")
	out.write(string.encode('ascii', 'xmlcharrefreplace'))
	out.write("\n</font></body></html>\n")
	out.close()

	# diff old and new
	print old_list_file, list_file
	if os.path.exists(list_file):
		Popen(["diff '%s' '%s'" % (old_list_file, list_file)], shell=True)

	return (list_file, html_file)

def compare_files(patterns, a, b):
	a = os.path.split(a)[1]
	b = os.path.split(b)[1]

	for pattern in patterns:
		a_match = re.findall(pattern, a)
		b_match = re.findall(pattern, b)
		if len(a_match) == len(b_match) == 0:
			continue
		elif len(a_match) == len(b_match):
			for i, match in enumerate(a_match):
				try:
					result = int(a_match[i]) - int(b_match[i])
					if result != 0:
						return result
				except ValueError:
					result = cmp(a_match, b_match)
					if result != 0:
						return result
		else:
			result = len(b_match) - len(a_match)
			return result
	result = cmp(a, b)
	return result

#############################################################################
## parse html
#############################################################################
def parse_epub(name, root_folder, epub_folder):	
	parser = EPUBParser()

	epub_folder = os.path.join(root_folder, epub_folder)

	glob_pattern = os.path.join(epub_folder, "OEBPS/OEBPS/*.htm")

	sort_patterns = [
		"(epub_tp.*)",
		"(epub_ded.*)",
		"epub_fm([0-9]+)",
		"epub_c?([0-9]+)",
		"epub_bm([0-9]+)"
		]
	files = glob(os.path.join(epub_folder, glob_pattern))
	files.sort(cmp=lambda a,b: compare_files(sort_patterns, a, b))

	for (i, f) in enumerate(files):
		print f
		if i < 99999:
			in_file = codecs.open(f, "r", "utf-8")
			text = in_file.read().encode("utf-8")
			in_file.close()
			parser.set_file(os.path.relpath(f, epub_folder))
			parser.feed(text)
			parser.clean_up()

	print "Sorting..."
	sorted_words = copy(parser.words)
	sorted_words.sort()

	return sorted_words


#words = parse_epub("moby_dick", "/Users/Scott/Documents/alpha", "Moby-Dick-epub/OEBPS/OEBPS/Melv_9780553898101_epub_fm1_r1.htm")
words = parse_epub("moby_dick", "/Users/Scott/Documents/alpha", "Moby-Dick-epub")
(list_file, html_file) = finalize(words, "moby_dick", "/Users/Scott/Documents/alpha")

subprocess.call(['textutil', '-convert', 'docx', html_file])