from OmegaExpansion import onionI2C
import time
import collections

class Sensor(object):
    def __init__(self, bufferTimeWindow=86400, thresholds=None, thresholdSamples=3):
        self.bufferTimeWindow = bufferTimeWindow
        self.buffer = collections.deque()
        self.thresholds = thresholds
        self.thresholdSamples = thresholdSamples

    def read(self):
        timestamp = time.time()
        data = self._readData()
        self._addToBuffer((timestamp, data))

        return timestamp, data

    def stats(self):
        if len(self.buffer) == 0:
            return None, None, None, 0

        total = [0] * len(self.buffer[0][1])
        minVals = [None] * len(self.buffer[0][1])
        maxVals = [None] * len(self.buffer[0][1])
        meanVals = [None] * len(self.buffer[0][1])
        for timestamp, data in self.buffer:
            for i, value in enumerate(data):
                total[i] = total[i] + value
                if (minVals[i] is None) or (value < minVals[i]):
                    minVals[i] = value
                if (maxVals[i] is None) or (value > maxVals[i]):
                    maxVals[i] = value

        for i, value in enumerate(total):
            meanVals[i] = value / float(len(self.buffer))
        numSamples = len(self.buffer)

        return meanVals, minVals, maxVals, numSamples

    def bufferSize(self):
        return len(self.buffer)

    def setThresholds(self, thresholds, thresholdSamples=3):
        self.thresholds = thresholds
        self.thresholdSamples = thresholdSamples

    def checkThresholds(self):
        if self.thresholds is None:
            return True
        if len(self.buffer) < self.thresholdSamples:
            return True

        # See if any thresholds are violated
        sampleData = []
        for i in range(self.thresholdSamples):
            sampleData.append(self.buffer[-i])
        for i, threshold in enumerate(self.thresholds):
            if threshold is not None:
                overThreshold = True
                for timestamp, data in sampleData:
                    if data[i] < threshold:
                        overThreshold = False
                if overThreshold:
                    return False

        return True

    def _readData(self):
        raise NotImplementedError()

    def _addToBuffer(self, timeDataTuple):
        self.buffer.append(timeDataTuple)
        lastTimestamp = timeDataTuple[0]

        # Remove old data
        while 1:
            if len(self.buffer) < 0:
                break
            timestamp = self.buffer[0][0]
            if (lastTimestamp - timestamp) <= self.bufferTimeWindow:
                break
            else:
                self.buffer.popleft()


class SensorSHT25(Sensor):
    def __init__(self, device=0, i2c=None, thresholds=None, thresholdSamples=3):
        super(SensorSHT25, self).__init__(thresholds=thresholds, thresholdSamples=thresholdSamples)
        # SHT25 address, 0x40(64)
        self.address = 0x40
        if device != 0:
            raise Exception('Device number must be 0!')
        
        if i2c is not None:
            self.i2c = i2c
        else:
            self.i2c = onionI2C.OnionI2C()

    def _readData(self):
        # Send temperature measurement command
        # 0xF3(243)   NO HOLD master
        data = [0xF3]
        self.i2c.write(self.address, data)
        time.sleep(0.5)

        # Read data back 2 bytes
        # Temp MSB, Temp LSB
        data = self.i2c.readBytes(self.address, 0x40, 2)

        # Convert the data
        temp = data[0] * 256 + data[1]
        cTemp= -46.85 + ((temp * 175.72) / 65536.0)
        fTemp = cTemp * 1.8 + 32

        # Send humidity measurement command
        # 0xF5(245)   NO HOLD master
        data = [0xF5]
        self.i2c.write(self.address, data)

        time.sleep(0.5)

        # Read data back, 2 bytes
        # Humidity MSB, Humidity LSB
        data = self.i2c.readBytes(self.address, 0x40, 2)

        # Convert the data
        humidity = data[0] * 256 + data[1]
        humidity = -6 + ((humidity * 125.0) / 65536.0)

        return cTemp, fTemp, humidity

class SensorSHT31(Sensor):
    def __init__(self, device=0, i2c=None, thresholds=None, thresholdSamples=3):
        super(SensorSHT31, self).__init__(thresholds=thresholds, thresholdSamples=thresholdSamples)
        # SHT31 address, 0x44(68) or 0x45(69)
        self.address = 0x44
        if device == 1:
            self.address = self.address + 1
        elif device not in [0, 1]:
            raise Exception('Device number must be 0 or 1!')
        
        if i2c is not None:
            self.i2c = i2c
        else:
            self.i2c = onionI2C.OnionI2C()

    def _readData(self):
        # Send measurement command, 0x2C(44)
        # 0x06(06)    High repeatability measurement
        data = [0x06]
        self.i2c.writeBytes(self.address, 0x2c, data)
        time.sleep(0.5)

        # SHT31 address, 0x44(68)
        # Read data back from 0x00(00), 6 bytes
        # Temp MSB, Temp LSB, Temp CRC, Humididty MSB, Humidity LSB, Humidity CRC
        data = self.i2c.readBytes(self.address, 0x00, 6)

        # Convert the data
        temp = data[0] * 256 + data[1]
        cTemp = -45 + (175 * temp / 65535.0)
        fTemp = -49 + (315 * temp / 65535.0)
        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

        return cTemp, fTemp, humidity

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('sensor', choices=['sht25', 'sht31'])
    parser.add_argument('--device', type=int, default=0)
    args = parser.parse_args()

    if args.sensor == 'sht25':
        sensor = SensorSHT25()
    elif args.sensor == 'sht31':
        sensor = SensorSHT31(device=args.device)

    timestamp, (cTemp, fTemp, humidity) = sensor.read()
    print('[{}] {}, Device {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(timestamp), args.sensor.upper(), args.device, cTemp, fTemp, humidity))
    