#!/usr/bin/env python3
"""
Run a round of data importing and processing
"""

import HighLevelFunctionality as hlf
from EmailAcctData import server_details

ONLY_UNSEEN = True

if __name__ == "__main__":
    hlf.retrieve_emails_into_database(server_details.copy(), ONLY_UNSEEN)
    hlf.retrieve_urls_into_database(1)
    hlf.print_database()
