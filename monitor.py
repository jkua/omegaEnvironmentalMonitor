#!/usr/bin/env python

import paho.mqtt.client as mqtt
import ssl
import json
import time
from OmegaExpansion import onionI2C
from readTemp import SensorSHT31, SensorSHT25


class SensorPublisher(object):
    def __init__(self, sensors, order=None, alertSender=None, statsHour=None):
        self.sensors = sensors
        self.order = order
        if order is None:
            self.order = self.sensors.keys()
        else:
            self.order = order

        self.alertSender = alertSender
        self.statsHour = statsHour
        self.lastStatsTime = None

        self.client = mqtt.Client()

        # userdata contains the last connection status
        self.client.user_data_set(None)

        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message

    def connect(self, host, port, caFile, certFile, keyFile):
        self.client.tls_set(ca_certs=caFile, certfile=certFile, keyfile=keyFile, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
        self.client.connect(host, port, keepalive=60)

    def disconnect(self):
        self.client.disconnect()

    def start(self, pollInterval):
        self.client.loop_start()

        while 1:
            try:
                startTime = time.time()
                print('----')
                for key in self.order:
                    try:
                        sensor = self.sensors[key]
                        timestamp, (cTemp, fTemp, humidity) = sensor.read()
                        print('[{}] {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(timestamp), key.title(), cTemp, fTemp, humidity))
                        if not sensor.checkThresholds():
                            print('*** OVER THRESHOLD!!! ***')
                            self.sendAlert(key, timestamp, (cTemp, fTemp, humidity))
                        payload = self.buildPayload(cTemp, humidity)
                        fullTopic = '{}/{}'.format(args.topic, key)
                        result, mid = self.client.publish(fullTopic, payload, qos=1)
                    except IOError:
                        print('\n*** Failed to get data for {}, device {}!')
                if (time.localtime().hour == self.statsHour) and (self.lastStatsTime is None or ((time.time() - self.lastStatsTime) > 80000)):
                    statsStrings = []
                    try:
                        for key in self.order:
                            sensor = self.sensors[key]
                            meanVals, minVals, maxVals = sensor.stats()
                            statsStrings.append('{} - Mean: {:.1f} deg F, Min: {:.1f} deg F, Max: {:.1f} deg F'.format(key.title(), meanVals[1], minVals[1], maxVals[1]))
                        statsMessage = '\n'.join(statsStrings)
                        self.sendStats(statsMessage)
                        print('Sent stats message!')
                    except:
                        print('*** Failed to send stats message!')
                measurementTime = time.time() - startTime
                time.sleep(max(pollInterval-measurementTime, 0))
            except KeyboardInterrupt:
                break

        self.client.loop_stop()

    def buildPayload(self, temp, humidity):
        data = {'timestamp': time.time(),
                'temperature': temp,
                'humidity': humidity
               }
        jsonString = json.dumps(data)
        return jsonString

    def sendAlert(self, sensorName, timestamp, data):
        alertMessage = 'WINE CELLAR ALERT! {} sensor reads {:.2f} deg C/{:.1f} deg F, {.1f} %RH!'.format(sensorName.title(), data[0], data[1], data[2])
        self.sendMessage(alertMessage)

    def sendMessage(self, message):
        if self.alertSender is not None:
            self.alertSender.sendSmsMessage(message)

    # The callback for when the client receives a CONNACK response from the server.
    @staticmethod
    def on_connect(client, userdata, flags, rc):
        # userdata contains the last connection status
        if rc != userdata:
            print("\n*** Connected with result code "+str(rc) + '\n')
            client.user_data_set(rc)

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("$SYS/#")

    # The callback for when this client publishes to the server.
    @staticmethod
    def on_publish(client, userdata, mid):
        print("Message published")

    # The callback for when a PUBLISH message is received from the server.
    @staticmethod
    def on_message(client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))


if __name__=='__main__':
    from twilioSender import TwilioSender
    import os.path
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--poll', type=float, default=15., help='Polling interval in seconds')
    parser.add_argument('--host', default='a2kr815ji4hl5t.iot.us-west-2.amazonaws.com')
    parser.add_argument('--port', type=int, default=8883)
    parser.add_argument('--topic', default='temp-humidity/Omega-F4E1')
    parser.add_argument('--cafile', default='~/certs/rootCA.pem')
    parser.add_argument('--cert', default='~/certs/certificate.pem')
    parser.add_argument('--key', default='~/certs/private.key')
    parser.add_argument('--config', default='twilio.cfg', help='Twilio config file')
    parser.add_argument('--statsHour', type=int, default=21, help='When to send daily stats')
    args = parser.parse_args()

    args.cafile = os.path.expanduser(args.cafile)    
    args.cert = os.path.expanduser(args.cert)    
    args.key = os.path.expanduser(args.key)

    i2c = onionI2C.OnionI2C()

    order = ['top', 'bottom', 'ambient']
    sensors = {'top': SensorSHT31(device=0, i2c=i2c, thresholds=[None, 70., None]),
               'bottom': SensorSHT31(device=1, i2c=i2c, thresholds=[None, 70., None]),
               'ambient': SensorSHT25(i2c=i2c, thresholds=[None, 80., None])
              }

    sender = TwilioSender(args.config)

    publisher = SensorPublisher(sensors, alertSender=sender, statsHour=self.statsHour)
    publisher.connect(args.host, args.port, args.cafile, args.cert, args.key)
    publisher.start(args.poll)
    publisher.disconnect()

