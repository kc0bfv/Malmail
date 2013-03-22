#!/usr/bin/env python3

import itertools as it

import EmailRetriever as er
import personalGmailData as pgd
import ContentHandlers as ch
import RetrieveURLs as rurl
import DatabaseOperations as dbo


class EmailHandler():
	def __init__(self):
		self.db = dbo.Database()

	def processEmails(self, unseenOnly=False):
		"""Retrieve emails, extract URLs, add URLs to DB, return URLs to process.

			Get the new emails from the server, add them to the database, 
			get the urls from each email, add them to the database,
			return the list of all urls that haven't been processed yet.

			Return value: [url string, ...]
			"""
		# Retrieve all the emails
		options = pgd.serverDetails.copy()
		options["unseenOnly"] = unseenOnly
		with er.EmailRetriever(**options) as emailGenerator:
			emailList = list(emailGenerator)

		# emailDBKeys are in the same order as emailList
		emailDBKeys = self.db.addEmails(emailList)
		assert (len(emailDBKeys) == len(emailList)), (
				"dbKeys, emailList are different length")

		# Get a list of urls in an email, for each email
		urlLists = [email.extractURLs() for email in emailList]

		self.db.addURLs(it.chain.from_iterable(urlLists))

		for (emailDBKey, urlList) in zip(emailDBKeys, urlLists):
			self.db.referenceURLsToEmail(urlList, emailDBKey)

		# Get the url list from the DB - that'll have all unexplored URLs, not
		#		just the ones from this email set
		return self.db.getURLs()

	def handleURLs(self, urlList, storeInDB=True):
		"""Handle all URLs in the URL list.

			Get the contents of each url in the list, "handle" the contents.
			
			urlList: [url string, ...]
			storeInDB: whether to store found urls in the database or not.
				Not storing them provides a way to limit depth of followed links
		"""
		for url in urlList:
			contentList = rurl.retrieveURLWithEachUserAgent(url)

			#TODO: something interesting with other handled content
			# - cross reference it with the user agents...
			if storeInDB:
				self.db.addURLs(it.chain.from_iterable(
					content.contents.extractURLs() for content in contentList))

		self.db.markURLsExplored(urlList)

		return self.db.getURLs()


	def main(self):
		# Only process URLs to maxLinkDepth
		(currentLinkDepth, maxLinkDepth) = (0, 3)

		# Grab the emails, kick off the process with some URLs
		urlList = self.processEmails()
		# Process urls until the database has no more
		while urlList:
			print(urlList)
			urlList = self.handleURLs(urlList, (currentLinkDepth < maxLinkDepth))
			currentLinkDepth += 1
		


if __name__ == "__main__":
	eh = EmailHandler()
	eh.main()
