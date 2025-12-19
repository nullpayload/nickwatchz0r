import ssl
import irc3
import os
import logging
import requests
import json
from typing import Dict, Any

# --- Configuration & Setup ---

# Set logging level for detailed output
logging.basicConfig(level=logging.INFO)

# Global constants for file access and user data
USER_FILE = "/app/data/users.json"
USER_DATA: Dict[str, Any] = {}

# --- Environment Variable Loading ---
IRC_SERVER = os.getenv("IRC_SERVER", "irc.efnet.org")
IRC_PORT = int(os.getenv("IRC_PORT", 6667))
TARGET_CHANNEL = os.getenv("IRC_CHANNEL", "#channel")

BOT_NICK = os.getenv("BOT_NICK", "nickwatchz0r")
BOT_USER_ID = os.getenv("BOT_USER_ID", "nickwatchz0r")
BOT_REAL_NAME = os.getenv("BOT_REAL_NAME", "nickwatchz0r ver 1.0")

ENABLE_REGISTRATION = os.getenv("ENABLE_REGISTRATION", "false").lower() in ('true', '1', 'yes')

PERSONAL_NICK = os.getenv("PERSONAL_NICK", "mynick")
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")

# --- TLS Context Handling ---

TLS_INSECURE = os.getenv("IRC_INSECURE_TLS", "false").lower() in ('true', '1', 'yes')

if TLS_INSECURE:
    logging.warning("!!! IRC_INSECURE_TLS is TRUE: Disabling certificate verification. !!!")

    def my_create_default_context(*args, **kwargs):
        """Replacement for ssl.create_default_context that is always unverified."""
        context = ssl._create_unverified_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context

    # Patch the official function for the irc3 library
    ssl.create_default_context = my_create_default_context
    ssl_context = ssl.create_default_context()

else:
    logging.info("IRC_INSECURE_TLS is FALSE: Using standard, verified TLS context.")
    ssl_context = ssl.create_default_context()

# --- Helper Functions (I/O) ---

def load_user_data(bot):
    """Loads user configuration from the JSON file."""
    global USER_DATA
    try:
        with open(USER_FILE, 'r') as f:
            USER_DATA = json.load(f)
        bot.log.info(f"Loaded {len(USER_DATA)} user configurations from {USER_FILE}")
    except FileNotFoundError:
        bot.log.warning(f"{USER_FILE} not found. Starting with empty user data.")
        USER_DATA = {}
    except json.JSONDecodeError:
        bot.log.error(f"Error decoding JSON from {USER_FILE}. Data is corrupt.")
        USER_DATA = {}

def save_user_data(bot):
    """Saves the current user configuration to the JSON file."""
    try:
        with open(USER_FILE, 'w') as f:
            json.dump(USER_DATA, f, indent=4)
        bot.log.info(f"Saved {len(USER_DATA)} user configurations.")
    except Exception as e:
        bot.log.error(f"Failed to save user data: {e}")

# --- Helper Function (Pushover) ---

def send_pushover_notification(bot, title: str, message: str, priority: int = 0, user_key_override: str = None):
    """Sends a notification using the Pushover API."""

    # Use user's key if provided, otherwise use the owner's global key
    user_key_to_use = user_key_override if user_key_override else PUSHOVER_USER_KEY

    if not user_key_to_use or not PUSHOVER_APP_TOKEN:
        bot.log.error("Pushover credentials (User Key or App Token) not set. Cannot send notification.")
        return

    url = "https://api.pushover.net/1/messages.json"
    payload = {
        "token": PUSHOVER_APP_TOKEN,
        "user": user_key_to_use,
        "message": message,
        "title": title,
        "priority": priority,
    }

    try:
        response = requests.post(url, data=payload, timeout=5)
        if response.status_code != 200:
            bot.log.error(f"Pushover rejected the request: {response.text}")
        response.raise_for_status()
        bot.log.info(f"Pushover notification sent successfully to user {user_key_to_use[:8]}...")
    except requests.exceptions.RequestException as e:
        bot.log.error(f"Failed to send Pushover notification: {e}")

# --- IRC3 Plugin ---

