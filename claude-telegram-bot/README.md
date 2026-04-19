# Claude Telegram Bot

A simple, standalone Telegram bot powered by Anthropic's Claude AI. This bot uses the Claude Sonnet 4 model to provide intelligent responses to user messages.

## Features

- 🤖 **Claude AI Integration** - Powered by Anthropic's Claude Sonnet 4 (claude-sonnet-4-20250514)
- 💬 **Interactive Chat** - Natural conversation with context-aware responses
- ⌨️ **Typing Indicator** - Shows "typing..." status while processing your message
- 🛡️ **Secure** - API keys stored in environment variables, never in code
- 📝 **Error Handling** - Graceful error messages and logging

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- An Anthropic API Key (from [Anthropic Console](https://console.anthropic.com/))

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd claude-telegram-bot
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Usage

### Running the Bot

```bash
python bot.py
```

You'll see output like:
```
2024-01-01 12:00:00,000 - __main__ - INFO - Starting Claude Telegram Bot...
2024-01-01 12:00:00,000 - __main__ - INFO - Bot is running! Press Ctrl+C to stop.
```

### Interacting with the Bot

1. **Start the bot** - Send `/start` to your bot on Telegram
2. **Chat** - Send any text message and Claude will respond

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Display welcome message and instructions |

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from @BotFather | Yes |
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |

### Bot Settings

You can modify these settings in `bot.py`:

```python
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Claude model to use
MAX_TOKENS = 2048                           # Maximum response length
```

## Project Structure

```
claude-telegram-bot/
├── bot.py              # Main bot application
├── requirements.txt    # Python dependencies
├── .env.example        # Example environment variables
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Getting API Keys

### Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token provided

### Anthropic API Key

1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key

## Troubleshooting

### Bot doesn't respond
- Check that your `TELEGRAM_BOT_TOKEN` is correct
- Ensure the bot is running without errors
- Verify the bot is not blocked by the user

### Claude API errors
- Verify your `ANTHROPIC_API_KEY` is valid
- Check your Anthropic API usage/quota
- Review the logs for specific error messages

### Installation issues
- Ensure Python 3.8+ is installed: `python --version`
- Try upgrading pip: `pip install --upgrade pip`
- Install dependencies in a virtual environment

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions:
- Check the logs for error messages
- Review the [python-telegram-bot documentation](https://docs.python-telegram-bot.org/)
- Check the [Anthropic API documentation](https://docs.anthropic.com/)
