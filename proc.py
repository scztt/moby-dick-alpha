import string 

class Word:
	def __init__(self, wordString, position):
		self.wordString = wordString
		self.sortWordString = wordString.lower().strip()
		for char in " !?,.;:":
			self.sortWordString = self.sortWordString.replace(char,"")

		try:
			asInteger = int(self.sortWordString)
			self.sortWordString = asInteger
		except Exception:
			pass

		self.position = position

	def __repr__(self):
		return repr((self.wordString, self.position))

  	def __cmp__(self, other):

  		result = cmp(self.sortWordString, other.sortWordString)
  		if result == 0:
  			return cmp(self.position, other.position)
  		else:
  			return result




origFile = file("/Users/Scott/Documents/alpha/Moby Dick.txt","r")
origText = origFile.read()
origFile.close()

# strip punctuation
strippedString = ""
prevChar = ""
for char in origText:
	if char in (string.letters + string.digits + " !?,.;:") or (char == "'" and prevChar in string.letters):
		if char in string.whitespace:
			print(ord(char))
		strippedString += char
	else:
		strippedString += " "
	prevChar = char

strippedString = strippedString.replace("--", " ")
strippedString = strippedString.replace("\n", " ")
strippedString = strippedString.replace("\r", " ")
strippedString = strippedString.replace("\t", " ")


for i in range(0,5):
	strippedString = strippedString.replace("  ", " ")

wordsArray = []
i = 0
for word in strippedString.split(" "):
	wordsArray.append(Word(word.strip(), i))
	i += 1

wordsSorted = sorted(wordsArray)

finalString = ""
for word in wordsSorted:
	finalString += word.wordString + " "

out = file("/Users/Scott/Documents/alpha/mobydick_alpha.txt", "w")
out.write(finalString)
out.close()


