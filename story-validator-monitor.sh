#!/bin/bash

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

# Telegram configuration
TELEGRAM_BOT_TOKEN="YOUR_BOT_TOKEN"
TELEGRAM_CHAT_ID="YOUR_CHAT_ID"

# Number of consecutive missed blocks before sending an alert
ALERT_THRESHOLD=10

send_telegram_alert() {
    local message="$1"
    local response=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id="$TELEGRAM_CHAT_ID" \
        -d text="$message" \
        -d parse_mode="HTML")
    
    echo -e "${YELLOW}[Telegram Alert] Sent: $message${RESET}"
    if [[ $(echo "$response" | jq -r '.ok') == "true" ]]; then
        echo -e "${GREEN}[Telegram Alert] Delivered successfully${RESET}"
    else
        echo -e "${RED}[Telegram Alert] Failed to deliver${RESET}"
    fi
}

# Read validator addresses and names from the file all_validators.txt
mapfile -t VALIDATOR_DATA < /root/story-validator-monitor/story_validators.txt

VALIDATOR_ADDRESSES=()
VALIDATOR_NAMES=()

declare -A MISSED_BLOCKS

for line in "${VALIDATOR_DATA[@]}"; do
    address=$(echo "$line" | awk '{print $1}')
    name=$(echo "$line" | awk '{print $2}')
    VALIDATOR_ADDRESSES+=("$address")
    VALIDATOR_NAMES+=("$name")
    MISSED_BLOCKS["$name"]=0
done

#Chagne your RPC endpoint
RPC_ENDPOINT="https://archive-rpc-story.josephtran.xyz"

while true; do
    current_height=$(curl -s "$RPC_ENDPOINT/status" | jq -r '.result.sync_info.latest_block_height')
    result_line="Block${GREEN} $current_height${RESET} |"

    for i in "${!VALIDATOR_ADDRESSES[@]}"; do
        VALIDATOR_ADDRESS="${VALIDATOR_ADDRESSES[$i]}"
        VALIDATOR_NAME="${VALIDATOR_NAMES[$i]}"

        signed=$(curl -s "$RPC_ENDPOINT/block?height=$current_height" | \
                 jq -r ".result.block.last_commit.signatures[] | select(.validator_address == \"$VALIDATOR_ADDRESS\") | .block_id_flag")

        if [[ "$signed" != "2" ]]; then
            MISSED_BLOCKS["$VALIDATOR_NAME"]=$((MISSED_BLOCKS["$VALIDATOR_NAME"] + 1))
            result_line+=" $VALIDATOR_NAME ${RED}❌ (${MISSED_BLOCKS["$VALIDATOR_NAME"]})${RESET} |"
            
            if [[ ${MISSED_BLOCKS["$VALIDATOR_NAME"]} -eq $ALERT_THRESHOLD ]]; then
                send_telegram_alert "⚠️  Alert: $VALIDATOR_NAME has missed $ALERT_THRESHOLD consecutive blocks. Last missed block at height $current_height"
                
            fi
        else
            MISSED_BLOCKS["$VALIDATOR_NAME"]=0
            result_line+=" $VALIDATOR_NAME ${GREEN}✅${RESET} |"
        fi
    done

    echo -e "$result_line"

    sleep 5
done
