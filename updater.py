#!/usr/bin/python3

import os
import platform
from time import strftime
import subprocess
import sys
import socket
import smtplib
from email.mime.text import MIMEText
import slacknotifier

try:
    slack_webhook_url = os.environ['SLACK_WEBHOOK_URL']
except KeyError:
    print("Error: Environment variable SLACK_WEBHOOK_URL must be provided explicitly")
    sys.exit(1)

try:
    os.environ['UPDATER_RECIPIETS']
except KeyError:
    print("Error: Environment variable UPDATER_RECIPIETS must be provided explicitly")
    sys.exit(1)
else:
    email_recipients = os.environ['UPDATER_RECIPIETS'].split(",")

try:
    smtp_server_ip = os.environ['UPDATER_SMTP_ADDERESS']
except KeyError:
    print("Error: Environment variable UPDATER_SMTP_ADDERESS must be provided explicitly")
    sys.exit(1)

try:
    smtp_server_port = os.environ['UPDATER_SMTP_PORT']
except KeyError:
    smtp_server_port="25"

hostname = socket.getfqdn()
message_body = list()

try:
    import requests
except:
    print("Python module \'requests\' has not been found. Trying to install it automatically")
    process = subprocess.Popen(['pip', 'install', 'requests'])
    retval = process.wait()

    if retval != 0:
        print("Python module \'request\' is absent and cannot be installed automatically\nExit")
        sys.exit(1)
    else:
        import requests


def centos_update():
    """Performs update CentOS-based system"""

    packages = list()
    packages_broken = list()
    packages_forbidden = list()

    print('Update check time: %s on host %s' % (strftime('%m/%d/%Y %H:%M:%S'), hostname))

    # Get a list of packages that are available for update
    result = subprocess.Popen("yum check-update", shell=True, stdout=subprocess.PIPE).stdout.read().split("\n")

    # Make a list of packages to be updated and make sure they do not contain either kernel patches or systemd updates
    for item in result:
        item_parts = item.split()
        if len(item_parts) == 3 and ('x86_64' in item_parts[0] or 'noarch' in item_parts[0]):
            # Check if package is a kernel patch or a systemd update
            if ('kernel' not in item_parts[0]) and ('systemd' not in item_parts[0]) and ('grub' not in item_parts[0]):
                # Get a list of valid packages
                packages.append(item_parts[0])
            else:
                # Get a list of forbidden packages
                packages_forbidden.append(item_parts[0])
    # Check if there are any valid packages to be installed
    if packages == []:
        print("Nothing to update. System is up to date")
    else:
        # Perform updating package by package
        for item in packages:
            process = subprocess.Popen(["yum", 
                                        "--quiet", 
                                        "--assumeyes", 
                                        "--exclude=kernel*",
                                        "--exclude=systemd*", 
                                        "upgrade", item])

            # Wait until the process is finished and get an exitcode
            retval = process.wait()
            if retval != 0:
                packages_broken.append(item)
        # Remove cache data afer update
        os.system("yum clean all --quiet")

    report(packages, packages_forbidden, packages_broken)
    print('Update finish time: %s on host %s' % (strftime('%m/%d/%Y %H:%M:%S'), hostname))

    # Send the information about packages that must be installed manually (kernel patches and systemd updates)
    if packages_forbidden != []:
        message_body = []
        message_body.append('Check time: %s' % strftime('%m/%d/%Y %H:%M:%S'))
        message_body.append('Server name: %s' % hostname)
        message_body.append('\nThe following %d updates must be installed manually:' % len(packages_forbidden))
        message_body.append('\n'.join(packages_forbidden))
        colour = '#3700ef'
        pkgqty = len(packages_forbidden)

        slack_payload = {
            'attachments': [
                {
                    'pretext': 'Host: %s - %d updates have not been installed' % (hostname, pkgqty),
                    'color': '%s' % colour,
                    'title': '%s' % hostname,
                    'text': '```%s```' % '\n'.join(message_body),
                    'mrkdwn_in': ['text'],
                }
            ]
        }

        result = slacknotifier.send(slack_payload, slack_webhook_url)

        # If Slack is not accessible, send notification via email
        if result[0] != 200:
            send_to_email(message_body)

    # Send the information about packages that have not been installed (due to error) to Slack
    if packages_broken != []:
        message_body = []
        message_body.append('Check Time: %s' % strftime('%m/%d/%Y %H:%M:%S'))
        message_body.append('Server name: %s' % hostname)
        message_body.append('\nThe following %d updates have not been installed due to errors:' % len(packages_broken))
        message_body.append('\n'.join(packages_broken))
        colour = '#ef0000'
        pkgqty = len(packages_broken)

        slack_payload = {
            'attachments': [
                {
                    'pretext': 'Host: %s - %d updates have not been installed' % (hostname, pkgqty),
                    'color': '%s' % colour,
                    'title': '%s' % hostname,
                    'text': '```%s```' % '\n'.join(message_body),
                    'mrkdwn_in': ['text'],
                }
            ]
        }

        result = slacknotifier.send(slack_payload, slack_webhook_url)

        # If Slack is not accessible, send notification via email
        if result[0] != 200:
            send_to_email(message_body)


