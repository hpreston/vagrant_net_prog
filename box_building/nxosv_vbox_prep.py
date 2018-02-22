#!/usr/bin/env python
'''
Author: Rich Wellum (richwellum@gmail.com)
    Adapted and enhanced (fwiw) for use with NX-OS
    by Hank Preston (hapresto@cisco.com)

This is a tool to take an NX-OS Base Virtual Box image from CCO and create a
new box that has been bootstrapped for use with Vagrant.

- Initial configuration complete
- Mgmt Configured for DHCP
- vagrant account created with password vagrant and pub SSH Key

Tested with nxosv-final.7.0.3.I7.1.box
            nxosv-final.7.0.3.I6.1.box

  * Note: nxosv-final.7.0.3.I7.3.box (and later) boxes posted to CCO do not need
    this script to complete the setup for Vagrant.

Pre-installed requirements:
python-pexpect
vagrant
virtualbox

Within OSX, these tools can be installed by homebrew (but not limited to):

/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
brew cask install virtualbox
brew cask install vagrant
brew cask install python
pip install pexpect

Full Description:

Takes an NX-OS Source Box downloaded locally and completes the setup and base configuration and outputs
an updated VirtualBox Vagrant box.

Adds an embedded Vagrantfile, that will be included in
box/include/Vagrantfile. This Vagrantfile configures:

  . Guest forwarding ports for 22, 80, 443 and 830
  . SSH username and password and SSH (insecure) pub key
  . Serial console port for configuration (disconnected by default)

This embedded Vagrantfile is compatible with additional non-embedded
Vagrantfiles for more advanced multi-node topologies.

  . Backs up existing box files.
  . Creates and registers a new VirtualBox VM.
  . Adds appropriate memory, display and CPUs.
  . Sets one NIC for networking.
  . Sets up port forwarding for the guest SSH, NETCONF and RESTCONF.
  . Sets up storage - hdd and dvd(for ISO).
  . Starts the VM, then uses pexpect to configure NX-OS for
    basic networking, with user name vagrant/vagrant and SSH key
  . Enables NX-API
  . Closes the VM down, once configured.

The resultant box image, will come up fully networked and ready for use
with NX-API.  Other programmability features of NX-OS can be enabled
manually or through provisioning with Ansible.

NOTE: If more than one interface in the resulting Vagrant box is required
      then those additional interfaces need to be added in the actual
      Vagrantfile.
'''

from __future__ import print_function
import sys
import os
import time
import subprocess
import getpass
import argparse
import re
import logging
from logging import StreamHandler
import textwrap

try:
    import pexpect
except ImportError:
    sys.exit('The "pexpect" Python module is not installed. Please install it using pip or OS packaging.')

# The background is set with 40 plus the number of the color,
# and the foreground with 30.
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# Telnet ports used to access IOS XE via socat
CONSOLE_PORT = 65000
CONSOLE_SOCKET = "/tmp/test"

logger = logging.getLogger(__name__)


class ColorHandler(StreamHandler):
    """
    Add colors to logging output
    partial credits to
    http://opensourcehacker.com/2013/03/14/ultima-python-logger-somewhere-over-the-rainbow/
    """

    def __init__(self, colored):
        super(ColorHandler, self).__init__()
        self.colored = colored

    COLORS = {
        'WARNING': YELLOW,
        'INFO': WHITE,
        'DEBUG': BLUE,
        'CRITICAL': YELLOW,
        'ERROR': RED
    }

    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    level_map = {
        logging.DEBUG: (None, CYAN, False),
        logging.INFO: (None, WHITE, False),
        logging.WARNING: (None, YELLOW, True),
        logging.ERROR: (None, RED, True),
        logging.CRITICAL: (RED, WHITE, True),
    }

    def addColor(self, text, bg, fg, bold):
        ctext = ''
        if bg is not None:
            ctext = self.COLOR_SEQ % (40 + bg)
        if bold:
            ctext = ctext + self.BOLD_SEQ
        ctext = ctext + self.COLOR_SEQ % (30 + fg) + text + self.RESET_SEQ
        return ctext

    def colorize(self, record):
        if record.levelno in self.level_map:
            bg, fg, bold = self.level_map[record.levelno]
        else:
            bg, fg, bold = None, WHITE, False

        # exception?
        if record.exc_info:
            formatter = logging.Formatter(format)
            record.exc_text = self.addColor(
                formatter.formatException(record.exc_info), bg, fg, bold)

        record.msg = self.addColor(str(record.msg), bg, fg, bold)
        return record

    def format(self, record):
        if self.colored:
            message = logging.StreamHandler.format(self, self.colorize(record))
        else:
            message = logging.StreamHandler.format(self, record)
        return message

