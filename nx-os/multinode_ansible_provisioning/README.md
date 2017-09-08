# multinode\_ansible\_provisioning

This example Vagrant Environment provisions 2 Nexus 9000 switches, and leverages Ansible to provision/configure basic settings.  

## Requirements

Assumes you already have Vagrant + VirtualBox installed and working.  

### Vagrant Box

You will need a Nexus 9000 Vagrant Box.  You can quickly create your own using the instructions provided in the [box_building](../../box_building) folder of this repo.  

### Ansible

For the provisioner to work, you'll need Ansible installed.  The example playbook uses modules that are available in 2.3+.  

1. Setup Python Virtual Environment

    ```bash
    virtualenv venv --python=python2.7
    source venv/bin/activate
    ```

1. Install requirements

    ```bash
    pip install -r requirements.txt
    ```

## vagrant up

Due to a shell incompatibility and error with the Nexus 9000v box and Vagrant, you'll need to `vagrant up` 3 times to fully complete the setup.  

```bash
# 1st Time - bring up the first nexus switch
vagrant up

# 2nd Time - provision first swtich, bring up second
vagrant up

# 3rd Time - provision second switch
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

nxos1#
nxos1# show ip int bri

IP Interface Status for VRF "default"(1)
Interface            IP Address      Interface Status
Lo11                 172.21.1.1      protocol-up/link-up/admin-up
Lo12                 172.21.2.1      protocol-up/link-up/admin-up
Lo13                 172.21.3.1      protocol-up/link-up/admin-up
Lo14                 172.21.4.1      protocol-up/link-up/admin-up
Eth1/1               172.20.0.1      protocol-up/link-up/admin-up
nxos1# exit

$ vagrant ssh nxos2

nxos2#
nxos2# show ip int bri

IP Interface Status for VRF "default"(1)
Interface            IP Address      Interface Status
Lo11                 172.22.1.1      protocol-up/link-up/admin-up
Lo12                 172.22.2.1      protocol-up/link-up/admin-up
Lo13                 172.22.3.1      protocol-up/link-up/admin-up
Lo14                 172.22.4.1      protocol-up/link-up/admin-up
Eth1/1               172.20.0.2      protocol-up/link-up/admin-up
nxos2# exit
```

### Reprovisioning Switches with Ansible

Should you make changes to the Ansible Playbooks and want to re-run it against the switches you can do so with `vagrant provision`.

```bash
$ vagrant provision

# Abbreviated Sample Output
==> nxos1: Running provisioner: ansible...
    nxos1: Running ansible-playbook...

PLAY [Provision NX-OS Devices] *************************************************

TASK [Gathering Facts] *********************************************************
ok: [nxos1]

TASK [Configure Interfaces] ****************************************************
ok: [nxos1] => (item={u'prefix': 24, u'ip_address': u'172.21.1.1', u'name': u'Loopback11', u'desc': u'Sample Network Route Injection'})
ok: [nxos1] => (item={u'prefix': 24, u'ip_address': u'172.21.2.1', u'name': u'Loopback12', u'desc': u'Sample Network Route Injection'})
ok: [nxos1] => (item={u'prefix': 24, u'ip_address': u'172.21.3.1', u'name': u'Loopback13', u'desc': u'Sample Network Route Injection'})
ok: [nxos1] => (item={u'prefix': 24, u'ip_address': u'172.21.4.1', u'name': u'Loopback14', u'desc': u'Sample Network Route Injection'})
ok: [nxos1] => (item={u'prefix': 24, u'ip_address': u'172.20.0.1', u'name': u'Ethernet1/1', u'desc': u'Link to other switch'})

PLAY RECAP *********************************************************************
nxos1                      : ok=7    changed=1    unreachable=0    failed=0

.
.
.
```

## Caveats and Known Issues

Some things to keep in mind when using this setup.

* Each Nexus 9000 consumes 4G of RAM so make sure your host workstation has enough power
* The data plane for communication between Ethernet interfaces is not fully supported on VirtualBox.  So do NOT be surprised if traffic doesn't work between connected interfaces