def ubuntu_update():
    """Performs update Ubuntu-based system"""

    packages = list()
    packages_broken = list()
    packages_forbidden = list()

    print('Update check time: %s on host %s' % (strftime('%m/%d/%Y %H:%M:%S'), hostname))

    # Get Ubuntu distributive name
    distrib_name = subprocess.check_output(["lsb_release", "-c", "-s"], universal_newlines=True).strip()

    # Download package information from all configured sources
    os.system("apt-get update -y")

    # Get a list of all packages that are to be upgraded
    result = subprocess.Popen("apt-get --assume-no --show-upgraded --verbose-versions --quiet upgrade", 
                            shell=True,
                            stdout=subprocess.PIPE).stdout.read().split("\n")
    for item in result:
        item_parts = item.split()
        if len(item_parts) == 4 and ('ubuntu' in item_parts[1] or distrib_name in item_parts[3]):
            # Check if a package is a kernel patch or a systemd update
            if ('kernel' not in item_parts[0]) and ('systemd' not in item_parts[0]) and ('grub' not in item_parts[0]):
                # Get a list of valid packages
                packages.append(item_parts[0])
            else:
                # Get a list of forbidden packages
                packages_forbidden.append(item_parts[0])

    # Check if there are any valid packages to be installed
    if packages == []:
        print("Nothing to update. System is up to date")
        print('Update finish time: %s on host %s' % (strftime('%m/%d/%Y %H:%M:%S'), hostname))
    else:
        # Perform updating package by package
        for item in packages:
            process = subprocess.Popen(["apt-get", "--quiet", "--assume-yes", "--only-upgrade", "install", item])
            # Wait until the process is finished and get an exitcode
            retval = process.wait()
            if retval != 0:
                print("Package %s cannot be installed" % item)
                packages_broken.append(item)
        # Remove cache data
        os.system("apt autoremove -y")
        os.system("apt clean all --quiet")

        print('%d of %d packages have been successfully installed on host %s' % (len(packages) - len(packages_broken),
                                                                                 len(packages), hostname))
    report(packages, packages_forbidden, packages_broken)
    print('Update finish time: %s on host %s' % (strftime('%m/%d/%Y %H:%M:%S'), hostname))

    # Send the information about packages that must be installed manually (kernel modules and systemd)
    if packages_forbidden != []:
        message_body = []
        message_body.append('Check Time: %s' % strftime('%m/%d/%Y %H:%M:%S'))
        message_body.append('Server name: %s' % hostname)
        message_body.append('\nThe following %d updates must be installed manually:' % len(packages_forbidden))
        message_body.append('\n'.join(packages_forbidden))
        colour = '#3700ef'
        pkgqty = len(packages_forbidden)

        slack_payload = {
            'attachments': [
                {
                    'pretext': 'Host: %s - %d updates have not been installed' % (hostname, pkgqty),
                    'color': '%s' % colour,
                    'title': '%s' % hostname,
                    'text': '```%s```' % '\n'.join(message_body),
                    'mrkdwn_in': ['text'],
                }
            ]
        }

        result = slacknotifier.send(slack_payload, slack_webhook_url)

        # If Slack is not accessible, send notification via email
        if result[0] != 200:
            send_to_email(message_body)

    # Send the information about packages that have not been installed (due to error) to Slack
    if packages_broken != []:
        message_body = []
        message_body.append('Check Time: %s' % strftime('%m/%d/%Y %H:%M:%S'))
        message_body.append('Server name: %s' % hostname)
        message_body.append('\nThe following %d updates have not been installed due to errors:' % len(packages_broken))
        message_body.append('\n'.join(packages_broken))
        colour = '#ef0000'
        pkgqty = len(packages_broken)

        slack_payload = {
            'attachments': [
                {
                    'pretext': 'Host: %s - %d updates have not been installed' % (hostname, pkgqty),
                    'color': '%s' % colour,
                    'title': '%s' % hostname,
                    'text': '```%s```' % '\n'.join(message_body),
                    'mrkdwn_in': ['text'],
                }
            ]
        }

        result = slacknotifier.send(slack_payload, slack_webhook_url)

        # If Slack is not accessible, send notification via email
        if result[0] != 200:
            send_to_email(message_body)


def send_to_email(message_body):
    """Function specifies a backup channel for notifications.
       It sends notification to email if Slack is not accessible"""

    message = MIMEText('\n'.join(message_body))
    message['Subject'] = message_body[2]
    message['From'] = hostname
    message['To'] = str(email_recipients).strip('[]')

    try:
        smtp_client = smtplib.SMTP(smtp_server_ip, smtp_server_port)
        for item in email_recipients:
            try:
                smtp_client.sendmail(hostname, item, message.as_string())
            except smtplib.SMTPException as e:
                print('It\'s impossible to send message to %s due to error' % item)
                print(str(e))
                raise SystemExit(0)
        smtp_client.quit()
    except:
        print('SMTP server %s:%s is unreachable' % (smtp_server_ip, smtp_server_port))
        raise SystemExit(0)


def report(packages, packages_forbidden, packages_broken):
    '''Reports on certain amount of packages of each category'''

    print("Packages to be installed: %d\nPackages that must be installed manually: %d\n"
          "Packages that have not been installed due to error: %s" % (len(packages),
                                                                        len(packages_forbidden),
                                                                        len(packages_broken)))

def main():
    # Determine a type of Linux. Only CentOS and Ubuntu are supported.
    if platform.dist()[0] == 'centos':
        centos_update()
    elif platform.dist()[0] == 'Ubuntu' or platform.dist()[0] == 'ubuntu':
        ubuntu_update()
    else:
        print("Unknown Linux distribution\nOnly HREL\\CentOS and Debian\\Ubuntu are supported at the moment")
        sys.exit()

if __name__ == '__main__':
    main()
