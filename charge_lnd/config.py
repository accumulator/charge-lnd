#!/usr/bin/env python3
import sys
import re
import configparser


def debug(message):
    sys.stderr.write(message + "\n")

class Config:
    def __init__(self, config_file):
        self.config_file = config_file
        self.default = None
        self.policies = []

        self.config = configparser.ConfigParser(converters={'list': lambda x: [i.strip() for i in x.split(',')]})

        with open(config_file, "r") as f:
            self.config.read_file(f)

        sections = self.config.sections()
        for s in sections:
            if s == 'default':
                self.default = self.config[s]
            else:
                self.policies.append(s)

    def get_config_for(self, policy_name):
        return self.config[policy_name]
