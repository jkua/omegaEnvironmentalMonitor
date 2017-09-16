import paho.mqtt.client as mqtt
import ssl
import json
import time
from OmegaExpansion import onionI2C
from readTemp import SensorSHT31, SensorSHT25

lastConnectStatus = None

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    global lastConnectStatus
    if rc != lastConnectStatus:
        print("\n*** Connected with result code "+str(rc) + '\n')
        lastConnectStatus = rc

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

#The callback for when this client publishes to the server.
def on_publish(client, userdata, mid):
    print("Message published")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def buildPayload(temp, humidity):
    data = {'timestamp': time.time(),
            'temperature': cTemp,
            'humidity': humidity
           }
    jsonString = json.dumps(data)
    return jsonString

if __name__=='__main__':
    import os.path
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--poll', type=float, default=15.)
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

    lastConnectStatus = None    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message

    client.tls_set(ca_certs=args.cafile, certfile=args.cert, keyfile=args.key, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
    client.connect(args.host, args.port, keepalive=60)

    client.loop_start()

    while 1:
        try:
            startTime = time.time()
            print('----')
            for key in order:
                sensor = sensors[key]
                cTemp, fTemp, humidity = sensor.read()
                print('[{}] {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(), key.title(), cTemp, fTemp, humidity))
                payload = buildPayload(cTemp, humidity)
                fullTopic = '{}/{}'.format(args.topic, key)
                result, mid = client.publish(fullTopic, payload, qos=1)
            measurementTime = time.time() - startTime
            time.sleep(max(args.poll-measurementTime, 0))
        except KeyboardInterrupt:
            pass

    client.loop_stop()
    client.disconnect()