def run(cmd, hide_error=False, cont_on_error=False):
    """
    Run command to execute CLI and catch errors and display them whether
    in verbose mode or not.

    Allow the ability to hide errors and also to continue on errors.
    """

    s_cmd = ' '.join(cmd)
    logger.info("'%s'", s_cmd)

    output = subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    tup_output = output.communicate()

    if output.returncode != 0:
        logger.error('Failed (%d):', output.returncode)
    else:
        logger.debug('Succeeded (%d):', output.returncode)

    logger.debug('Output [%s]' % tup_output[0])

    if not hide_error and 0 != output.returncode:
        logger.error('Error [%s]' % tup_output[1])
        if not cont_on_error:
            sys.exit('Quitting due to run command error')
        else:
            logger.debug(
                'Continuing despite error cont_on_error=%d', cont_on_error)

    return tup_output[0]


def pause_to_debug():
    logger.critical("Pause before debug")
    logger.critical(
        "Use: 'socat unix-connect:/tmp/test stdin' to access the VM")
    raw_input("Press Enter to continue.")
    # To debug post box creation, add the following line to Vagrantfile
    # config.vm.provider "virtualbox" do |v|
    #   v.customize ["modifyvm", :id, "--uart1", "0x3F8", 4, "--uartmode1", 'tcpserver', 65000]
    # end


def cleanup_box():
    """
    Destroy Running Box.
    """
    logger.debug("Destroying Box")
    run(["vagrant", "destroy", "-f"], cont_on_error=True)


