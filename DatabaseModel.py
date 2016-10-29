#import cymysql
#cymysql.install_as_MySQLdb()

import peewee as pw

#TODO: import these settings from elsewhere
#dbSettings={"database": "malmail", "host": "localhost",
#                "user": "malmail", "passwd": "malmail"}

#database = pw.MySQLDatabase(**dbSettings)
database = pw.SqliteDatabase("malmail.db")

class MalmailModel(pw.Model):
    id = pw.PrimaryKeyField()
    class Meta:
        database = database

BASE_CLASS = MalmailModel

class Email(MalmailModel):
    fromAddress = pw.CharField(max_length=256)
    toAddress = pw.CharField(max_length=256)
    fromFriend = pw.BooleanField()
    content = pw.CharField(max_length=1024)

class Domain(MalmailModel):
    url = pw.CharField(max_length=256)

class URL(MalmailModel):
    domain = pw.ForeignKeyField(Domain) #TODO: what implication does this have for foreign key constraints? (cascading...)
    url = pw.CharField(max_length=2083)
    processed = pw.BooleanField()

class Content(MalmailModel):
    content = pw.CharField(max_length=1024) #TODO: varbinary?

class HTML_Content(Content):
    pass

class JS_Content(Content):
    pass

class Other_Content(Content):
    pass

class URL_To_Email(MalmailModel):
    email = pw.ForeignKeyField(Email)
    url = pw.ForeignKeyField(URL)

class URL_To_URL(MalmailModel):
    source_url = pw.ForeignKeyField(URL, related_name="source_url")
    contained_url = pw.ForeignKeyField(URL, related_name="contained_url")
    userAgent = pw.CharField(max_length=4096)

class HTML_To_URL(MalmailModel):
    content = pw.ForeignKeyField(HTML_Content)
    url = pw.ForeignKeyField(URL)
    userAgent = pw.CharField(max_length=4096)

class JS_To_URL(MalmailModel):
    content = pw.ForeignKeyField(JS_Content)
    url = pw.ForeignKeyField(URL)
    userAgent = pw.CharField(max_length=4096)

class Other_To_URL(MalmailModel):
    content = pw.ForeignKeyField(Other_Content)
    url = pw.ForeignKeyField(URL)
    userAgent = pw.CharField(max_length=4096)
