# Wave-2: story-validators-race
<img src="assets/story-wave2-banner-05.png" alt="Grafa banner" style="width: 100%; height: 100%; object-fit: cover;" />

# Task4: Useful utility for validators
For Task 4, I have developed two useful utilities for Story blockchain validators:

1. Validator Monitor: A real-time monitoring tool with Telegram alerts
2. RPC Scanner: A comprehensive RPC endpoint scanner and vulnerability checker

Below are detailed instructions for each tool.

## 1. Validator Monitor

### Description

This tool is a useful utility for Story blockchain validators, helping to monitor block signing status and send alerts via Telegram when a validator misses multiple consecutive blocks.

### Key Features

1. Monitor block signing status of multiple validators simultaneously.
2. Display the number of consecutive missed blocks for each validator.
3. Send alerts via Telegram when a validator misses multiple consecutive blocks (default is 10 blocks).
4. Display real-time results with color coding for easy reading.

### How to Use

#### System Requirements

- Bash shell
- curl
- jq

#### Installation
