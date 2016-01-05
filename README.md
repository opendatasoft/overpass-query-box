# Overpass-pack
This project contains a main installation script, install.sh. It :
* Download and build Overpass API, and install few upstart script to run
daemons (required for OSM daily updates, web API, areas generation)
* Download Overpass Turbo, edit its configuration to use our own server
(localhost) and build it
* Installs and configure Nginx to use the freshly installed Overpass API
and Turbo
* (Optional) Installs a crontab which run a python script to daily process Overpass requests and upload responses
on a FTP server

## Usage
`Usage : ./install.sh INSTALL_DIR OVERPASS_VERSION [FTP_SERVER FTP_USER FTP_PASSWORD]`
Where :
* INSTALL_DIR is the absolute path where to install Overpass API
and its database
* OVERPASS_VERSION The Overpass Version to use like 0.7.52
(see http://dev.overpass-api.de/releases/)
* FTP_SERVER (optionnal): The FTP server on which to upload requests results processed by the crontab
* FTP_USER (optionnal): The FTP user
* FTP_PASSWORD (optionnal): The FTP password

## Daily requests and FTP upload
If you provide FTP credentials to the installation script, a python script will daily run to process Overpass requests
and upload responses on a remote server. This script :
* Fetch all files on the remote FTP server in the directory `/requests`
* Determines which requests to process : It runs every requests every 24 hours, or those which have been modified since
the last processing
* Pass its content to the Overpass interpreter and get the response.
* Upload each responses in a separate file on the FTP server.

## License
This software is licensed under the MIT license.

