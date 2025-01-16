from telethon import TelegramClient, events, errors
import asyncio
import logging
import os
from dotenv import load_dotenv
import sys
import traceback

# Constants
RESPONSE_TIMEOUT = 60    # seconds
CHECK_FREQUENCY = 10     # seconds
RESTART_DELAY = 5        # seconds after crash
ERROR_SLEEP_TIME = 1     # seconds to sleep on error to prevent tight loops
SESSION_NAME = 'bot_monitor_session'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO

# Message templates
ALERT_MESSAGE = "⚠️ Warning: Bot {bot} has not responded for {timeout} seconds!"
LOG_MESSAGES = {
    'bot_response': "Received response from bot",
    'check_sent': "Sent check command to {target}",
    'check_success': "Bot responded within timeout",
    'check_timeout': "Bot did not respond within {timeout} seconds",
    'alert_sent': "Alert sent to user {user_id}",
    'alert_fail': "Failed to send alert to user {user_id}: {error}",
    'rate_limit': "Hit rate limit, waiting {seconds} seconds",
    'error_check': "Error in check_bot: {error}",
    'error_handler': "Error in handle_bot_response: {error}",
    'error_monitor': "Error in monitor loop: {error}",
    'error_critical': "Critical error: {error}",
    'error_unexpected': "Unexpected error: {error}",
    'missing_env': "Missing required environment variables!",
    'shutdown_signal': "Received shutdown signal",
    'restart_delay': "Restarting in {delay} seconds...",
    'user_termination': "Program terminated by user",
    'fatal_error': "Fatal error: {error}"
}

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=LOG_LEVEL
)
logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self, client: TelegramClient, target_bot: str, alert_user_ids: list[int]):
        self.client = client
        self.target_bot = target_bot
        self.alert_user_ids = alert_user_ids
        self.check_event = asyncio.Event()
        self.is_running = True
        
    async def send_alerts(self):
        alert_message = ALERT_MESSAGE.format(bot=self.target_bot, timeout=RESPONSE_TIMEOUT)
        for user_id in self.alert_user_ids:
            try:
                await self.client.send_message(user_id, alert_message)
                logger.info(LOG_MESSAGES['alert_sent'].format(user_id=user_id))
            except Exception as e:
                logger.error(LOG_MESSAGES['alert_fail'].format(user_id=user_id, error=str(e)))

    async def check_bot(self):
        try:
            self.check_event.clear()
            await self.client.send_message(self.target_bot, '/check')
            logger.info(LOG_MESSAGES['check_sent'].format(target=self.target_bot))
            
            try:
                await asyncio.wait_for(self.check_event.wait(), timeout=RESPONSE_TIMEOUT)
                logger.info(LOG_MESSAGES['check_success'])
            except asyncio.TimeoutError:
                logger.warning(LOG_MESSAGES['check_timeout'].format(timeout=RESPONSE_TIMEOUT))
                await self.send_alerts()
                
        except errors.FloodWaitError as e:
            logger.warning(LOG_MESSAGES['rate_limit'].format(seconds=e.seconds))
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(LOG_MESSAGES['error_check'].format(error=str(e)))
            
    async def monitor(self):
        @self.client.on(events.NewMessage(from_users=self.target_bot))
        async def handle_bot_response(event):
            try:
                self.check_event.set()
                logger.info(LOG_MESSAGES['bot_response'])
            except Exception as e:
                logger.error(LOG_MESSAGES['error_handler'].format(error=str(e)))

        while self.is_running:
            try:
                await self.check_bot()
                await asyncio.sleep(CHECK_FREQUENCY)
            except Exception as e:
                logger.error(LOG_MESSAGES['error_monitor'].format(error=str(e)))
                await asyncio.sleep(ERROR_SLEEP_TIME)

    async def stop(self):
        self.is_running = False
        self.check_event.set()

async def run_forever():
    while True:
        try:
            # Get credentials from environment variables
            API_ID = os.getenv('TELEGRAM_API_ID')
            API_HASH = os.getenv('TELEGRAM_API_HASH')
            PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER')
            TARGET_BOT = os.getenv('TARGET_BOT')
            ALERT_USER_IDS = [int(id.strip()) for id in os.getenv('ALERT_USER_IDS', '').split(',')]
            
            if not all([API_ID, API_HASH, PHONE_NUMBER, TARGET_BOT, ALERT_USER_IDS]):
                logger.error(LOG_MESSAGES['missing_env'])
                sys.exit(1)
            
            client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
            await client.start(phone=PHONE_NUMBER)
            
            monitor = BotMonitor(client, TARGET_BOT, ALERT_USER_IDS)
            
            try:
                await monitor.monitor()
            except KeyboardInterrupt:
                logger.info(LOG_MESSAGES['shutdown_signal'])
                await monitor.stop()
                break
            except Exception as e:
                logger.error(LOG_MESSAGES['error_unexpected'].format(error=str(e)))
                logger.error(traceback.format_exc())
            finally:
                await client.disconnect()
                
        except Exception as e:
            logger.error(LOG_MESSAGES['error_critical'].format(error=str(e)))
            logger.error(traceback.format_exc())
        
        logger.info(LOG_MESSAGES['restart_delay'].format(delay=RESTART_DELAY))
        await asyncio.sleep(RESTART_DELAY)

if __name__ == "__main__":
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        logger.info(LOG_MESSAGES['user_termination'])
    except Exception as e:
        logger.critical(LOG_MESSAGES['fatal_error'].format(error=str(e)))
        logger.critical(traceback.format_exc())