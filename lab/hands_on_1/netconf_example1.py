#! /usr/bin/env python
"""
Lab: vagrant up for Network Engineers
Author: Hank Preston <hapresto@cisco.com>

netconf_example1.py
Illustrate the following concepts:
- Send <get> to retrieve config and state data 
- Process and leverage XML within Python 
- Report back current state of interface 
"""

__author__ = "Hank Preston"
__author_email__ = "hapresto@cisco.com"
__copyright__ = "Copyright (c) 2016 Cisco Systems, Inc."
__license__ = "MIT"

from ncclient import manager
import xmltodict
from pprint import pprint

device = {
             "address": "127.0.0.1",
             "port": 2223,
             "username": "vagrant",
             "password": "vagrant"
          }

# NETCONF filter to use
netconf_filter = open("filter-ietf-interfaces.xml").read()

if __name__ == '__main__':
    with manager.connect(host=device["address"], port=device["port"],
                         username=device["username"],
                         password=device["password"],
                         hostkey_verify=False) as m:

        # Get Configuration and State Info for Interface
        netconf_reply = m.get(netconf_filter)

        # Process the XML and store in useful dictionaries
        intf_details = xmltodict.parse(netconf_reply.xml)["rpc-reply"]["data"]
        #pprint(netconf_reply.xml)
        intf_config = intf_details["interfaces"]["interface"]
        intf_info = intf_details["interfaces-state"]["interface"]

        print("")
        print("Interface Details:")
        print("  Name: {}".format(intf_config["name"]["#text"]))
        print("  Type: {}".format(intf_config["type"]["#text"]))
        print("  MAC Address: {}".format(intf_info["phys-address"]))
        print("  Packets Input: {}".format(intf_info["statistics"]["in-unicast-pkts"]))
        print("  Packets Output: {}".format(intf_info["statistics"]["out-unicast-pkts"]))
