#!/usr/bin/env python3
"""
Claude Telegram Bot
A simple Telegram bot powered by Anthropic's Claude API.
"""

import os
import logging
from dotenv import load_dotenv
from anthropic import Anthropic
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.request import HTTPXRequest

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Get API keys from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Validate environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set!")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable is not set!")

# Initialize Anthropic client with proxy support for China/regional blocks
anthropic_client = Anthropic(
    api_key=ANTHROPIC_API_KEY,
    base_url="https://api.anthropic.com",
)

# Bot configuration
CLAUDE_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048

# Proxy configuration for Telegram (if behind firewall)
PROXY_URL = os.getenv("TELEGRAM_PROXY_URL")  # e.g., "http://proxy:8080"


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    welcome_message = (
        "👋 **Hello! I'm Claude, your AI assistant.**\n\n"
        "I'm powered by Anthropic's Claude Sonnet 4 model. "
        "Feel free to send me any message and I'll do my best to help you!\n\n"
        "Just type your question or topic, and I'll respond with a thoughtful answer."
    )
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages and respond with Claude's output."""
    user_message = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(f"Message from user {user_id} (@{username}): {user_message[:50]}...")
    
    # Show typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Call Claude API
        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        # Extract the response text
        claude_response = response.content[0].text
        
        # Send the response
        await update.message.reply_text(claude_response)
        logger.info(f"Response sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing message from user {user_id}: {e}")
        error_message = (
            "❌ **Sorry, I encountered an error while processing your message.**\n\n"
            "Please try again later. If the problem persists, contact the bot administrator."
        )
        await update.message.reply_text(error_message, parse_mode="Markdown")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An unexpected error occurred. Please try again later."
        )


def main() -> None:
    """Start the bot."""
    logger.info("Starting Claude Telegram Bot...")
    
    # Build request with proxy if configured
    request_kwargs = {}
    if PROXY_URL:
        request_kwargs['proxy_url'] = PROXY_URL
        logger.info(f"Using proxy: {PROXY_URL}")
    
    # Create the Application with custom request handler
    request = HTTPXRequest(**request_kwargs) if request_kwargs else None
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Run the bot
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
