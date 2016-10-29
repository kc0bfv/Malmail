#!/usr/bin/env python3

"""This module knows how to get URLs and content out of many things."""

import email
import itertools as it
import html.parser as htp
import unittest
import urllib.request as urlReq
import urllib.parse as urlParse

import DatabaseOperations

class EqualityWithToTuple():
    """Superclass for objects that need equality other than "id()".

            Subclasses must define _toTuple.  They gain a sense of equality
            determined by the tuplization returned by _toTuple."""

    def _toTuple(self):
        """In subclasses this should tuplize the "public" members."""
        raise NotImplementedError(
                        "Called _toTuple on superclass EqualityWithToTuple")

    def __eq__(self, other):
        try: return (self._toTuple() == other._toTuple())
        except: return False
    def __ne__(self, other): return not self.__eq__(other)
    def __hash__(self): return hash(self._toTuple())
    def __repr__(self): return repr(self._toTuple())


class RetrievedData(EqualityWithToTuple):
    """Superclass for different types of toplevel data objects - Web or Email"""
    def __init__(self, data, contentType, url=None):
        """
                data - the data from the response
                contentType - the mimetype of the data
                """
        self.data = selContentClass(contentType) (data)
        self.contentType = contentType
        self.redirect = None
        self.url = url
        self.toDatabaseClass = DatabaseOperations.ContentToDatabase

    def _toTuple(self):
        return (self.url, self.data, self.redirect, self.contentType)

    def body(self): return self.data.body()

    def extractURLs(self):
        def _absolutizeURL(url):
            return url if (self.url is None) else urlParse.urljoin(self.url, url)
        # The data knows how to extract its own URLs
        return [_absolutizeURL(url) for url in self.data.extractURLs()]

    @property
    def content(self):
        return self.data.body()


class WebData(RetrievedData):
    """Represents data retrieved from a urllib.Request"""
    def __init__(self, obj, req):
        """
                obj: an HTTPResponse object
                req: a urllib.request.Request object
                """
        contentTypeHeader = obj.getheader("Content-Type")
        refreshHeader = obj.getheader("Refresh")
        data = obj.read()
        defaultEncoding = "ISO-8859-1"

        try:    # Extract content type and encoding
            contentType = contentTypeHeader.partition(";")[0]
            encoding = contentTypeHeader.partition("charset=")[2]
        except AttributeError:
            contentType = None
            encoding = defaultEncoding

        try:    # Decode data
            decodedData = data.decode(encoding)
        except LookupError:
            decodedData = data.decode(defaultEncoding)

        super().__init__(decodedData, contentType, req.full_url)
        # The data knows how
        self.toDatabaseClass = self.data.toDatabaseClass

        #TODO: extract redirect from other places, too
        try:    # Extract the redirect address
            self.redirect = obj.getheader("Refresh").partition("url=")[2]
        except AttributeError:
            self.redirect = None


class EmailData(RetrievedData):
    """Represents byte or string data as an email"""
    def __init__(self, obj):
        if type(obj) is bytes:
            msg = email.message_from_bytes(obj)
        else:
            msg = email.message_from_string(obj)

        if msg.is_multipart():
            super().__init__(msg, "multipartEmail")
        else:
            super().__init__(msg.get_payload(decode=True), msg.get_content_type())

        self.fromAddress = msg["From"]
        self.toAddress = msg["To"]
        self.fromFriend = False

        # Use the emailContentToDatabase handler regardless of data...
        self.toDatabaseClass = DatabaseOperations.EmailContentToDatabase



class Content(EqualityWithToTuple):
    def __init__(self, data):
        self.data = data
        # These data classes need to know which class adds their content to DB
        self.toDatabaseClass = DatabaseOperations.OtherContentToDatabase

    def _toTuple(self):
        return (self.data)

    def extractURLs(self):
        """Return a list of URLs contained in the data"""
        raise NotImplementedError("Called extractURLs on superclass Content")

    def body(self):
        """Return the "body" of the message, as a string if possible

                "body" isn't well defined.  But it's the HTML in a web document, for
                instance
                """
        return self.data

