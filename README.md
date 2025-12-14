# `NICKWATCHZ0R` 

### A Containerized IRC Mention Monitor with Pushover Notifications

`nickwatchz0r` is a lightweight Python-based IRC bot built on the `irc3` library. It joins a specified channel, constantly monitors chat for mentions of designated nicknames, and instantly pushes a notification via the **Pushover** service when a mention is detected.

The script supports two primary modes: a simple **Single-User Mode** (monitoring one nick for the bot owner) and a **Multi-User Registration Mode** (allowing multiple IRC users to register their Pushover key and preferred nick to watch).

##  Quick Start (Docker Compose)

The easiest way to run `nickwatchz0r` is using Docker Compose.

1.  **Create a `docker-compose.yml` file:**

    ```yaml
    services:
      nickwatchz0r:
        image: nullpayload/nickwatchz0r:latest  
        container_name: nickwatchz0r
        restart: unless-stopped
        environment:
          # --- IRC CONFIG ---
          IRC_SERVER: 'irc.libera.chat' # Required: The IRC server to connect to
          IRC_PORT: 6697               # Default is 6667 (insecure), use 6697 for TLS/SSL
          IRC_CHANNEL: '#mychannel'    # Required: The channel to join (e.g., #support)
          BOT_NICK: 'nickwatchz0r'     # The nickname the bot will use
          BOT_USER_ID: 'nickwatchz0r'           # Added: The IRC user ID (username)
          BOT_REAL_NAME: 'nickwatchz0r ver 1.0'  # Added: The IRC real name (GECOS)

          # --- PUSHOVER CREDENTIALS (REQUIRED) ---
          PUSHOVER_APP_TOKEN: 'YOUR_APP_TOKEN' # Required: Your Pushover Application Token
          
          # --- SINGLE-USER MODE CONFIG (For the owner) ---
          # PUSHOVER_USER_KEY and PERSONAL_NICK are only used if ENABLE_REGISTRATION is false
          PUSHOVER_USER_KEY: 'YOUR_OWNER_USER_KEY' # Required: Your personal Pushover User Key
          PERSONAL_NICK: 'YourIRCnick'             # Required: The nickname YOU want to be notified for

          # --- SECURITY & MODE CONFIG ---
          ENABLE_REGISTRATION: 'false' # Set to 'true' to allow other users to register
          IRC_INSECURE_TLS: 'false'    # Set to 'true' to disable certificate verification (USE WITH CAUTION)

        volumes:
          # Required for Multi-User Mode: saves registered users here
          - ./data:/app/data
    ```

2.  **Run the container:**

    ```bash
    docker-compose up -d
    ```

##  Configuration Variables

The bot is entirely configured via the following environment variables:

### Required Settings

| Variable | Default | Description |
| :--- | :--- | :--- |
| `IRC_SERVER` | `irc.efnet.org` | The hostname of the IRC network (e.g., `irc.libera.chat`). |
| `IRC_CHANNEL` | `#channel` | The channel the bot should join and monitor (e.g., `#mychannel`). |
| `PUSHOVER_APP_TOKEN` | *None* | **REQUIRED.** Your Pushover Application API Token. |

### Single-User Mode Settings

These are primarily used when `ENABLE_REGISTRATION` is set to `false`.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `PUSHOVER_USER_KEY` | *None* | **REQUIRED** in Single-User Mode. Your personal Pushover User Key. |
| `PERSONAL_NICK` | `mynick` | **REQUIRED** in Single-User Mode. The nickname the owner wants to be watched. |

### Bot Customization

| Variable | Default | Description |
| :--- | :--- | :--- |
| `IRC_PORT` | `6667` | The port for the IRC server. Use `6697` for SSL/TLS connections. |
| `BOT_NICK` | `nickwatchz0r` | The nickname the bot will use on the network. |
| `BOT_REAL_NAME` | `System Monitor Bot` | The realname the bot reports. |

### Security & Mode Control

| Variable | Default | Description |
| :--- | :--- | :--- |
| `ENABLE_REGISTRATION` | `false` | If `true`, the multi-user registration system is enabled. |
| `IRC_INSECURE_TLS` | `false` | **CAUTION:** Set to `true` to skip TLS certificate verification. Use only for networks with self-signed or broken certificates. |

## Bot Functionality & Commands

### 1\. Single-User Mode (`ENABLE_REGISTRATION: false`)

  * The bot only monitors mentions of the nick specified in `PERSONAL_NICK`.
  * Any mention of `PERSONAL_NICK` in the `IRC_CHANNEL` sends a Pushover notification to the key in `PUSHOVER_USER_KEY`.
  * The `!register` command is disabled.

### 2\. Multi-User Registration Mode (`ENABLE_REGISTRATION: true`)

This mode allows the bot to monitor different watch-nicks for different users and send notifications to their individual Pushover keys.

| Command | Usage | Description |
| :--- | :--- | :--- |
| `!register` | **PM the bot:** `!register <PushoverKey> <NickToWatch>` | Registers the user's Pushover key and sets the specific nick they want to monitor (e.g., `!register uJ0uP9r... myaltnick`). |
| `!hello` | **Type in channel:** `!hello` | The bot responds with its status and provides the registration instructions. |

### Data Persistence - THIS DATA IS NOT ENCRYPTED

When `ENABLE_REGISTRATION` is `true`, the user data (`Pushover Key` and `NickToWatch`) is saved to a file named `/app/users.json` within the container. **It is critical to use a Docker volume** (as shown in the compose example) to ensure this file persists across container restarts.

```yaml
volumes:
  - ./data:/app/data # Maps the bot's data directory to a local directory
```