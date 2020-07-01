
   #############################################################
   #                     by Egor Ternovoi                      #
   #       https://github.com/TheAngryPython/watchdog_py       #
   #                        TG: EgTer                          #
   #                           2020                            #
   #############################################################

# SETTINGS
import os
command = "python3 bot.py"
path = os.path.dirname(os.path.abspath(__file__))
delimiter = "/"
whitelist = ['bot.py']

# CODE

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time, subprocess as s
p = s.Popen(command.split())
class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        global p
        print('MODIFED',event.src_path)
        spl = event.src_path.split(delimiter)
        if spl[len(spl)-1] in whitelist:
            print('MODIFED',event.src_path,'reloading!')
            p.kill()
            p = s.Popen(command.split())
            print('STARTED!')

observer = Observer()
observer.schedule(Handler(), path=path, recursive=True)
observer.start()

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
