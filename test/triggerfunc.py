from __future__ import print_function

import sys
import os

current_directory = os.path.split(os.path.abspath(__file__))[0]
sys.path.append(current_directory + "/" + "..")

import hive


def print_ping():
    print("PING")


def print_pong():
    print("PONG")


def test_empty_triggerfunc():
    """Trigger function will trigger associated triggerable"""
    hive_pang = hive.triggerfunc()
    hive_pong = hive.triggerable(print_pong)
    hive.trigger(hive_pang, hive_pong)

    hive_pang()


def test_callable_triggerfunc():
    """Trigger function will trigger associated triggerable, after first calling triggerfunc wrapped function"""
    hive_ping = hive.triggerfunc(print_ping)
    hive_pong = hive.triggerable(print_pong)
    hive.trigger(hive_ping, hive_pong)

    hive_ping()


test_empty_triggerfunc()
test_callable_triggerfunc()