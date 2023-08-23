#!/bin/bash

# place this file in /etc/profile.d/

BOTNAME=SSH-Bot
# webhook URL should be placed in /etc/ssh_notify_webhook.
# the file must be 644 (root)
WEBHOOK=$(</etc/ssh_notify_webhook)
DATE=$(date +"%d-%m-%Y-%H:%M:%S")

function jq() {
    # simple json handler using python, which is installed by default in debian
    python3 -c "import sys;import json;a=json.loads(sys.argv[1]);print(a[sys.argv[2]]);" "$1" $2
}

HOST=$(hostname)
IP=$(awk '{ ip = $1 } END { print ip }' <<< $SSH_CLIENT)

IPINFO=$(wget https://ipinfo.io/$IP -O /dev/stdout 2>/dev/null)

ISP=$(jq "$IPINFO" org | tr ' ' '_')
COUNTRY=$(jq "$IPINFO" country)
CITY=$(jq "$IPINFO" city)

getCurrentTimestamp() { date -u --iso-8601=seconds; };

wget -O- --post-data \
'{
    "username": "'$BOTNAME'",
    "embeds": [{
        "color": 12976176,
        "title": "New login on ***'$HOST'***",
    "fields": [
      {
        "name": "User",
        "value": "'$(whoami)'"
      },
        {
        "name": "Host",
        "value": "'$HOST'"
      },
       {
        "name": "Date",
        "value": "'$DATE'"
      },
      {
        "name": "Origin",
        "value": "'$IP' | :flag_'${COUNTRY,,}': '$COUNTRY', '$CITY' | '$ISP'"
      },
      {
        "name": "Terminal",
        "value": "'$TERM'"
      }

    ],
        "timestamp": "'$(getCurrentTimestamp)'"
    }]
}' --header "Content-Type: application/json" $WEBHOOK 2>/dev/null
