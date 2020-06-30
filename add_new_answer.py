# -*- coding: utf-8 -*-
import json, requests
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

key = json.loads(open('cfg.txt', 'r').read())['yandex']
langs = ['ru', 'en', 'it', 'fr', 'de', 'uk', 'pl']
format = 'https://translate.yandex.net/api/v1.5/tr.json/translate?key={key}&text={text}&lang={lang}&format=plain'
orig = input(f'orig ({langs[0]}): ') or langs[0]
while orig not in langs:
    print('orig not in langs!')
    orig = input(f'orig ({langs[0]}): ') or langs[0]

while 1:
    try:
        lst = []
        name = input('name: ')
        print('value: ', end='')
        while 1:
            inp = input()
            if inp.find('EOF') != -1:
                t=inp.replace('EOF','')
                if t:
                    lst.append(t)
                val = '\n'.join(lst)
                break
            else:
                lst.append(inp)
        cfg = {}
        cfg[orig] = val
        for lang in langs:
            if lang == orig:
                continue
            print(f'requesting {lang}:')
            answer = json.loads(requests.get(format.format(lang=lang,text=val,key=key)).text)['text'][0]
            cfg[lang] = answer
            print(answer)
        try:
            l = Lang.get(name=name)
            l.langs = json.dumps(cfg)
            l.save()
        except:
            l = Lang(name=name, langs=json.dumps(cfg))
            l.save()
    except:
        print('exit')
        break

db.close()
