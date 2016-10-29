#!/usr/bin/env python3

import argparse
from collections import defaultdict
import tempfile
import os.path
import urllib.request as urlReq
import urllib.error as urlErr
import sys

import ContentHandlers as ch
from Common import *

userAgents = [
                # Chrome - OS X
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_7) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.790.0 Safari/535.1",
                # Chrome - Linux
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.1 (KHTML, like Gecko) Ubuntu/11.04 Chromium/13.0.782.41 Chrome/13.0.782.41 Safari/535.1",
                # Chrome - Windows XP
                "Mozilla/5.0 (Windows NT 5.1) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.792.0 Safari/535.1",
                # Firefox - Win XP
                "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0",
                # Firefox - Linux
                "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1",
                # Firefox - OS X
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:9.0a2) Gecko/20111101 Firefox/9.0a2",
                # Internet Explorer 8 - Win XP
                "Mozilla/5.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727)",
                # Internet Explorer 9 - Win 7
                "Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Win64; x64; Trident/5.0; .NET CLR 3.5.30729; .NET CLR 3.0.30729; .NET CLR 2.0.50727; Media Center PC 6.0)",
                # Internet Explorer 5.5 - Win 98
                "Mozilla/4.0 (compatible;MSIE 5.5; Windows 98)"
]

class URLContentsListEntry():
    """Store user agents and contents"""
    def __init__(self, userAgents=None, contents=None):
        self.userAgents = [] if userAgents is None else userAgents
                # A list of user agents that produced these contents
        self.contents = contents # The specific contents

def retrieveURLWithEachUserAgent(url, userAgents=userAgents, timeout=2):
    """Retrieve the contents of the URL with all user agents.

            url: a url string
            userAgents: a list of User Agent strings.  Defaults to the built-in list

            Return value: [URLContentsListEntry, URLContentsListEntry, ...]
            """
    def _retrieveURL(userAgent):
        request = urlReq.Request(url, headers={"User-Agent": userAgent})
        with urlReq.urlopen(request, timeout=timeout) as connection:
            return ch.WebData(connection, request)

    try: # Detect an invalid URL early
        urlReq.Request(url)
    except ValueError as err:
        print_error("Invalid URL:", url, "Exception:", err)
        return []

    responses = defaultdict(list)
    for uA in userAgents:
        try:
            response = _retrieveURL(uA)
        except urlErr.HTTPError as err:
            print_error("HTTP error retrieving URL:", url, "Agent:", uA,
                            "Code:", err.code, "Reason:", err.reason)
        except urlErr.URLError as err:
            if ((type(err.reason) is str) and
                            err.reason.startswith("unknown url type")):
                print_error("Invalid URL:", url, "Reason:", err.reason)
            else:
                print_error("URL error retrieving URL:", url, "Agent:", uA,
                                "Reason:", err.reason)
            return [] # URLErrors are regardless of agent, so don't try other agents
        except Exception as err:
            print_error("Unknown error retrieving URL:", url, "Agent:", uA,
                            "Exception:", err)
        else:
            responses[response].append(uA)

    return [URLContentsListEntry(userAgents=agents, contents=response)
                    for (response, agents) in responses.items()]

def outputURLContentsList(contentsList, basepath):
    """Output a set of URL contents to files in a directory.

            contentsList: [URLContentsListEntry, URLContentsListEntry, ...]
            basepath: a string path of the directory to output each contents in

            Return value: the log file containing the user agent to output file map
            """
    with tempfile.NamedTemporaryFile(dir=basepath, delete=False,
                    prefix="log", mode="w") as logfile:
        for entry in contentsList:
            if isinstance(entry.contents.body(), bytes):
                mode = "wb"
            else:
                mode = "w"
            with tempfile.NamedTemporaryFile(dir=basepath, delete=False,
                            mode=mode) as outfile:
                outfile.write(entry.contents.body())
            logfile.write("{0} - {1}\n".format(entry.userAgents, outfile.name))
            if entry.contents.redirect:
                logfile.write("------ {0}".format(entry.contents.redirect))
    return logfile.name

def main():
    parser = argparse.ArgumentParser(
                    description="Retrieve URL contents with multiple User Agent strings.")
    parser.add_argument("-d", "--dir", default="./",
                    help="The directory to store output in.")
    parser.add_argument("URL", help="The URL to retrieve.")

    args = parser.parse_args()
    outputDir = os.path.abspath(args.dir)
    url = args.URL

    if os.path.exists(outputDir) and not os.path.isdir(outputDir):
        print("Output directory file exists but is not a directory:",
                        format(outputDir))
        exit(1)
    elif not os.path.isdir(outputDir):
        os.mkdir(outputDir)

    outputURLContentsList(retrieveURLWithEachUserAgent(url), outputDir)

if __name__=="__main__":
    main()
