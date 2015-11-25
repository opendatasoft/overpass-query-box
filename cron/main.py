#!/usr/bin/env python

import sys
import os
import urllib
import requests
from ftplib import FTP, error_perm, error_reply

API_URL = 'http://localhost/cgi-bin'
REQUEST_EXTENSION = '.overpass'
TIMEOUT_MINUTES = 15

if len(sys.argv) < 4:
    sys.stderr.write('Usage : ./main.py REQUESTS_DIRECTORY FTP_SERVER FTP_USER FTP_PASSWORD\n')
    sys.exit(1)

requests_directory = sys.argv[1]
results_directory = os.path.dirname(os.path.realpath(__file__)) + '/results'
ftp_server = sys.argv[2]
ftp_user = sys.argv[3]
ftp_password = sys.argv[4]
if not os.path.exists(requests_directory):
    os.makedirs(requests_directory)
if not os.path.exists(results_directory):
        os.makedirs(results_directory)

print 'Downloading requests responses...'

file_list = [each for each in os.listdir(requests_directory) if each.endswith(REQUEST_EXTENSION)]
for filename in file_list:
    with open('%s/%s' % (requests_directory, filename), 'r') as fd:
        query = fd.read()
    url = '%s/interpreter?data=%s' % (API_URL  ,urllib.quote(query, safe=''))
    req = requests.get(url, timeout=(TIMEOUT_MINUTES * 60))
    if req.status_code != 200:
        sys.stderr.write('URL %s returned status code %d\n' % (url, req.status_code))
    else:

        filename_result = filename[:-len(REQUEST_EXTENSION)] + '.xml'
        with open('%s/%s' % (results_directory, filename_result), 'w+') as fd:
            fd.write(req.text.encode('utf-8'))
        print("%s done." % filename_result)

print 'Download completed, starting upload on FTP...'

file_list = [each for each in os.listdir(results_directory) if each.endswith('.xml')]
ftp = FTP(ftp_server, user=ftp_user, passwd=ftp_password)
for filename in file_list:
    try:
        ftp.delete(filename)
    except (error_perm, error_reply) as e:
        sys.stderr.write('Cannot delete file %s: %s\n' % (filename, e.message))
    fd = open('%s/%s' % (results_directory, filename))
    ftp.storbinary('STOR %s' % filename, fd)
    fd.close()
    print('File %s uploaded.' % filename)
ftp.quit()

print("Upload completed.")
