#!/bin/bash
# This script works for Ubuntu 14.04
# It:
#   * Installs Overpass API
#   * Installs Overpass Turbo
#   * Installs Nginx and its configuration to run the Overpass web API/turbo
#   * Creates a crontab to daily run API requests and upload response on a FTP


if [ "$EUID" -ne 0 ]; then
    echo "Please run this installer as root"
    exit
fi

if [ $# -ne 2 && $# -ne 5 ]; then
    echo "Usage : ./install.sh INSTALL_DIR OVERPASS_VERSION"\
        "[FTP_SERVER FTP_USER FTP_PASSWORD]"
    exit
fi
if [ $# -eq 2]; then
    INSTALL_CRON_FTP=false
else
    INSTALL_CRON_FTP=true
    FTP_SERVER=$3
    FTP_USER=$4
    FTP_PASSWORD=$5
fi

INSTALL_DIR=$(echo -n $1 | sed 's:/*$::')
OVERPASS_VERSION=$2
NGINX_DIR="/var/www"

##################################
# Prepare installation
##################################

# Install packages
sudo apt-get update
sudo apt-get install -y g++ make expat libexpat1-dev zlib1g-dev wget nginx\
                        git nodejs fcgiwrap

# Create directories
mkdir -p "$INSTALL_DIR/exec"
mkdir -p "$INSTALL_DIR/db"
mkdir -p "$INSTALL_DIR/diffs"

##################################
# Overpass API
##################################
OVERPASS_DIR="osm-3s_v$OVERPASS_VERSION"
OVERPASS_ARCHIVE="$OVERPASS_DIR.tar.gz"
pushd $INSTALL_DIR
    # Download and build Overpass API
    wget "http://dev.overpass-api.de/releases/$OVERPASS_ARCHIVE"
    tar -zxvf $OVERPASS_ARCHIVE
    pushd OVERPASS_DIR
        ./configure CXXFLAGS="-O3" --prefix="$INSTALL_DIR/exec"
        make
        make install
    popd
    rm -rf $OVERPASS_DIR

    # Download latest planet file and populate database. This can take days
    wget http://planet.openstreetmap.org/planet/planet-latest.osm.bz2
    "$INSTALL_DIR/exec/bin/init_osm3s.sh" "$INSTALL_DIR/planet-latest.osm.bz2"\
        "$INSTALL_DIR/db" "$INSTALL_DIR/exec"
    rm planet-latest.osm.bz2

    # Create crons and start them
    cp -r etc/init etc/init.new
    sed -i "s,INSTALL_DIR,$INSTALL_DIR,g" etc/init.new/*.conf
    cp etc/init.new/*.conf /etc/init
    rm -rf etc/init.new
    initctl reload-configuration
    initctl start overpass-dispatcher
    initctl start overpass-areas
    initctl start overpass-rules-loop
    initctl start overpass-fetch-diffs
    initctl start overpass-apply-diffs
popd

##################################
# Overpass Turbo
##################################
pushd "$NGINX_DIR"
    git clone https://github.com/tyrasd/overpass-turbo.git
    pushd overpass-turbo
        # Replace default server by our own
        sed -i 's,//overpass-api.de/api/,http://localhost/cgi-bin/,g' js/configs.js
        npm install uglify-js csso pegjs
        make
        make install
    popd
popd

##################################
# Nginx
##################################
chown -R www-data:www-data $INSTALL_DIR
chown -R www-data:www-data "$NGINX_DIR/overpass-turbo"
cp etc/nginx/sites-available/overpass /etc/nginx/sites-available/overpass
sed -i "s,INSTALL_DIR,$INSTALL_DIR,g" /etc/nginx/sites-available/overpass
ln -s /etc/nginx/sites-available/overpass /etc/nginx/sites-enabled/overpass
service nginx restart

##################################
# Cron - Process requests and FTP upload
##################################
if [ "$INSTALL_CRON_FTP" = true ] ; then
    cp -r cron "$INSTALL_DIR"
    crontab -l > mycron
    echo "*/5 * * * * $INSTALL_DIR/cron/main.py $FTP_SERVER $FTP_USER $FTP_PASSWORD" >> mycron
    crontab mycron
    rm mycron
fi