def configure_nx(verbose=False, wait=True):
    """
    Bring up NX-OS and do some initial config.
    Using socat to do the connection as telnet has an
    odd double return on vbox
    """
    logger.warn('Waiting for NX-OS to boot (may take 3 minutes or so)')
    localhost = 'localhost'

    PROMPT = r'[\w-]+(\([\w-]+\))?[#>]'
    # don't want to rely on specific hostname
    # PROMPT = r'(Router|csr1kv).*[#>]'
    CRLF = "\r\n"

    def send_line(line=CRLF):
        child.sendline(line)
        if line != CRLF:
            logger.info('NX-OS Config: %s' % line)
            child.expect(re.escape(line))

    def send_cmd(cmd, expect_prompt=True):
        if not isinstance(cmd, list):
            cmd = list((cmd,))
        for c in cmd:
            send_line(c)
        if expect_prompt:
            child.expect(PROMPT)


    try:
        #child = pexpect.spawn("socat TCP:%s:%s -,raw,echo=0,escape=0x1d" % (localhost, CONSOLE_PORT))
        child = pexpect.spawn("socat unix-connect:%s stdin" % (CONSOLE_SOCKET))

        if verbose:
            child.logfile = open("tmp.log", "w")

        # Long time for full configuration, waiting for ip address etc
        child.timeout = 600

        # wait for indication that boot has gone through
        if (wait):
            child.expect(r'%POAP-2-POAP_DHCP_DISCOVER_START:', child.timeout)
            logger.warn(
                'Logging into Vagrant Virtualbox and configuring NX-OS')

        # Abort POAP
        logger.warn("Aborting POAP")
        send_cmd("y", expect_prompt=False)
        time.sleep(1)

        # Disable Secure Password Enforcement
        logger.warn("Disable Secure Password")
        send_cmd("n", expect_prompt=False)
        time.sleep(1)

        # Set admin password
        logger.warn("Setting Admin Password")
        if (wait):
            child.expect(r'Enter the password for', child.timeout)
        send_cmd("admin", expect_prompt=False)
        time.sleep(2)
        if (wait):
            child.expect(r'Confirm the password', child.timeout)
        logger.warn("Confirming Admin Password")
        send_cmd("admin", expect_prompt=False)
        time.sleep(3)
        send_line()
        time.sleep(2)
        send_line()
        time.sleep(1)

        # wait for indication next step is ready
        if (wait):
            child.expect(r'Would you like to enter the basic configuration dialog', child.timeout)
        # Disable Basic System Configuration
        logger.warn("Disable Basic Sys Config")
        send_cmd("no", expect_prompt=False)
        # time.sleep(10)

        # wait for indication next step is ready
        if (wait):
            child.expect(r'User Access Verification', child.timeout)

        # Login as admin
        logger.warn("Logging in as admin")
        send_cmd("admin", expect_prompt=False)
        time.sleep(1)
        send_cmd("admin", expect_prompt=False)
        time.sleep(1)
        send_cmd("term width 300")

        # enable plus config mode
        logger.warn("Deploying Baseline configuration.")
        send_cmd("enable")
        send_cmd("conf t")

        # Perform basic Vagrant Configuration
        send_cmd("hostname n9kv1")
        send_cmd("interface mgmt 0")
        send_cmd("ip address dhcp ")
        send_cmd("no shut")
        send_cmd("exit")
        send_cmd("username vagrant password vagrant role network-admin")
        send_cmd("username vagrant sshkey ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key")

        # Enable Features
        send_cmd("feature nxapi")

        # Enable Guest Shell - needed because running with 4G Ram and not auto-installed
        # Used to set boot variable correctly
        send_cmd("guestshell enable")
        time.sleep(1)
        # wait for indication that guestshell is ready
        if (wait):
            child.expect(r"%VMAN-2-ACTIVATION_STATE: Successfully activated virtual service 'guestshell", child.timeout)
            logger.info('Guest Shell Enabled')
        time.sleep(5)

        # Set Boot Variable
        logger.warn("Setting boot image")
        send_cmd("guestshell run ls /bootflash/nxos*")
        boot_image = child.before.split("/")[4].strip()
        send_cmd("boot nxos bootflash:/{}".format(boot_image))


        # Disable Guest Shell to save resources in base box
        send_cmd("guestshell destroy", expect_prompt=False)
        time.sleep(1)
        send_cmd("y")
        time.sleep(1)
        # wait for indication that guestshell is destroyed
        if (wait):
            child.expect(r"%VMAN-2-INSTALL_STATE: Successfully destroyed virtual service 'guestshell", child.timeout)
            logger.info('Guest Shell Destroyed')


        # done and save
        logger.warn("Finishing Config and Saving to Startup-Config")
        send_cmd("end")
        send_cmd(["copy run start", CRLF])

        # just to be sure
        logger.warn('Waiting 10 seconds...')
        time.sleep(10)


    except pexpect.TIMEOUT:
        raise pexpect.TIMEOUT('Timeout (%s) exceeded in read().' % str(child.timeout))


