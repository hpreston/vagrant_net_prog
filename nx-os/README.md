# Nexus 9000v Sample Vagrant Configs

Here are some sample Vagrant configurations (Vagrantfiles) for use with the Nexus 9000v image.  

For instructions on how to create a Vagrant box for the Nexus 9000v see [box_building](../../box_building) folder of this repo.

**Note:**  Keep in mind that each 9000v you spin up will require CPU and Memory from your host machine.  

* [basic](basic): This is what you get when you just `vagrant init`
* [two-switches](two-switches): This is a custom Vagrantfile that deploys 2 N9Kvs with eth1/1 connected to an internal private network
* [multinode\_ansible\_provisioning](multinode_ansible_provisioning): This example Vagrant Environment provisions 2 Nexus 9000 switches, and leverages Ansible to provision/configure basic settings.
