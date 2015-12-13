import threading

import hive as h
from .getch import change_termios, restore_termios, raw_input


class commandlineclass(object):
    command = None
    def __init__(self):
        self._hive = h.get_run_hive()
        self._commands = []
        self._listeners = []
        self._running = False
    def _new_command(self, command):
        self._commands.append(command)
    def start(self):
        if self._running: return
        def gcom(event, addcomfunc):
            try:
                while not event.is_set():
                    try:
                        com = raw_input(">>>")
                        if com != None:
                            addcomfunc(com)
                    except EOFError:
                        pass
            finally:
                restore_termios()
        change_termios()
        self.dead = threading.Event()
        t = threading.Thread(target=gcom, args=(self.dead, self._new_command,))    
        t.daemon = True
        t.start()
    def stop(self):
        if self._running:
            self._running = False
            self.dead.set()
    def add_listener(self, listener):
        assert callable(listener), listener
        self._listeners.append(listener)
    def send_command(self, command):
        for listener in self._listeners:
            listener(command)
    def flush(self):
        for c in self._commands:
            self.send_command(c)
            self.command = c
            self._hive._push_command()
        self._commands = []
                
def build_commandline(cls, i, ex, args):
    i.start = h.triggerable(cls.start)    
    i.stop = h.triggerable(cls.stop)
    i.flush = h.triggerable(cls.flush)
    prop_command = h.property(cls,"command", "str")
    i.push_command = h.push_out(prop_command)
    
    ex.prop_command = prop_command
    ex.command = h.output(i.push_command)
    ex.send_command = cls.send_command
    ex.start = h.entry(i.start)    
    ex.flush = h.entry(i.flush)
    ex.stop = h.entry(i.stop)
    ex.listen = h.socket(cls.add_listener)
    
Commandline = h.hive("commandline", build_commandline, commandlineclass)