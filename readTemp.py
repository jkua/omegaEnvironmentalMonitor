from OmegaExpansion import onionI2C
import time

class SensorSHT25:
    def __init__(self, device=0, i2c=None):
        # SHT25 address, 0x40(64)
        self.address = 0x40
        if device != 0:
            raise Exception('Device number must be 0!')
        
        if i2c is not None:
            self.i2c = i2c
        else:
            self.i2c = onionI2C.OnionI2C()

    def read(self):
        # Send temperature measurement command
        # 0xF3(243)   NO HOLD master
        data = [0xF3]
        self.i2c.write(self.address, data)
        time.sleep(0.5)

        # Read data back 2 bytes
        # Temp MSB, Temp LSB
        data = i2c.readBytes(self.address, 0x40, 2)

        # Convert the data
        temp = data[0] * 256 + data[1]
        cTemp= -46.85 + ((temp * 175.72) / 65536.0)
        fTemp = cTemp * 1.8 + 32

        # Send humidity measurement command
        # 0xF5(245)   NO HOLD master
        data = [0xF5]
        i2c.write(self.address, data)

        time.sleep(0.5)

        # Read data back, 2 bytes
        # Humidity MSB, Humidity LSB
        data = i2c.readBytes(self.address, 0x40, 2)

        # Convert the data
        humidity = data[0] * 256 + data[1]
        humidity = -6 + ((humidity * 125.0) / 65536.0)

        humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

        return cTemp, fTemp, humidity

class SensorSHT31:
    def __init__(self, device=0, i2c=None):
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

    def read(self):
        # Send measurement command, 0x2C(44)
        # 0x06(06)    High repeatability measurement
        data = [0x06]
        self.i2c.writeBytes(self.address, 0x2c, data)
        time.sleep(0.5)

        # SHT31 address, 0x44(68)
        # Read data back from 0x00(00), 6 bytes
        # Temp MSB, Temp LSB, Temp CRC, Humididty MSB, Humidity LSB, Humidity CRC
        data = i2c.readBytes(self.address, 0x00, 6)

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
    args = parse.parse_args()

    if args.sensor == 'sht25':
        sensor = SensorSHT25()
    elif args.sensor == 'sht31':
        sensor = SensorSHT31(device=args.device)

    cTemp, fTemp, humidity = sensor.read()
    print('[{}] {}, Device {} - {:5.2f} deg C, {:5.1f} deg F, {:4.1f} %RH'.format(time.ctime(), args.sensor.upper(), args.device, cTemp, fTemp, humidity))