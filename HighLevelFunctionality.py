"""
Provide high-level functionality for ingesting data
"""

from DatabaseOperations import Database
from EmailRetriever import EmailRetriever
from RetrieveURLs import retrieveURLWithEachUserAgent

def retrieve_emails_into_database(email_server_opts, unseen_only=True):
    """
    Pull email from a server into the database

    :param dict email_server_opts:
        Information about the email server.  The dictionary should have the
        following keys: str hostname, int port, str username, str password

    :param bool unseen_only:
        Optional - Default True
        If true, only pull in emails that are marked unread
    """
    email_server_opts["unseenOnly"] = unseen_only

    with EmailRetriever(**email_server_opts) as email_connection:
        for email in email_connection:
            with Database() as dbo:
                email_id = dbo.addContent(email)
                urls = email.extractURLs()
                dbo.addURLs(urls, email_id, fromEmail=True)

def retrieve_urls_into_database(extract_depth=1):
    """
    Pull content from all unprocessed URLs into the database.  With all
    content it pulls in, extract the URLs and add them to the database.
    Repeat this process on the new URLs "extract_depth" number of times.

    :param int extract_depth:
        Optional - Default 1
        How many rounds of extraction to complete before quitting
    """
    with Database() as dbo:
        next_round_urls = dbo.getURLs()
        for _ in range(extract_depth):
            round_urls, next_round_urls = next_round_urls, list()

            for url in round_urls:
                print("Processing URL: {}".format(url))
                for url_contents in retrieveURLWithEachUserAgent(url):
                    dbo.addContent(
                        url_contents.contents, url, url_contents.userAgents)
                    contained_urls = url_contents.contents.extractURLs()
                    next_round_urls.extend(contained_urls)
                    dbo.addURLs(contained_urls, url, url_contents.userAgents)

            dbo.markURLsExplored(round_urls)

        dbo.markURLsExplored(next_round_urls)


def print_database():
    """
    Print the database content
    """
    with Database() as dbo:
        dbo.printDatabase()
