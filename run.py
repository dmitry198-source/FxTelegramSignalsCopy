import os
import asyncio
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Environment variables
ACCOUNT_ID = os.environ.get('ACCOUNT_ID')
API_KEY = os.environ.get('API_KEY')
APP_URL = os.environ.get('APP_URL')
TELEGRAM_USER = os.environ.get('TELEGRAM_USER')
TELEGRAM_BOT_TOKEN = os.environ.get('TOKEN')

# Placeholder for the MetaApi connection
async def ConnectMetaTrader(trade):
    # Here you'll use ACCOUNT_ID and API_KEY to connect to MetaTrader
    print(f"Executing Trade: {trade}")
    await asyncio.sleep(1)  # Simulate delay for demonstration
    print("Trade executed")

# Function to parse the incoming trade signal
def ParseSignal(signal: str) -> dict:
    trade = {}
    # Example parsing logic
    lines = signal.split('\n')
    for line in lines:
        if 'SELL' in line or 'BUY' in line:
            trade['OrderType'] = 'Sell' if 'SELL' in line else 'Buy'
            words = line.split()
            trade['Symbol'] = words[1] if len(words) > 1 else None
        if 'At :' in line:
            trade['Entry'] = float(line.split(':')[1].strip())
        if 'SL :' in line:
            trade['StopLoss'] = float(line.split(':')[1].strip())
        if 'TP :' in line or 'Tp1' in line:
            trade['TakeProfit'] = [float(line.split(':')[1].strip())]
    
    return trade

# Telegram message handler
def handle_message(update, context):
    if TELEGRAM_USER and update.effective_user.username != TELEGRAM_USER:
        update.message.reply_text("Unauthorized user.")
        return

    message_text = update.effective_message.text
    trade = ParseSignal(message_text)
    if trade:
        asyncio.run(ConnectMetaTrader(trade))

# Main function to run the Telegram bot
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
