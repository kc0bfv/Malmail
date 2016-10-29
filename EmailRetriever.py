#!/usr/bin/env python3

import imaplib
import itertools as it
import unittest
import socket

from EmailAcctData import server_details
import ContentHandlers as ch

class EmailRetrieverException(Exception):
    instanceMessage=""
    def __init__(self, imapException):
        self.value = self.instanceMessage + ": " + str(imapException)

    def __str__(self):
        return self.value

class ErrorConnecting(EmailRetrieverException):
    instanceMessage = "Failed to connect to server"

class ErrorLoggingIn(EmailRetrieverException):
    instanceMessage = "Failed to login"

class ErrorSettingDirectory(EmailRetrieverException):
    instanceMessage = "Failed to set directory"

class ErrorRetrieving(EmailRetrieverException):
    instanceMessage = "Failed to retrieve emails"


class EmailRetriever():
    """Enables simple email retrieval with a 'with' statement.

            Intended use:
                    with EmailRetriever(**options) as emailConnection:
                            for email in emailConnection:
                                    process(email)

            Return value: an iterator that yields ContentHandler.EmailData instances
            """

    def __init__(self, hostname, port, username, password, unseenOnly=True,
                    useSSL=True, directory="INBOX"):
        self.serverDetails = {"host": hostname, "port": port}
        self.userDetails = {"user": username, "password": password}
        self.directory = directory
        self.useSSL = useSSL
        self.unseenOnly = unseenOnly

    def __enter__(self):
        imapClass = imaplib.IMAP4_SSL if self.useSSL else imaplib.IMAP4

        try:
            self.imapObject = imapClass(**self.serverDetails)
        except socket.gaierror as exc:
            raise ErrorConnecting(exc) from exc
        except imaplib.IMAP4.error as exc:
            raise ErrorConnecting(exc) from exc

        try:
            self.imapObject.login(**self.userDetails)
        except imaplib.IMAP4.error as exc:
            raise ErrorLoggingIn(exc) from exc

        return self._emailGenerator()

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.imapObject.logout()
        except:
            pass


    def _emailGenerator(self):
        """Returns data from the email.

                Yield value: ContentHandlers.EmailData instances
                """
        def _extractEmail(emailDataList):
            return emailDataList[0][1]

        searchStr = "UNSEEN" if self.unseenOnly else "ALL"

        try:
            (success, response) = self.imapObject.select(self.directory)
        except imaplib.IMAP4.error as exc:
            raise ErrorSettingDirectory(exc)
        else:
            if success != "OK":
                raise ErrorSettingDirectory(response)
            try:
                (_, uidSpaceSeparated) = self.imapObject.uid("search", None, searchStr)
                uidList = uidSpaceSeparated[0].split()
                for uid in uidList:
                    (_, emailDataList) = self.imapObject.uid("fetch", uid, "(RFC822)")
                    yield ch.EmailData(_extractEmail(emailDataList))

            except imaplib.IMAP4.error as exc:
                raise ErrorRetrieving(exc)

            finally:
                try:
                    self.imapObject.close()
                except:
                    pass





class EmailRetrieverTester(unittest.TestCase):
    def setUp(self):
        self.setupOptions = server_details.copy()
        self.setupOptions["unseenOnly"] = False

    def test_retrieveMail(self):
        numToGet = 3

        with EmailRetriever(**self.setupOptions) as emailConnection:
            # Just retrieve 3 emails...
            emails = [email for (_, email) in zip(range(numToGet), emailConnection)]

        self.assertEqual(len(emails), numToGet)

    def test_wrongUsername(self):
        self.setupOptions["username"] = "wrong"
        self.assertRaises(ErrorLoggingIn, self.run_with, self.setupOptions)

    def test_wrongServer(self):
        self.setupOptions["hostname"] = "wrong"
        self.assertRaises(ErrorConnecting, self.run_with, self.setupOptions)

    def test_wrongDirectory(self):
        self.setupOptions["directory"] = "_wrong_DOES_NOT_EXIST"
        self.assertRaises(ErrorSettingDirectory, self.run_with, self.setupOptions)

    def run_with(self, options):
        with EmailRetriever(**options) as email:
            retrieveOne = next(email)
        return True


if __name__ == "__main__":
    unittest.main()
