import base64
import pyaes
from pbkdf2 import PBKDF2
import random, string
import os
import sys
import models
import json
import requests
import time
from telethon import TelegramClient, events, Button
import logging
import datetime
from peewee import *

db = SqliteDatabase('langs.sqlite3')

class BaseModel(Model):
    class Meta:
        database = db

class Lang(BaseModel):
    name = TextField()
    langs = TextField()

db.connect()
db.create_tables([Lang])

file_log = logging.FileHandler('log.log')
console_out = logging.StreamHandler()
logging.basicConfig(handlers=(file_log, console_out), format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s',
                    level=logging.WARNING)

cfg = json.loads(open('cfg.txt', 'r').read())

langs = ['ru', 'en', 'it', 'fr', 'de', 'uk', 'pl']

api_id = cfg['appid']
api_hash = cfg['apphash']

def encrypt(key, text):
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k = 12))
    key = PBKDF2(key, salt).read(32)
    aes = pyaes.AESModeOfOperationCTR(key)
    ciphertext = aes.encrypt(text.encode('utf-8'))
    return (salt, base64.b64encode(ciphertext).decode())

def decrypt(key, salt, text):
    key = PBKDF2(key, salt).read(32)
    text = base64.b64decode(text)
    aes = pyaes.AESModeOfOperationCTR(key)
    decrypted = aes.decrypt(text)
    return decrypted.decode('utf-8')

def gt(name, lang='en'):
    return json.loads(Lang.get(name=name).langs)[lang]

client = TelegramClient('bot', api_id, api_hash).start(bot_token=cfg['token'])

@client.on(events.NewMessage)
async def new_msg(event):
    chat = await event.get_chat()
    sender = await event.get_sender()
    chat_id = event.chat_id
    user_id = event.sender_id
    text = event.message.message
    try:
        models.Chat.get(chat_id=chat_id)
    except:
        c = models.Chat.create(chat_id=chat_id)
        c.save()
    try:
        user = models.User.get(user_id=user_id)
        user.username = sender.username
        user.firstname = sender.first_name
        user.lastname = sender.last_name
    except:
        lang = sender.lang_code
        if sender.lang_code not in langs:
            lang = 'en'
        user = models.User.create(user_id=user_id, username=sender.username,
        firstname=sender.first_name, lastname=sender.last_name, lang=lang)
    user.save()
    user.messages += 1
    lang = user.lang
    if user.tmp:
        tmp = json.loads(user.tmp)

    if text.lower() == 'stop' or text == '/stop':
        user.tmp = None
        user.action = None
        await client.send_message(chat_id, 'Stopped!')
    elif user.action == 'add_start':
        user.tmp = json.dumps({'name':text + str(datetime.datetime.now())})
        user.action = 'add_data'
        await client.send_message(chat_id, gt('add_data', lang))
    elif user.action == 'add_data':
        tmp['data'] = text
        user.tmp = json.dumps(tmp)
        user.action = 'add_pass'
        await client.send_message(chat_id, gt('add_pass', lang))
    elif user.action == 'add_pass':
        salt, data = encrypt(text, tmp['data'])
        user.tmp = None
        user.action = None
        d = models.Data.create(user=user, name=tmp['name'], data=data, salt=salt)
        d.save()
        await client.send_message(chat_id, gt('add_end', lang))
    elif text == '/start':
        await client.send_message(chat_id, gt('start', lang))
    elif text == '/add':
        user.action = 'add_start'
        await client.send_message(chat_id, gt('add_start', lang))
    elif text == '/all':
        if models.Data.filter(user=user).count() == 0:
            await client.send_message(chat_id, gt('all_none', lang))
        else:
            user.action = 'all_start'
            markup = client.build_reply_markup(Button.text('hi'))
            await client.send_message(chat_id, gt('all_start', lang), buttons=markup)

    user.save()

client.start()
client.run_until_disconnected()
