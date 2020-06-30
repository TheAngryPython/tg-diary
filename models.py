from peewee import *
import uuid
import datetime

db = SqliteDatabase('db.sqlite3')

class BaseModel(Model):
    class Meta:
        database = db

class Chat(BaseModel):
    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    chat_id = IntegerField(unique=True)

class User(BaseModel):
    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = IntegerField(unique=True)
    register_date = DateTimeField(default=datetime.datetime.now)
    username = CharField(default=None, null = True)
    firstname = CharField()
    lastname = CharField(default=None, null = True)
    lang = TextField(default='en')
    action = TextField(default=None, null = True)
    tmp = TextField(default=None, null = True)
    messages = IntegerField(default=0)

class Data(BaseModel):
    uuid = UUIDField(primary_key=True, default=uuid.uuid4)
    user = ForeignKeyField(User)
    name = TextField()
    data = TextField()
    creation_date = DateField(default=datetime.datetime.now)
    salt = TextField()

db.connect()
db.create_tables([Chat, User, Data])
