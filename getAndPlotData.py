import boto3
from boto3.dynamodb.conditions import Key
import numpy as np
import matplotlib.pyplot as plt
import datetime
import time

def getData(table, key, startTimeMs):
    response = table.query(
        KeyConditionExpression=Key('id').eq(key) & Key('timestamp').gt(startTimeMs)
    )
    items = response['Items']

    print('{} items'.format(len(items)))

    receivedTime = []
    measurementTime = []
    measurementDt = []
    temperature = []
    humidity = []

    for item in items:
        receivedTime.append(int(item['timestamp'])/1e3)
        measurementTime.append(float(item['payload']['timestamp']))
        measurementDt.append(datetime.datetime.fromtimestamp(item['payload']['timestamp']))
        temperature.append(float(item['payload']['temperature']))
        humidity.append(float(item['payload']['humidity']))
        # print('[{}] Received: {:.3f}, {:.1f} deg C, {:.1f} %RH'.format(measurementDt[-1], receivedTime[-1], temperature[-1], humidity[-1]))

    receivedTime = np.array(receivedTime)
    measurementTime = np.array(measurementTime)
    measurementDt = np.array(measurementDt)
    temperature = np.array(temperature)
    humidity = np.array(humidity)

    _, uniqueIdx = np.unique(measurementTime, return_index=True)
    print('{} unique messages ({:.2f}%)'.format(len(uniqueIdx), len(uniqueIdx)/float(len(items))*100.))

    delayMs = (receivedTime-measurementTime) * 1000
    print('Delay - Mean: {:.1f} ms, Std: {:.1f} ms, Min: {:.1f} ms, Max: {:.1f} ms'.format(np.mean(delayMs), np.std(delayMs), np.min(delayMs), np.max(delayMs)))

    return receivedTime, measurementTime, measurementDt, temperature, humidity

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=1)
    args = parser.parse_args()

    startTime = time.time() - 24*3600*args.days
    startTimeMs = int(startTime * 1000)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('wine-cellar-monitor')

    fig, ax = plt.subplots(3, sharex=True)
    colors = {'top': 'r', 'bottom': 'b', 'ambient': 'g'}
    ax[0].set_title('Last {} hours'.format(args.days*24))

    for key in ['ambient', 'top', 'bottom']:
        fullKey = 'temp-humidity/Omega-F4E1/' + key
        receivedTime, measurementTime, measurementDt, temperature, humidity = getData(table, fullKey, startTimeMs)

        ax[0].plot(measurementDt, temperature * 9./5 + 32, colors[key], label=key.title())
        ax[0].set_ylim([50, 80])
        ax[0].grid(True)
        ax[0].set_ylabel('Temperature (F)')
        ax[0].legend(loc='lower right')

        ax[1].plot(measurementDt, humidity, colors[key])
        ax[1].set_ylim([0, 100])
        ax[1].grid(True)
        ax[1].set_ylabel('Humidity (%RH)')

        ax[2].plot(measurementDt, receivedTime - measurementTime, colors[key]+'x')
        ax[2].grid(True)
        ax[2].set_ylabel('Message Delay (s)')
        
    fig.autofmt_xdate()
    plt.show()
