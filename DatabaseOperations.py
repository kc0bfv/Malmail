class Database():
	def __init__(self):
		# TODO: Init the database...

		self.cheaterFullSet = set()
		self.cheaterExploredSet = set()

	def addURLs(self, urlList):
		"""Add URLs to the database if they're not there already.

			urlList: the iterable of URLs to add
			"""
		# TODO: add URLs to the database if they're not already
		urlList = list(urlList)

		# Union the set with the urlList
		self.cheaterFullSet |= set(urlList)

	def getURLs(self):
		"""Return the URLs in the database that require processing.

			Return value: [url string, url string, ...]
			"""
		
		# TODO: Don't do this cheater method, do it for reals.  Remove urlLists
		return list(self.cheaterFullSet - self.cheaterExploredSet)

	def markURLsExplored(self, urlList):
		self.cheaterExploredSet |= set(urlList)

	def addEmails(self, emailList):
		"""Add emails to the database, return their DB key.

			emailList: an iterable of EmailData objects

			Return: [dbKey, ...] - same order as emailList
			"""
		cnt = 0
		def _add(email):
			nonlocal cnt
			cnt += 1
			return cnt
		
		return [_add(email) for email in emailList]

	def referenceURLsToEmail(self, urlList, emailDBKey):
		"""Reference URLs (that are already in the DB) to the email.

			urlList: an iterable of url strings
			emailDBKey: a database key for an email

			Throws: 
			"""
		pass
