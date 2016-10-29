"""
Abstracted database operations

The external interface is the Database class
"""

import urllib.parse

from Common import *
from DatabaseModel import *

def domain(url):
    """
    Utility function split the domain out of the url

    :param str url: The url to split out
    :returns: The scheme and domain
    """
    (scheme, netloc, path, query, fragment) = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((scheme, netloc, "", None, None))


class ContentToDatabase():
    """
    A super class for the classes that add specific content types to the
    database.
    """

    @classmethod
    def add(cls, content, referrer=None, userAgents=None):
        """
        Add content to the database, return its database key.

        :param content:
            Some object that a subclass can handle
        :param str referrer:
            OPTIONAL: default - None
            The URL string to reference this content to, if any
        :param iterable userAgents:
            An iterable containing strings of the userAgents used to retrieve
            this content.

        :returns: integer databaseKey
        """
        raise NotImplementedError("Called add on superclass ContentToDatabase")

    # The database model represented by each subclass
    model = None
    referrerModel = None

    @classmethod
    def _insertGenericIfNotExists(cls, dbModel, **data):
        """
        Insert some data if it's not already in there.

        Return: The data's database key, either the new one if it got inserted,
        or the old one if it was already present.
        """
        # Build up a query
        query = dbModel.select()
        for (row, dat) in data.items():
            query = query.where(getattr(dbModel, row) == dat)

        # Execute the query, and maybe the insert
        try:
            return query.get().id
        except dbModel.DoesNotExist:
            return dbModel.insert(**data).execute()

    @classmethod
    def _insertContentIfNotExists(cls, **data):
        return cls._insertGenericIfNotExists(cls.model, **data)

    @classmethod
    def _insertReferrerIfNotExists(cls, **data):
        return cls._insertGenericIfNotExists(cls.referrerModel, **data)

class EmailContentToDatabase(ContentToDatabase):
    """Referenced by toDatabaseClass in email"""
    model = Email
    # No referrerModel - no URL resolves to the email, so no need...

    @classmethod
    def add(cls, content, referrer=None, userAgents=None):
        emailFields = {"fromAddress": content.fromAddress,
                        "toAddress": content.toAddress,
                        "fromFriend": content.fromFriend,
                        "content": content.content}
        return cls._insertContentIfNotExists(**emailFields)

class HTML_JS_OtherToDatabase(ContentToDatabase):
    """Superclass for HTML/JS/OtherContentToDatabase"""
    @classmethod
    def add(cls, content, referrer=None, userAgents=None):
        contentFields = {"content": content.content}
        contentKey = cls._insertContentIfNotExists(**contentFields)

        if referrer is not None:
            try:
                url=URL.select().where(URL.url == referrer).get()
            except URL.DoesNotExist:
                print_error(
                    "Error associating content with non-existent URL:", url)
            else:
                for userAgent in userAgents:
                    referrerFields = {"content": contentKey,
                                    "url": url, "userAgent": userAgent}
                    cls._insertReferrerIfNotExists(**referrerFields)

        return contentKey

class HTMLContentToDatabase(HTML_JS_OtherToDatabase):
    """Referenced by toDatabaseClass in HTML content"""
    model = HTML_Content
    referrerModel = HTML_To_URL

class JSContentToDatabase(HTML_JS_OtherToDatabase):
    """Referenced by toDatabaseClass in JS content"""
    model = JS_Content
    referrerModel = JS_To_URL

class OtherContentToDatabase(HTML_JS_OtherToDatabase):
    """Referenced by toDatabaseClass in web content"""
    model = Other_Content
    referrerModel = Other_To_URL