def create_Vagrantfile(boxname, vmmemory="4096"):
    """
    Create a Basic Vagrantfile.
    """

    template = """# -*- mode: ruby -*-\n# vi: set ft=ruby :
                  Vagrant.configure("2") do |config|
                    config.vm.box = "{boxname}"
                    config.vm.synced_folder '.', '/vagrant', disabled: true
                    config.ssh.insert_key = false
                    config.vm.boot_timeout = 400
                    config.vm.guest = :other
                    # turn off the check if the plugin is installed
                    if Vagrant.has_plugin?("vagrant-vbguest")
                      config.vbguest.auto_update = false
                    end
                    config.vm.provider "virtualbox" do |vb|
                       vb.memory = "{vmmemory}"
                    end
                  end
                  """
    vagrantfile_contents = template.format(boxname=boxname, vmmemory=vmmemory)
    logger.info("Contents of Vagrantfile to be used")
    logger.info(vagrantfile_contents)
    logger.warn("Creating Vagrantfile")
    with open("Vagrantfile", "w") as f:
        f.write(vagrantfile_contents)


def box_add(boxname, boxpath):
    """
    Add Box to Vagrant Inventory.
    """
    logger.debug("Adding box %s to Vagrant." % (boxname))
    run(["vagrant", "box", "add", "-f", boxname, boxpath])

def box_remove(boxname):
    """
    Remove Box from Vagrant Inventory.
    """
    logger.debug("Removing box %s from Vagrant." % (boxname))
    run(["vagrant", "box", "remove", "-f", boxname])


def vagrant_up(cont_on_error=False):
    """
    Bring Up Vagrant
    """
    logger.warn("Starting Vagrant Environment.")
    logger.warn("  Note: vagrant may generate an error, that is expected")
    logger.warn("  Note: this step may take 3-5 minutes to complete.")
    run(["vagrant", "up"], cont_on_error=cont_on_error)



