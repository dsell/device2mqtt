#!/usr/bin/python
# -*- coding: utf-8 -*-
# vim tabstop=4 expandtab shiftwidth=4 softtabstop=4

#
# device
#	Provides device tracking and alarms
#


__author__ = "Dennis Sell"
__copyright__ = "Copyright (C) Dennis Sell"



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


MYID = socket.gethostname()
CLIENT_NAME = "device2mqtt[" + MYID + "]"
CLIENT_VERSION = "0.6"
CLIENT_TOPIC = "/client/" + CLIENT_NAME + "/" 
MQTT_TIMEOUT = 60	#seconds
WATCH_TOPIC = "/device/" + MYID + "/command"
LOGFORMAT = '%(asctime) - 15s %(message)s'
LOGFILE = "/var/log/mqtt-growl.log"


#TODO might want to add a lock file
#TODO  need to deal with no config file existing!!!
#read in configuration file
homedir = os.path.expanduser("~")
f = file(homedir + '/.device2mqtt.conf')
cfg = Config(f)
MQTT_HOST = cfg.MQTT_HOST
MQTT_PORT = cfg.MQTT_PORT
ALARMFILE = cfg.ALARMFILE
#TODO  need to finish using config values

mqtt_connected = False


#define what happens after connection
def on_connect( self, obj, rc):
	global mqtt_connected
	mqtt_connected = True
	print "MQTT Connected"
	mqttc.publish ( "/clients/" + CLIENT_NAME + "/status" , "connected", 1, 1 )
	mqttc.publish( "/clients/" + CLIENT_NAME + "/version", CLIENT_VERSION, 1, 1 )
	mqttc.subscribe( WATCH_TOPIC, 2 )
	mqttc.subscribe( CLIENT_TOPIC + "ping", 2)


def on_disconnect( self, obj, rc ):
	pass


#On recipt of a message create a pynotification and show it
def on_message( self, obj, msg):
	if (( msg.topic == CLIENT_BASE + "ping" ) and ( msg.payload == "request" )):
		mqttc.publish( CLIENT_BASE + "ping", "response", qos = 1, retain = 0 )
	else:
		if ( msg.payload == "stolen" ):
	#		p2 = subprocess.Popen( "/usr/bin/amixer set Master 100" )
	#		p3 = subprocess.Popen( "/usr/bin/amixer set Master unmute" )
			p = subprocess.Popen( "mplayer " + ALARMFILE, shell = True )
			p.wait()
			print "stolen"
		else:
			print "unknown command"


def do_update_loop():
	global mqtt_connected
	global running
	while running:
		if (mqtt_connected ):
			#publish external IP
			p = subprocess.Popen( "curl ifconfig.me/ip", shell = True, stdout = subprocess.PIPE )
			myip = p.stdout.readline()
			mqttc.publish( "/device/" + MYID + "/ip", myip.strip('\n'), 1, 1 )

			#publish internal IP
			p = subprocess.Popen( "curl ifconfig.me/forwarded", shell = True, stdout = subprocess.PIPE )
			myip = p.stdout.readline()
			mqttc.publish( "/device/" + MYID + "/internal", myip.strip('\n'), 1, 1 )

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
			mqttc.publish( "/device/" + MYID + "/ssids", ssids, 1, 1 )
			mqttc.publish( "/device/" + MYID + "/bssids", bssids, 1, 1 )

			#publish time of update
			mqttc.publish( "/device/" + MYID + "/time", time.strftime( "%x %X" ), 1, retain=1 )
			count = 60
			while ( mqtt_connected and ( count != 0 )):
				count -= 1
				time.sleep(10)
		else:
			time.sleep(30)


def mqtt_connect():
	rc = 1
	while ( rc ):
		print "Attempting connection..."
		mqttc.will_set("/clients/" + CLIENT_NAME + "/status", "disconnected_", 1, 1)

		#define the mqtt callbacks
		mqttc.on_message = on_message
		mqttc.on_connect = on_connect
		mqttc.on_disconnect = on_disconnect

		#connect
		rc = mqttc.connect( MQTT_HOST, MQTT_PORT, MQTT_TIMEOUT )
		if rc != 0:
			logging.info( "Connection failed with error code $s, Retrying", rc )
			print "Connection failed with error code ", rc, ", Retrying in 30 seconds."
			time.sleep(30)
		else:
			print "Connect initiated OK"


def mqtt_disconnect():
	global mqtt_connected
	if ( mqtt_connected ):
		mqtt_connected = False 
		print "MQTT Disconnected"
	mqttc.disconnect()


def cleanup(signum, frame):
	global running
	running = False
	mqtt_disconnect()
	sys.exit(signum)


#create an mqtt client
mqttc = mosquitto.Mosquitto( CLIENT_NAME )

#trap kill signals including control-c
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

running = True

t = threading.Thread(target=do_update_loop)
t.start()

def main_loop():
	global mqtt_connected
	mqttc.loop(10)
	while True:
		if ( mqtt_connected ):
			rc = mqttc.loop(10)
			if rc != 0:	
				mqtt_disconnect()
	#			print rc
				print "Stalling for 20 seconds to allow broker connection to time out."
				time.sleep(20)
				mqtt_connect()
				mqttc.loop(10)
		pass


mqtt_connect()
main_loop()















