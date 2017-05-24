# Nexus 9000v Sample Vagrant Configs

Here are some sample Vagrant configurations (Vagrantfiles) for use with the Nexus 9000v image.  

For instructions on how to create a Vagrant box for the Nexus 9000v see [Developer Tooling for Open NX-OS on DevNet](https://developer.cisco.com/site/nx-os/docs/guides/developer-tooling/index.gsp)

**Note:**  Keep in mind that each 9000v you spin up will require CPU and Memory from your host machine.  

* [basic/Vagrantfile](basic/Vagrantfile): This is what you get when you just `vagrant init` 
* [two-switches/Vagrantfile](two-switches/Vagrantfile): This is a custom Vagrantfile that deploys 2 N9Kvs with eth1/0/1 connected to an internal private network