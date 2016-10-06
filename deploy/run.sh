#! /bin/bash

cd pfl
devcron.py crontab &
service nginx start