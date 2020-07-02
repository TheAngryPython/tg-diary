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

commands = [{'command':'start', 'description':'start'}, {'command':'add', 'description':'add record'}, {'command':'all', 'description':'show records'}, {'command':'del', 'description':'delete record'}, {'command':'help', 'description':'help'}, {'command':'settings', 'description':'settings'}, {'command':'stop', 'description':'stop'}, ]
requests.get(f'https://api.telegram.org/bot{cfg["token"]}/setMyCommands?commands={json.dumps(commands)}')

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
    msg_id = event.id
    text = event.message.message
    try:
        await client.delete_messages(chat_id, [msg_id])
    except:
        pass
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
        limit = 100
        if len(text) > limit:
            await client.send_message(chat_id, gt('too_long', lang).format(**locals()))
        else:
            user.tmp = json.dumps({'name':text + ' ' + str(datetime.datetime.now())})
            user.action = 'add_data'
            await client.send_message(chat_id, gt('add_data', lang))
    elif user.action == 'add_data':
        limit = 3700
        if len(text) > limit:
            await client.send_message(chat_id, gt('too_long', lang).format(**locals()))
        else:
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
    elif user.action == 'settings':
        if text.lower() not in langs:
            await client.send_message(chat_id, gt('settings_err', lang))
        else:
            user.lang = text.lower()
            user.tmp = None
            user.action = None
            await client.send_message(chat_id, gt('settings_successful', text.lower()).format(**locals()))
    elif user.action == 'all_start':
        try:
            d = models.Data.filter(user=user)
            d[int(text)-1]
            user.tmp = json.dumps({'number':int(text)-1})
            user.action = 'all_pass'
            await client.send_message(chat_id, gt('all_pass', lang))
        except:
            await client.send_message(chat_id, gt('all_err', lang))
    elif user.action == 'del_start':
        try:
            d = models.Data.filter(user=user)
            d[int(text)-1].delete_instance()
            user.tmp = None
            user.action = None
            await client.send_message(chat_id, gt('done', lang))
        except:
            await client.send_message(chat_id, gt('all_err', lang))
    elif user.action == 'all_pass':
        try:
            d = models.Data.filter(user=user)
            d = d[tmp['number']]
            salt = d.salt
            try:
                data = decrypt(text, salt, d.data)
                user.tmp = None
                user.action = None
                await client.send_message(chat_id, gt('block', lang).format(**locals()))
            except:
                await client.send_message(chat_id, gt('pass_incorrect', lang))
        except:
            await client.send_message(chat_id, gt('error', lang))
    elif user.action == 'delete_start':
        if text.lower() == 'yes':
            user.delete_instance()
            for d in models.Data.filter(user=user):
                d.delete_instance()
            await client.send_message(chat_id, 'Success!')
        else:
            user.tmp = None
            user.action = None
            await client.send_message(chat_id, 'Stopped!')
    elif text == '/start':
        await client.send_message(chat_id, gt('start', lang))
    elif text == '/add':
        user.action = 'add_start'
        await client.send_message(chat_id, gt('add_start', lang))
    elif text == '/all':
        d = models.Data.filter(user=user)
        if d.count() == 0:
            await client.send_message(chat_id, gt('all_none', lang))
        else:
            user.action = 'all_start'
            t = gt('all_start', lang)+'\n\n'
            i = 1
            for s in d:
                t += f'{i}. {s.name}\n\n'
                i += 1
            t += gt('all_enter', lang)
            lst = []
            while len(t) > 2500:
                lst.append(t[:2500])
                t = t.replace(t[:2500], '')
            lst.append(t)
            for i in lst:
                await client.send_message(chat_id, i)
    elif text == '/settings':
        user.action = 'settings'
        await client.send_message(chat_id, gt('settings_start', lang) + "'ru', 'en', 'it', 'fr', 'de', 'uk', 'pl'")
    elif text == '/help':
        user.tmp = None
        user.action = None
        await client.send_message(chat_id, gt('help', lang))
    elif text == '/del' or text == '/delete':
        d = models.Data.filter(user=user)
        if d.count() == 0:
            await client.send_message(chat_id, gt('all_none', lang))
        else:
            user.tmp = None
            user.action = 'del_start'
            t = '\n\n'
            i = 1
            for s in d:
                t += f'{i}. {s.name}\n\n'
                i += 1
            await client.send_message(chat_id, gt('all_start', lang)+t+gt('all_enter', lang))
    elif text == '/get_data':
        name = f'{user_id}_{"".join(random.choices(string.ascii_letters + string.digits, k = 24))}--get--data--.json'
        js = {}
        js['user'] = {'uuid':str(user.uuid),'user_id':user.user_id,'register_date':str(user.register_date),'username':user.username,'firstname':user.firstname,'lastname':user.lastname,'lang':user.lang,'action':user.action,'tmp':user.tmp,'messages':user.messages}
        js['blocks'] = []
        for d in models.Data.filter(user=user):
            js['blocks'].append({'uuid':str(d.uuid),'name':d.name,'data':d.data,'creation_date':str(d.creation_date),'salt':d.salt})
        f = open(name, 'w')
        f.write(json.dumps(js, indent=4))
        f.close()
        await client.send_file(chat_id, name)
        os.remove(name)
    elif text == '/delete_data':
        user.action = 'delete_start'
        await client.send_message(chat_id, gt('delete_start'))
    elif text.find('/amsg') != -1:
        if user_id == int(cfg['id']):
            msg = text.replace('/amsg ','').replace('/amsg','')
            key = cfg['yandex']
            format = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key={key}&text={text}&lang={lang}&format=plain'
            orig = 'ru'
            ans = {}
            for lang in langs:
                if lang == orig:
                    ans[orig] = msg
                    continue
                answer = json.loads(requests.get(format.format(lang=lang,text=msg,key=key)).text)['text'][0]
                ans[lang] = answer
            await client.send_message(chat_id, '\n\n'.join([ans[a] for a in ans]))
            for chat in models.Chat.select():
                await client.send_message(chat.chat_id, ans[user.lang])
    elif text == '/db':
        if user_id == int(cfg['id']):
            await client.send_file(chat_id, 'db.sqlite3')
    else:
        await client.send_message(chat_id, gt('not_recognized', lang))

    try:
        user.save()
    except:
        pass

client.start()
client.run_until_disconnected()
