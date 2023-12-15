#!/usr/bin/env python3
import asyncio
import logging
import math
import os

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

from metaapi_cloud_sdk import MetaApi
from prettytable import PrettyTable
from telegram import ParseMode, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater, ConversationHandler, CallbackContext

# MetaAPI Credentials
API_KEY = os.environ.get("API_KEY")
ACCOUNT_ID = os.environ.get("ACCOUNT_ID")

# Telegram Credentials
TOKEN = os.environ.get("TOKEN")
TELEGRAM_USER = os.environ.get("TELEGRAM_USER")

# Heroku Credentials
APP_URL = os.environ.get("APP_URL")

# Port number for Telegram bot web hook
PORT = int(os.environ.get('PORT', '8443'))

# Enables logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# possibles states for conversation handler
CALCULATE, TRADE, DECISION = range(3)

# allowed FX symbols
SYMBOLS = ['AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURNZD', 'EURUSD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'NOW', 'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDJPY', 'XAGUSD', 'XAUUSD']

# Default risk factor and lot size
DEFAULT_RISK_FACTOR = float(os.environ.get("RISK_FACTOR", 0.01))


# Helper Functions
def ParseSignal(signal: str, risk_factor: float) -> dict:
    """Starts the process of parsing the signal and entering the trade on the MetaTrader account.

    Arguments:
        signal: trading signal
        risk_factor: the risk factor for position sizing

    Returns:
        a dictionary that contains trade signal information
    """

    # ... (your existing ParseSignal function)

    return trade

# Helper Functions
def GetTradeInformation(update: Update, trade: dict, balance: float) -> None:
    """Calculates information from given trade including stop loss and take profit in pips, position size, and potential loss.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
    """
    # ... (rest of the function)

def Calculation_Command(update: Update, context: CallbackContext) -> int:
    """Starts the process of calculating trade information based on a given signal.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if not (update.effective_message.chat.username == TELEGRAM_USER):
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return ConversationHandler.END

    # ... (your existing Calculation_Command function)

    return CALCULATE

def main() -> None:
    """Starts the bot."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('trade', Trade_Command)],
        states={
            CALCULATE: [
                CommandHandler('calculate', Calculation_Command)
            ],
            TRADE: [
                MessageHandler(Filters.text & ~Filters.command, PlaceTrade)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)

    # Other handlers
    dp.add_handler(CommandHandler("start", welcome))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))
    dp.add_error_handler(error)

    # Start the Bot
    if APP_URL:
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)
        updater.bot.setWebhook(APP_URL + TOKEN)
    else:
        updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
