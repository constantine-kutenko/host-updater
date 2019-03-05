# host-updater

## Overview

The script performs updating packages on Linux-based hosts within different environments. It works with RedHat Linux, CentOS, Debian and Ubuntu distributives. In case there were any problems or issues with updating packages it sends notifications to a certain Slack channel. If notification to Slack cannot be sent it sends repeated notification via email to a certain group of email addresses. Notifications are also sent if there were any packages that update 'kernel' or 'systemd'. Such packets are not updated automatically and notification is sent to consider installation the packages mentioned manually.

## Dependencies

- Linux-based operation system
- Python 3.x
- Python libraries:
    - os
    - platform
    - subprocess
    - sys
    - socket
    - json
    - smtplib
    - email.mime.tex
    - requests
- External packages:
    - slacknotifier

## Environment variables

| Variable | Default value | Description |
| ---------| ------------- | ----------- |
| SLACK_WEBHOOK_URL | Null | Specifies a Slack channel URL |
| UPDATER_RECIPIETS | Null | Specifies a list of notification recipients in format |
| UPDATER_SMTP_ADDERESS | Null | Specifies an address for SMTP server |
| UPDATER_SMTP_PORT | 25 | Specifies a TCP port for smtp server |

### How to run

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/QWERTY/ASDFGHJK/q2w3e4r5t6y7u8i9o0"
export UPDATER_RECIPIETS="user1@example.com,user2@example.com"
export UPDATER_SMTP_ADDERESS="127.0.0.1"
export UPDATER_SMTP_PORT="25"

python3 updater.py
```
