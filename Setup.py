#!/usr/bin/env python3

def write_config():
    filename = "EmailAcctData.py"

    try:
        from EmailAcctData import server_details
    except ImportError as e:
        server_details = {"hostname": "", "port": "993", "username": "",
                "password": ""}

    print("Malmail Setup")
    print(
"""This program will request information about the email account you wish to
look for malicious email in.  It will write that information in plaintext, as
a dictionary, to the file "{}" in the current directory.
""".format(filename))

    new = dict()
    new["hostname"] = input("IMAP Server Hostname ({}): ".format(
        server_details["hostname"]))
    new["port"] = input("IMAP Server Port ({}): ".format(
        server_details["port"]))
    new["username"] = input("Username ({}): ".format(
        server_details["username"]))
    new["password"] = input("Password ({}): ".format(
        server_details["password"]))

    for key, val in new.items():
        if val:
            server_details[key] = val

    with open(filename, "w") as f:
        f.write("server_details = {}".format(server_details))

if __name__ == "__main__":
    write_config()
