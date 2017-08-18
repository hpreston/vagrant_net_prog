#! /usr/bin/env python
"""
Lab: vagrant up for Network Engineers
Author: Hank Preston <hapresto@cisco.com>

netconf_example3.py
Illustrate the following concepts:
- Constructing XML Config Payload for NETCONF
- Sending <edit-config> operation with ncclient
- Verify result
"""

__author__ = "Hank Preston"
__author_email__ = "hapresto@cisco.com"
__copyright__ = "Copyright (c) 2016 Cisco Systems, Inc."
__license__ = "MIT"

from ncclient import manager

device = {
             "address": "127.0.0.1",
             "port": 2223,
             "username": "vagrant",
             "password": "vagrant"
          }


# NETCONF Config Template to use
netconf_template = open("config-temp-native-interfaces.xml").read()

if __name__ == '__main__':
    # Build the XML Configuration to Send
    netconf_payload = netconf_template.format(int_type="GigabitEthernet",
                                              int_id="2",
                                              int_desc="Configured by NETCONF",
                                              ip_address="10.255.255.1",
                                              subnet_mask="255.255.255.0"
                                              )

    print("Configuration Payload:")
    print("----------------------")
    print(netconf_payload)
    print("")

    with manager.connect(host=device["address"], port=device["port"],
                         username=device["username"],
                         password=device["password"],
                         hostkey_verify=False) as m:

        # Send NETCONF <edit-config>
        netconf_reply = m.edit_config(netconf_payload, target="running")

        # Print the NETCONF Reply
        print(netconf_reply)
