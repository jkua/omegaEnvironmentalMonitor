#!/usr/env python

import ConfigParser
import subprocess
import json

class TwilioSender(object):
    def __init__(self, configFile):
        self.config = ConfigParser.ConfigParser()
        self.config.read(configFile)
        self.account = self.config.get('twilio', 'account')
        self.token = self.config.get('twilio', 'token')
        self.senderPhone = self.config.get('twilio', 'senderPhone')

    def sendSmsMessage(self, body, receiverPhone):
        command = ['curl', 'https://api.twilio.com/2010-04-01/Accounts/{}/Messages.json'.format(self.account),
                   '-X', 'POST',
                   '--data-urlencode', 'To={}'.format(receiverPhone),
                   '--data-urlencode', 'From={}'.format(self.senderPhone),
                   '--data-urlencode', 'Body={}'.format(body),
                   '-u', '{}:{}'.format(self.account, self.token)
                  ]

        p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = p.communicate()
        rc = p.returncode

        if rc == 0:
            json.loads(output)
            return output
        else:
            print('\nReturn code: {}'.format(rc))
            print('\nError: {}'.format(err))
            raise Exception('Failed to send message!')


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('body', help='Message to send')
    parser.add_argument('--to', required=True, help='Phone number to send the message to')
    parser.add_argument('--config', default='twilio.cfg', help='Twilio config file')
    args = parser.parse_args()

    sender = TwilioSender(args.config)
    sender.sendSmsMessage(args.body, args.to)
