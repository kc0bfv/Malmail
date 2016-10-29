#!/usr/bin/env python3
"""
Script creates all missing tables in the database.
"""

from DatabaseModel import database, BASE_CLASS

def create_tables():
    """
    Creates all the missing tables in the database
    """
    database.connect()

    subclasses = set([BASE_CLASS])
    len_prev = -1
    while len_prev != len(subclasses):
        len_prev = len(subclasses)
        for subc in set(subclasses):
            subclasses.update(subc.__subclasses__())
    subclasses.remove(BASE_CLASS)
    for subc in subclasses:
        if not subc.table_exists():
            subc.create_table()
            print("Created {}".format(subc))

    database.close()

if __name__ == "__main__":
    create_tables()
