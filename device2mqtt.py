#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# device
#    Provides device tracking and alarms
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"


APPNAME = "device2mqtt"
VERSION = "0.8"
WATCHTOPIC = "/raw/" + APPNAME + "/command"

import sys
import os
import mosquitto
import socket
import time
import subprocess
from gi.repository import NetworkManager, NMClient
import logging
import signal
import pynotify
import threading
from config import Config
import commands
from daemon import Daemon
from mqttcore import MQTTClientCore
from mqttcore import main


class MyMQTTClientCore(MQTTClientCore):
    def __init__(self, appname, clienttype):
        MQTTClientCore.__init__(self, appname, clienttype)
        self.clientversion = VERSION
        self.watchtopic = WATCHTOPIC
        self.clientversion = VERSION 
        self.alarmfile = self.cfg.ALARMFILE

        t = threading.Thread(target=self.do_thread_loop)
        t.start()

    def on_connect(self, mself, obj, rc):
        MQTTClientCore.on_connect(self, mself, obj, rc)
        self.mqttc.subscribe(self.watchtopic, 2)

    def on_message(self, mself, obj, msg):
        MQTTClientCore.on_message(self, mself, obj, msg)
        if ( msg.topic == self.watchtopic ):
            if ( msg.payload == "stolen" ):
                p2 = subprocess.Popen( "/usr/bin/amixer set Master 100" )
                p3 = subprocess.Popen( "/usr/bin/amixer set Master unmute" )
                p = subprocess.Popen( "mplayer " + self.alarmfile, shell = True )
                p.wait()
                print "stolen"
        else:
            print "unknown command"

    def do_thread_loop(self):
        while ( self.running ):
            if ( self.mqtt_connected ):    
                    #publish external IP
                    p = subprocess.Popen( "curl ifconfig.me/ip", shell = True, stdout = subprocess.PIPE )
                    myip = p.stdout.readline()
                    self.mqttc.publish( "/device/" + self.clientname + "/ip_ext", myip.strip('\n'), qos=1, retain=True)

                    #publish internal IP
                    p = subprocess.Popen( "curl ifconfig.me/forwarded", shell = True, stdout = subprocess.PIPE )
                    myip = p.stdout.readline()
                    self.mqttc.publish( "/device/" + self.clientname + "/ip", myip.strip('\n'), qos=1, retain=True)

                    #publish SSID's
                    nmc = NMClient.Client.new()
                    devs = nmc.get_devices()
                    ssids = ""
                    bssids = ""
                    for dev in devs:
                        if dev.get_device_type() == NetworkManager.DeviceType.WIFI:
                            for ap in dev.get_access_points():
                                ssids += "\n"
                                ssids += ap.get_ssid()
                                bssids += "\n"
                                bssids += ap.get_bssid()
                    self.mqttc.publish( "/device/" + self.clientname + "/ssids", ssids, qos=1, retain=True)
                    self.mqttc.publish( "/device/" + self.clientname + "/bssids", bssids, qos=1, retain=True)

                    #publish time of update
                    self.mqttc.publish( "/device/" + self.clientname + "/time", time.strftime( "%x %X" ), qos=1, retain=True)
                    count = 60
                    while ( self.mqtt_connected and ( count != 0 )):
                        count -= 1
                        time.sleep(10)


class MyDaemon(Daemon):
    def run(self):
        mqttcore = MyMQTTClientCore(APPNAME, clienttype="type2")
        mqttcore.main_loop()


if __name__ == "__main__":
    daemon = MyDaemon('/tmp/' + APPNAME + '.pid')
    main(daemon)
