#! /bin/bash

yum install -y gcc zlib-devel openssl-devel
cd /usr/src
wget https://www.python.org/ftp/python/2.7.13/Python-2.7.13.tgz
tar xzf Python-2.7.13.tgz
cd Python-2.7.13
./configure
make altinstall

wget https://bootstrap.pypa.io/get-pip.py
python2.7 get-pip.py

cp -R /usr/lib/python2.7/site-packages/cli /usr/local/lib/python2.7/site-packages
cp -R /usr/lib/python2.7/site-packages/errors /usr/local/lib/python2.7/site-packages
cp -R /usr/lib/python2.7/site-packages/pnp /usr/local/lib/python2.7/site-packages
