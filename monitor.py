#!/usr/bin/env python

import paho.mqtt.client as mqtt
import ssl
import json
import time
from OmegaExpansion import onionI2C
from readTemp import SensorSHT31, SensorSHT25


class SensorPublisher(object):
    def __init__(self, sensors, order=None):
        self.sensors = sensors
        self.order = order
        if order is None:
            self.order = self.sensors.keys()
        else:
            self.order = order

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
                        cTemp, fTemp, humidity = sensor.read()
                        print('[{}] {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(), key.title(), cTemp, fTemp, humidity))
                        payload = self.buildPayload(cTemp, humidity)
                        fullTopic = '{}/{}'.format(args.topic, key)
                        result, mid = self.client.publish(fullTopic, payload, qos=1)
                    except IOError:
                        print('\n*** Failed to get data for {}, device {}!')
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
    args = parser.parse_args()

    args.cafile = os.path.expanduser(args.cafile)    
    args.cert = os.path.expanduser(args.cert)    
    args.key = os.path.expanduser(args.key)

    i2c = onionI2C.OnionI2C()

    order = ['top', 'bottom', 'ambient']
    sensors = {'top': SensorSHT31(device=0, i2c=i2c),
               'bottom': SensorSHT31(device=1, i2c=i2c),
               'ambient': SensorSHT25(i2c=i2c)
              }

    publisher = SensorPublisher(sensors)
    publisher.connect(args.host, args.port, args.cafile, args.cert, args.key)
    publisher.start(args.poll)
    publisher.disconnect()