def main(argv):
    input_box = ''

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
            A tool to create an NX-OS Vagrant VirtualBox box from a base NX-OS Box.

            The Base Box will be installed, booted and configured.

            "vagrant ssh" provides access to the NX-oS management interface
            with internet access. It uses the insecure Vagrant SSH key.
        '''),

        epilog=textwrap.dedent('''\
            E.g.:
                box build with local box:
                    %(prog)s nxosv-final.7.0.3.I7.1.box
        '''))

    parser.add_argument('BOX_FILE',
                        help='local Base Box filename')
#     parser.add_argument('-o', '--create_ova', action='store_true',
#                         help='additionally use VBoxManage to export an OVA')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='will pause with the VM in a running state. Use: socat unix-connect:/tmp/test stdin to access')
    parser.add_argument('-n', '--nocolor', action='store_true',
                        help='don\'t use colors for logging')
    parser.add_argument('-v', '--verbose',
                        action='store_const', const=logging.INFO,
                        default=logging.WARN, help='turn on verbose messages')
    args = parser.parse_args()

    # setup logging
    root_logger = logging.getLogger()
    root_logger.setLevel(level=args.verbose)
    handler = ColorHandler(colored=(not args.nocolor))
    formatter = logging.Formatter("==> %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    logger = logging.getLogger("box-builder")

    # PRE-CHECK: is socat installed?
    logger.warn('Check whether "socat" is installed')
    try:
        run(['socat', '-V'])
    except OSError:
        sys.exit(
            'The "socat" utility is not installed. Please install it prior to using this script.')

    # Get source Box name and determine key details for script
    input_box = args.BOX_FILE
    box_name =  os.path.basename(input_box)
    vmname_base = os.path.basename(os.getcwd()) + "_default_"
    version = box_name[box_name.find(".")+1:len(box_name)-4]
    output_box = "nxos_{}".format(version)

    # if debug flag then set the logger to debug
    if args.debug:
        args.verbose = logging.DEBUG

    if not os.path.exists(input_box):
        sys.exit('%s does not exist' % input_box)

    # Set up paths
    base_dir = os.path.join(os.getcwd(), 'created_boxes')
    box_dir = os.path.join(base_dir, output_box)
    box_out = os.path.join(box_dir, output_box + '.box')
    pathname = os.path.abspath(os.path.dirname(sys.argv[0]))

#     vbox = os.path.join(box_dir, vmname + '.vbox')
#     vdi = os.path.join(box_dir, vmname + '.vdi')
#     ova_out = os.path.join(box_dir, vmname + '.ova')

    logger.debug('Input Box is %s', input_box)
    logger.debug('pathname: %s', pathname)
    logger.debug('VM Name Base:  %s', vmname_base)
    logger.debug('base_dir: %s', base_dir)
    logger.debug('box_dir:  %s', box_dir)
    logger.debug('Source Box Path: %s', box_name)
    logger.debug('Exported Box Path:  %s', box_out)
#     logger.warn('vbox:     %s', vbox)

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    if not os.path.exists(box_dir):
        os.makedirs(box_dir)

    # Delete existing Box
    if os.path.exists(box_out):
        os.remove(box_out)
        logger.debug('Found and deleted previous %s', box_out)

    # Delete existing OVA
#     if os.path.exists(ova_out) and args.create_ova is True:
#         os.remove(ova_out)
#         logger.debug('Found and deleted previous %s', ova_out)


    # Destroy any existing vagrant environment
    cleanup_box()
    logger.warn("  Note: An error may occur if the Vagrant environment isn't initialized, not problem")

    # Create Vagrantfile
    create_Vagrantfile(box_name)

    # Add Box to Vagrant Inventory
    box_add(box_name, input_box)

    # Bring up Environment
    vagrant_up(cont_on_error=True)

    # Determine VM Name from Virtual Box
    vms_list_running = run(['VBoxManage', 'list', 'runningvms']).split("\n")
    possible_vms = [vm for vm in vms_list_running if vmname_base in vm]
    if len(possible_vms) == 1:
        # Extract just the VM Name from the output
        vmname = possible_vms[0].split()[0][1:len(possible_vms[0].split()[0])-2]
        logger.warn("Found VirtualBox VM: {}".format(vmname))
    else:
        sys.exit("Could not determine the VM Name.")

    # Complete Startup
    # Configure NX-OS
    # do print steps for logging set to DEBUG and INFO
    # DEBUG also prints the I/O with the device on the console
    # default is WARN
    configure_nx(args.verbose < logging.WARN)

    # Good place to stop and take a look if --debug was entered
    if args.debug:
        pause_to_debug()


    # Export as new box
    logger.warn('Powering down and generating new Vagrant VirtualBox')
    logger.warn('Waiting for machine to shutdown')
    run(["vagrant", "halt", "-f"])

    # Add the embedded Vagrantfile
    vagrantfile_pathname = os.path.join(pathname, 'include', 'embedded_vagrantfile_nx')

    logger.warn("Exporting new box file.  (may take 3 minutes or so)")
    run(["vagrant", "package", "--vagrantfile", vagrantfile_pathname, "--output", box_out])
    logger.warn('New Vagrant Box Created: %s', box_out)

    # Destroy original Source Box
    logger.warn("Cleaning up build resources.")
    cleanup_box()
    box_remove(box_name)

    # Delete Vagrantfile used to build box
    os.remove("Vagrantfile")

    logger.warn('Completed!')
    logger.warn(" ")

    logger.warn('Add box to system:')
    logger.warn('  vagrant box add --name nxos/{version} {boxout} --force'.format(version=version, boxout=box_out))
    logger.warn(" ")
    logger.warn('Use your new box:')
    logger.warn("Make project directory: ")
    logger.warn("  mkdir my_project ")
    logger.warn("  cd my_project")
    logger.warn('Initialize Project Vagrant Environment:')
    logger.warn('  vagrant init nxos/{version}'.format(version=version))
    logger.warn('Bring up box:')
    logger.warn('  vagrant up')
    logger.warn('')
    logger.warn("Note: Due to a shell error, 'vagrant up' will error the "\
                "first time launching a box.  Run 'vagrant up' to complete")

    logger.warn('Note:')
    logger.warn(
        '  Both the NX-OS SSH and NX-API username and password is vagrant/vagrant')



if __name__ == '__main__':
    main(sys.argv[1:])
