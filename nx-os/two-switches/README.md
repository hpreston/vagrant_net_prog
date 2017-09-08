# two-switches

This example Vagrant Environment provisions 2 Nexus 9000 switches.

## Requirements

Assumes you already have Vagrant + VirtualBox installed and working.  

### Vagrant Box

You will need a Nexus 9000 Vagrant Box.  You can quickly create your own using the instructions provided in the [box_building](../../box_building) folder of this repo.  

## vagrant up

Due to a shell incompatibility and error with the Nexus 9000v box and Vagrant, you'll need to `vagrant up` 3 times to fully complete the setup.  

```bash
# 1st Time - bring up the first nexus switch
vagrant up

# 2nd Time -  bring up second
vagrant up

# 3rd Time - complete
vagrant up
```

Once complete you should have 2 switches configured and ready.  

```bash
$ vagrant status
Current machine states:

nxos1                     running (virtualbox)
nxos2                     running (virtualbox)

This environment represents multiple VMs. The VMs are all listed
above with their current state. For more information about a specific
VM, run `vagrant status NAME`.

$ vagrant ssh nxos1

n9kv1#

$ vagrant ssh nxos2

n9kv1#
```

## Caveats and Known Issues

Some things to keep in mind when using this setup.

* Each Nexus 9000 consumes 4G of RAM so make sure your host workstation has enough power
* The data plane for communication between Ethernet interfaces is not fully supported on VirtualBox.  So do NOT be surprised if traffic doesn't work between connected interfaces