class Database():
    """
    Database presents a set of operations against the database.

    Intended use:
        with Database() as db:
            db.do_things()
    """
    def __init__(self):
        # Cheats
        self.cheaterFullSet = set()
        self.cheaterExploredSet = set()

    def __enter__(self):
        database.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        database.close()

    def addURLs(self, urlList, referrer=None, userAgents=None,
            fromEmail=False):
        """
        Add URLs to the database if they're not there already.
        
        :param iterable urlList:
            An iterable yielding string URLs
        
        :param str/int referrer:
            The url string or integer email_id of the document or email
            that contained this URL

        :param iterable userAgents:
            An iterable yielding string userAgents
            Only used when the referrer is a URL

        :param bool fromEmail:
            Make this true when the referrer is an email
        """
        for url in urlList:
            if not URL.select().where(URL.url == url).exists():
                dom = domain(url)
                try:
                    domainID = Domain.select().where(
                            Domain.url == dom).get().id
                except Domain.DoesNotExist:
                    domainID = Domain.insert(url = dom).execute()
                URL.insert(domain=domainID, url = url,
                        processed=False).execute()
        if referrer:
            if fromEmail:
                self.referenceURLsToEmail(urlList, referrer)
            else:
                self.referenceURLsToURL(urlList, referrer, userAgents)

    def getURLs(self):
        """
        Return the URLs in the database that require processing.
        
        :returns: [url string, url string, ...]
        """

        recordList = URL.select().where(URL.processed == False).execute()
        return [item.url for item in recordList]

    def markURLsExplored(self, urlList):
        """
        Mark all urls in urlList as having-been explored

        :param iterable urlList:
            An iterable containing url strings
        """
        for url in urlList:
            URL.update(processed = True).where(URL.url == url).execute()

    def addContent(self, content, referrer=None, userAgents=None):
        """
        Add content of some RetrievedData type into the database

        :param RetrievedData content:
            The content to add

        :param string referrer:
            OPTIONAL: default - None
            The URL that referred to this content, if one

        :param iterable userAgents:
            OPTIONAL: default - None
            An iterable containing string userAgents that retrieved the
            content from referrer.  Not used if referrer is None

        :returns: The database ID of the added content
        """
        return content.toDatabaseClass.add(content, referrer, userAgents)

    def referenceURLsToEmail(self, urlList, emailDBKey):
        """
        Reference URLs (that are already in the DB) to the email.
        
        :param iterable urlList:
            An iterable of url strings to reference to the email
        :param int emailDBKey:
            A database key for an email
        """
        for url in urlList:
            try:
                URL_To_Email.insert(
                        email=emailDBKey,
                        url=URL.select().where(URL.url == url).get()
                    ).execute()
            except URL.DoesNotExist:
                print_error("Error associating email with non-existent URL:",
                        url)

    def referenceURLsToURL(self, urlList, sourceUrl, userAgents):
        """
        Reference URLs (that are already in the DB) to the url (also in db)

        :param iterable urlList:
            An iterable of url strings to reference to the email
        :param string sourceUrl:
            The url to reference each urlList item to.  Also a string
        :param iterable userAgents:
            A list of userAgent strings that produced the url mapping
        """
        errorString = ("Error associating {contNE}URL ({cont}) with {srcNE}"
                        "URL ({src})")
        nonExist = "non-existent "

        for containedUrl in urlList:
            src = URL.select().where(URL.url == sourceUrl).first()
            cont = URL.select().where(URL.url == containedUrl).first()

            formatDict = {"contNE": nonExist if (src is None) else "",
                            "srcNE": nonExist if (cont is None) else "",
                            "cont": containedUrl, "src": sourceUrl}

            if (src is not None) and (cont is not None):
                for userAgent in userAgents:
                    URL_To_URL.insert(source_url = src, contained_url = cont,
                                    userAgent=userAgent).execute()
            else:
                print_error(errorString.format(**formatDict))

    def printDatabase(self):
        """
        Print out the database in a rough way
        """
        subclasses = set([BASE_CLASS])
        len_prev = -1
        while len_prev != len(subclasses):
            len_prev = len(subclasses)
            for subc in set(subclasses):
                subclasses.update(subc.__subclasses__())
        subclasses.remove(BASE_CLASS)
        for subc in subclasses:
            print("{}: {}".format(subc.__name__, subc.select().count()))
            for mbr in subc.select():
                print(mbr._data)
