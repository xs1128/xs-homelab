#!/bin/bash

# Run WireGuard and output JSON in the shape needed for your widget
WG_OUTPUT=$(sudo -n /opt/homebrew/bin/wg show)

# Simplified parser: adapt to real wg output
INTERFACE=$(echo "$WG_OUTPUT" | grep '^interface:' | awk '{print $2}')
PEERS=$(echo "$WG_OUTPUT" | grep '^peer:' | wc -l)
IP=$(ifconfig "$INTERFACE" 2>/dev/null | grep 'inet ' | awk '{print $2}')
ACTUAL_IP=$(curl -s https://ifconfig.me)
GEO_JSON=$(curl -s "https://ipwho.is/$ACTUAL_IP")
CITY=$(echo "$GEO_JSON" | jq -r '.city')
COUNTRY=$(echo "$GEO_JSON" | jq -r '.country')


STATUS="false"
if [ -n "$INTERFACE" ]; then STATUS="true"; fi

cat <<EOF
[
  {
    "vpn_enabled": "$STATUS",
    "ip": "$IP",
    "geo": {
      "city": "$CITY",
      "country": "$COUNTRY"
    },
    "peers": $PEERS
  }
]
EOF