@irc3.plugin
class WatcherPlugin:

    def __init__(self, bot):
        self.bot = bot
        self.personal_nick = os.getenv("PERSONAL_NICK", "eXklusve")

        global USER_DATA

        if ENABLE_REGISTRATION:
            load_user_data(self.bot)
        else:
            # Single-User Mode: Clear user data and use owner's config
            USER_DATA = {}
            if PUSHOVER_USER_KEY and self.personal_nick:
                # Use the bot's nick as the registration key for the owner's config
                USER_DATA[self.bot.nick] = {
                    "pushover_user_key": PUSHOVER_USER_KEY,
                    "watch_nick": self.personal_nick,
                    "priority": 0
                }
                self.bot.log.warning("Single-User Mode: Monitoring owner's nick.")
            else:
                self.bot.log.error("Single-User Mode enabled but PUSHOVER_USER_KEY or PERSONAL_NICK is missing!")

        self.bot.log.info(f"Registration system enabled: {ENABLE_REGISTRATION}")
        self.bot.log.info("WatcherPlugin Loaded Successfully.")

    @irc3.event(irc3.rfc.PRIVMSG)
    def handle_pms_and_registration(self, mask, target, data, **kwargs):
        """Processes private messages, specifically for the !register command."""

        # Ignore channel messages
        if target.lower() != self.bot.nick.lower():
            return

        user_irc_nick = mask.nick
        data_parts = data.strip().split()
        command = data_parts[0].lower()

        if command == '!register':
            if not ENABLE_REGISTRATION:
                self.bot.privmsg(user_irc_nick,
                    f"The user registration system is disabled. Monitoring mentions for '{self.personal_nick}' only.")
                return

            if len(data_parts) >= 3:
                pushover_key = data_parts[1]
                nick_to_watch = data_parts[2]

                if len(pushover_key) < 30 or len(nick_to_watch) < 3:
                     self.bot.privmsg(user_irc_nick,
                        "Error: Invalid Pushover Key or Nick To Watch format.")
                     return

                # Save the new user configuration
                global USER_DATA
                USER_DATA[user_irc_nick] = {
                    "pushover_user_key": pushover_key,
                    "watch_nick": nick_to_watch,
                    "priority": 0
                }
                save_user_data(self.bot)

                self.bot.privmsg(user_irc_nick,
                    f"Registration successful! You will receive notifications for mentions of '{nick_to_watch}'.")
            else:
                self.bot.privmsg(user_irc_nick,
                    "Usage: !register <YourPushoverUserKey> <NickToWatch>")

    @irc3.event(irc3.rfc.PRIVMSG)
    def monitor_and_dispatch(self, mask, target, data, **kwargs):
        """Processes channel messages, responds to !hello, and handles personal mentions."""

        # Ignore private messages to the bot
        if target.lower() == self.bot.nick.lower():
            return

        # --- Command Response (!hello) ---
        if data.strip().lower() == '!hello':
            if ENABLE_REGISTRATION:
                status_message = (
                    f"Hello {mask.nick}! I am {self.bot.nick}, the notification monitor. "
                    "The multi-user registration system is OPEN. "
                    "PM me `!register <YourPushoverUserKey> <NickToWatch>` to get setup."
                )
            else:
                status_message = (
                    f"Hello {mask.nick}! I am {self.bot.nick}, the notification monitor. "
                    f"The system is running in Single-User Mode and is only watching for mentions of {self.personal_nick}."
                )
            self.bot.privmsg(target, status_message)

        # --- Personal Mention Detection and Notification Dispatch ---

        message_lower = data.strip().lower()
        sender_nick_lower = mask.nick.lower()
        nicks_to_notify = []

        # Check all registered users for their watch nick
        for user_config in USER_DATA.values():
            watch_nick_lower = user_config.get('watch_nick', '').lower()

            # If the message contains the watch nick AND the sender is not the person being watched
            if watch_nick_lower and watch_nick_lower in message_lower and watch_nick_lower != sender_nick_lower:
                 nicks_to_notify.append(watch_nick_lower)

        if nicks_to_notify:
            triggered_nick_list = list(set(nicks_to_notify))

            log_message = (
                f"*** MENTION DETECTED *** Triggers: {', '.join(triggered_nick_list)}, "
                f"Sender: {mask.nick}, Channel: {target}"
            )
            self.bot.log.info(log_message)

            self.handle_personal_mention(mask, target, data, triggered_nick_list)


    def handle_personal_mention(self, mask, target, data, triggered_nick_list):
        """Notifies all registered users who are watching the mentioned nick."""

        # Iterate through all registered users
        for user_config in USER_DATA.values():

            user_watch_nick_lower = user_config.get('watch_nick', '').lower()

            # Check if this user's watched nick was in the list of triggered nicks
            if user_watch_nick_lower in triggered_nick_list:

                # Prepare Notification Content
                title = f"IRC Mention in {target}!"
                message = f"<{mask.nick}> {data.strip()}"

                self.bot.log.info(f"ACTION: Sending Pushover notification for mention of {user_watch_nick_lower}.")

                # Send the notification, using the user's specific key
                send_pushover_notification(
                    self.bot,
                    title,
                    message,
                    user_key_override=user_config['pushover_user_key']
                )

# --- IRC3 Bot Configuration and Run ---

config = {
    'nick': BOT_NICK,
    'host': IRC_SERVER,
    'port': IRC_PORT,
    'ssl': True,
    'ssl_context': ssl_context,
    'includes': [
        'irc3.plugins.core',
        'irc3.plugins.autojoins',
        '__main__',
    ],
    'autojoins': [TARGET_CHANNEL],
    'verbose': True,
    'reconnect': True,
    'realname': BOT_REAL_NAME,
    'username': BOT_USER_ID,
}

if __name__ == '__main__':
    bot = irc3.IrcBot.from_config(config)
    bot.run()