class PlainTextContent(Content):
    def extractURLs(self):
        # Eliminate some characters, like newlines, that typically break
        # URLs in plain text messages
        toReplaceChars = "\n\r"
        if isinstance(self.data, bytes):
            replaced = self.data.translate(None, bytes(toReplaceChars, "ascii"))
        else:
            replaced = self.data.translate("".maketrans("", "", toReplaceChars))

        # Find likely URLs in the result
        urlList = []
        urlPrefixes = ("http://", "https://")

        #TODO: make this better.  Right now, this can't detect links that are not preceeded by a space.  If they're preceeded by a linespace, then other data, the linespace doesn't get replaced with a space, so then the url isn't detected...

        if isinstance(replaced, bytes):
            urlPrefixes = tuple(bytes(pref, "ascii") for pref in urlPrefixes)

        for token in replaced.split():
            if token.startswith(urlPrefixes):
                urlList.append(token)

        return urlList

    def body(self):
        if isinstance(self.data, bytes):
            return self.data.decode()
        else:
            return self.data

class HTMLContent(Content):
    def __init__(self, data):
        super().__init__(data)
        self.toDatabaseClass = DatabaseOperations.HTMLContentToDatabase

    def extractURLs(self):
        class URLExtractor(htp.HTMLParser):
            attrsContainingURLs = ["src", "href"]
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.urlList = []

            def handle_starttag(self, tag, attrs):
                for (attrName, attrValue) in attrs:
                    if attrName.lower() in self.attrsContainingURLs:
                        self.urlList.append(attrValue)

        parser = URLExtractor()
        parser.feed(self.data)
        parser.close()
        # TODO: I get some weird URLs sometimes, without http://.  Why?  These mess up the URL retriever
        return parser.urlList


class JSContent(Content):
    def __init__(self, data):
        super().__init__(data)
        self.toDatabaseClass = DatabaseOperations.JSContentToDatabase

    def extractURLs(self):
        #TODO
        return []


class MultipartEmailContent(Content):
    def __init__(self, data):
        super().__init__(data="")

        # Retrieve the data parts
        max_iteration_depth = 3
        dataParts = []
        partsToSearch = [data]
        for iteration in range(max_iteration_depth):
            multiParts = (part.is_multipart() for part in partsToSearch)
            singleParts = (not part.is_multipart() for part in partsToSearch)
            dataParts += list(it.compress(partsToSearch, singleParts))
            partsToSearch = list(it.chain.from_iterable(part.get_payload()
                            for part in it.compress(partsToSearch, multiParts)))
        partsToSearch = [] # Allow garbage collection on any leftovers...

        # Helper function to decode a part into a string
        defaultEncoding = "ISO-8859-1"
        def _returnStringPayload(part):
            payload = part.get_payload(decode=True)
            try:
                decodedPayload = payload.decode(part.get_content_charset())
            except LookupError:
                decodedPayload = payload.decode(defaultEncoding)
            return decodedPayload

        # Store data parts as data of the appropriate type
        dataClasses = (selContentClass(p.get_content_type()) for p in dataParts)
        dataAsString = [_returnStringPayload(p) for p in dataParts]
        self.data = [dataClass(strData)
                        for (dataClass, strData) in zip(dataClasses, dataAsString)]

    def extractURLs(self):
        """Extract urls for all data parts."""
        return list(it.chain.from_iterable(
                part.extractURLs() for part in self.data))

    def body(self):
        return "\n".join(part.body() for part in self.data)



def selContentClass(contentType):
    """Determine which Content class to use.

            contentType: a string containing the mime type, or "multipartEmail"

            Return value: an appropriate subclass of Content
            """
    mimeList = {"text/html": HTMLContent,
                    "text/plain": PlainTextContent,
                    "application/javascript": JSContent,
                    "multipartEmail": MultipartEmailContent}
    return mimeList.get(contentType, PlainTextContent)







