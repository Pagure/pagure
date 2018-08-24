#!/usr/bin/env python

from __future__ import print_function
import json
import os
import sys

data = None
with open('emoji_strategy.json') as stream:
    data = json.load(stream)

if not data:
    print('Could not load the data from the JSON file')
    sys.exit(1)

# Retrieve the items we keep in the JSON
tokeep = {}
for key in data:
    if '-' in data[key]['unicode'] and data[key]['unicode'].startswith('1F'):
        continue
    tokeep[key] = data[key]

# Check if we have the keys of all images we kept

unicodes = [tokeep[key]['unicode'] for key in tokeep]
images = [item.replace('.png', '') for item in os.listdir('png')]

print(set(unicodes).symmetric_difference(set(images)))


with open('emoji_strategy2.json', 'w') as stream:
    json.dump(tokeep, stream)
