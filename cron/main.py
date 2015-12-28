#!/usr/bin/env python

import sys
import os
import urllib
import requests
import shutil
import json
import datetime
from ftplib import FTP, error_perm, error_reply

API_URL = 'http://localhost/cgi-bin'
TIMEOUT_MINUTES = 15
HOURS_BEFORE_PROCESS = 24

if len(sys.argv) < 4:
    sys.stderr.write('Usage : ./main.py FTP_SERVER FTP_USER FTP_PASSWORD\n')
    sys.exit(1)

results_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'results')
requests_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'requests')
cron_history_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cron_history')
cron_history = {}
ftp_server = sys.argv[1]
ftp_user = sys.argv[2]
ftp_password = sys.argv[3]

if os.path.exists(results_directory):
    shutil.rmtree(results_directory)
if os.path.exists(requests_directory):
    shutil.rmtree(requests_directory)
if os.path.exists(cron_history_path):
    with open(cron_history_path, 'r') as fd:
        cron_history = json.load(fd)
os.makedirs(requests_directory)
os.makedirs(results_directory)


def date_to_ftp_timestamp(dt):
    return dt.strftime('%Y%m%d%H%M%S')


def ftp_timestamp_to_date(timestamp):
    return datetime.datetime.strptime(timestamp, '%Y%m%d%H%M%S')

print 'Downloading requests...'
# Connect to the FTP server and change directory to /requests
ftp = FTP(ftp_server, user=ftp_user, passwd=ftp_password)
if 'requests' not in ftp.nlst():
    ftp.mkd('requests')
ftp.cwd('requests')

# Download all files from the /requests directory
file_list = ftp.nlst()
for filename in file_list:
    with open(os.path.join(requests_directory, filename), 'w+') as fd:
        ftp.retrbinary('RETR ' + filename, fd.write)


# We close FTP connection because requests processing can take a while
print 'Processing requests and downloading responses...'

# Determine which requests to process
files_to_process = []
for filename in file_list:
    do_process = False
    res = ftp.sendcmd('MDTM %s' % filename)
    last_modified = ftp_timestamp_to_date(res.split(' ')[1])
    if cron_history.get(filename):
        history_last_modified = cron_history[filename].get('last_modified')
        if history_last_modified:
            history_last_modified = ftp_timestamp_to_date(history_last_modified)
            if history_last_modified != last_modified:
                do_process = True
        if not do_process:
            history_last_processed = ftp_timestamp_to_date(cron_history[filename].get('last_processed'))
            if history_last_processed:
                diff = datetime.datetime.now() - history_last_processed
                datetime.timedelta(0, 32400)
                if diff.total_seconds() / 60 / 60 >= HOURS_BEFORE_PROCESS:
                    do_process = True
            else:
                do_process = True
    else:
        cron_history[filename] = {}
        do_process = True

    if do_process:
        files_to_process.append(filename)
        cron_history[filename]['last_modified'] = date_to_ftp_timestamp(last_modified)
        cron_history[filename]['last_processed'] = date_to_ftp_timestamp(datetime.datetime.now())

with open(cron_history_path, 'w+') as fd:
    json.dump(cron_history, fd)

# We close FTP because the request can take a while
ftp.close()

for filename in files_to_process:
    with open(os.path.join(requests_directory, filename), 'r') as fd:
        query = fd.read()
    print("Processing %s..." % filename)
    url = '%s/interpreter?data=%s' % (API_URL, urllib.quote(query, safe=''))
    req = requests.get(url, timeout=(TIMEOUT_MINUTES * 60))
    req.raise_for_status()
    with open(os.path.join(results_directory, filename), 'w+') as fd:
        fd.write(req.text.encode('utf-8'))
    print("%s done." % filename)

print 'Download completed, starting upload on FTP...'
file_list = os.listdir(results_directory)
if file_list:
    ftp = FTP(ftp_server, user=ftp_user, passwd=ftp_password)
    for filename in file_list:
        try:
            ftp.delete(filename)
        except (error_perm, error_reply) as e:
            sys.stderr.write('Cannot delete file %s: %s\n' % (filename, e.message))
        fd = open(os.path.join(results_directory, filename))
        ftp.storbinary('STOR %s' % filename, fd)
        fd.close()
        print('File %s uploaded.' % filename)
    ftp.close()
print("Upload completed.")

shutil.rmtree(requests_directory)
shutil.rmtree(results_directory)