class ContentHandlersTester(unittest.TestCase):
    def test_handleHTML_extractURLs(self):
        testURLs= [
                (
                    [
                        "https://notmet.net/test.htm",
                        "https://notmet.net/"
                        ],
                    "https://notmet.net/test.htm"
                    )
                ]
        for (linkList, url) in testURLs:
            request = urlReq.Request(url)
            with urlReq.urlopen(request) as connection:
                wd = WebData(connection, request)

            self.assertEqual(set(linkList), set(wd.extractURLs()))

    def test_EmailData_extractURLs(self):
        testEmails = [
                (
                    [
                        'https://mail.google.com/mail/images/welcome-inbox-screenshot.png',
                        'https://mail.google.com/mail/images/welcome-conversation-screenshot.png',
                        'http://www.example.com/',
                        'http://www.example.com/linesplit'
                        ],
                    b'MIME-Version: 1.0\r\nReceived: by 10.227.11.133; Thu, 28 Feb 2013 12:42:35 -0800 (PST)\r\nDate: Thu, 28 Feb 2013 12:42:35 -0800\r\nMessage-ID: <CAN9Dh1v88LUBvX6WLmG41Ugn=UoXchS=pHp4RDHZTvRNCX34rw@mail.gmail.com>\r\nSubject: Get started with Gmail\r\nFrom: Gmail Team <mail-noreply@google.com>\r\nTo: Research Blackhole <research.blackhole@notmet.net>\r\nContent-Type: multipart/alternative; boundary=002215974a724558c304d6ceeea0\r\n\r\n--002215974a724558c304d6ceeea0\r\nContent-Type: text/plain; charset=ISO-8859-1\r\n\r\n4 things you need to know\r\nGmail is a little bit different. Learn these 4 basics and you\'ll never look\r\nback.\r\n[image: Inbox screenshot]\r\n\r\n1. Archive instead of delete\r\nTidy up your inbox without deleting anything. You can always search to find\r\nwhat you need or look in "All Mail."\r\n\r\n2. Chat and video chat\r\nChat directly within Gmail. You can even talk face-to-face with built-in\r\nvideo chat.\r\n http://www.example.com/ \r\n3. Labels instead of folders\r\nLabels do the work of folders with an extra bonus: you can add more than\r\none to an email.\r\n http://www.example\r\n.com/linesplit \r\n[image: Conversation screenshot]\r\n\r\n4. Conversation view\r\nGmail groups emails and their replies in your inbox, so you always see your\r\nmessages in the context of your conversation. Related messages are stacked\r\nneatly on top of each other, like a deck of cards.\r\n\r\nWelcome!\r\n\r\n- The Gmail Team\r\n\r\n--002215974a724558c304d6ceeea0\r\nContent-Type: text/html; charset=ISO-8859-1\r\n\r\n<html>\r\n<font face="Arial, Helvetica, sans-serif">\r\n\r\n<p>\r\n<span style="font-size: 120%; font-weight: bold">4 things you need to know</span>\r\n<br />\r\nGmail is a little bit different. Learn these 4 basics and you\'ll never\r\nlook back.</p>\r\n\r\n<img width="297" height="225" src="https://mail.google.com/mail/images/welcome-inbox-screenshot.png" alt="Inbox screenshot" style="float: left; margin-right: 2em" />\r\n\r\n<p>\r\n<span style="font-size: 120%; font-weight: bold; white-space: nowrap">1. Archive instead of delete</span>\r\n<br />\r\nTidy up your inbox without deleting anything. You can always search to find\r\nwhat you need or look in "All Mail."</p>\r\n\r\n<p>\r\n<span style="font-size: 120%; font-weight: bold; white-space: nowrap">2. Chat and video chat</span>\r\n<br />\r\nChat directly within Gmail. You can even talk face-to-face with built-in video\r\nchat.</p>\r\n\r\n<p>\r\n<span style="font-size: 120%; font-weight: bold; white-space: nowrap">3. Labels instead of folders</span>\r\n<br />\r\nLabels do the work of folders with an extra bonus: you can add more than one to\r\nan email.</p>\r\n\r\n<p style="clear: left">&nbsp;</p>\r\n\r\n<img width="293" height="111" src="https://mail.google.com/mail/images/welcome-conversation-screenshot.png" alt="Conversation screenshot" style="float: left; margin-right: 2em" />\r\n\r\n<p>\r\n<span style="font-size: 120%; font-weight: bold; white-space: nowrap">4. Conversation view</span>\r\n<br />\r\nGmail groups emails and their replies in your inbox, so you always see your\r\nmessages in the context of your conversation. Related messages are stacked\r\nneatly on top of each other, like a deck of cards.</p>\r\n\r\n<div style="clear: left"></div>\r\n\r\n<p>Welcome!</p>\r\n\r\n<p>- The Gmail Team</p>\r\n\r\n</font>\r\n</html>\r\n\r\n--002215974a724558c304d6ceeea0--',
                    ),
                    ]

        for (urlList, contents) in testEmails:
            # Check the equality of these as sets, cause order doesn't matter
            self.assertEqual(set(urlList),
                    set(EmailData(contents).extractURLs()))


if __name__ == "__main__":
    unittest.main()
