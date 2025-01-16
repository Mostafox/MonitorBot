# Telegram Bot Monitor

A Python script that monitors a Telegram bot's responsiveness by sending `/check` commands and alerting specified users if the bot fails to respond within the timeout period.

## Features

- Monitors bot response time
- Sends alerts to specified users when bot is unresponsive
- Auto-restarts on crashes
- Rate limit handling
- Comprehensive error logging

## Requirements

- Python 3.7+
- Telegram account
- Telegram API credentials

## Installation

1. Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```
2. Create a `.env` file with your credentials based on the `sample.env` file.

## Getting Telegram API Credentials

1. Visit [Telegram API](https://my.telegram.org/auth)
2. Log in with your phone number
3. Go to 'API development tools'
4. Create a new application
5. Copy the `api_id` and `api_hash` to your `.env` file

## Usage

Run the script:
```sh
python main.py
```

The script will:
1. Connect to Telegram using your credentials
2. Send `/check` command to the target bot every 10 seconds
3. Wait up to 60 seconds for a response
4. Send alerts to specified users if no response is received
5. Auto-restart if any errors occur

## Alert User IDs

To get a user's Telegram ID:
1. Send a message to `@userinfobot` on Telegram
2. It will reply with the user's ID
3. Add the ID to the `ALERT_USER_IDS` in your `.env` file (comma-separated for multiple users)