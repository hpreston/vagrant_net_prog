# IOS XE (CSR 1000v) Sample Vagrant Configs

Here are some sample Vagrant configurations (Vagrantfiles) for use with the CSR 1000v image.  

For instructions on how to create a Vagrant box for the CSR 1000v see [box_building](../../box_building) folder of this repo.

**Note:**  Keep in mind that each CSR 1000v you spin up will require CPU and Memory from your host machine.  

* [basic](basic): This is what you get when you just `vagrant init`
* [netprog_ready](netprog_ready): This is my default starting point for IOS XE Programmability work.  It deploys a single IOS XE router with 3 interfaces (1 Management + 2 more), enables NETCONF/RESTCONF/YANG and Guest Shell features.  
