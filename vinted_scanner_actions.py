import os
import json
import sys

# Read configuration from environment variables
telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
queries = json.loads(os.environ.get('VINTED_QUERIES', '[]'))

# Import and modify the original script's Config
import Config
Config.telegram_bot_token = telegram_bot_token
Config.telegram_chat_id = telegram_chat_id
Config.queries = queries

# Run the main scanner
from vinted_scanner import main
if __name__ == "__main__":
    main()
