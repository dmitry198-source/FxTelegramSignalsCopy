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

    # converts message to list of strings for parsing
    signal = signal.splitlines()
    signal = [line.rstrip() for line in signal]

    trade = {}

    # determines the order type of the trade
    order_keywords = ['Buy Limit', 'Sell Limit', 'Buy Stop', 'Sell Stop', 'Buy', 'Sell']
    for keyword in order_keywords:
        if keyword.lower() in signal[0].lower():
            trade['OrderType'] = keyword
            break
    else:
        # Log the invalid order type
        logger.error('Invalid order type: %s', signal[0])
        return {}

    # extracts symbol from trade signal
    trade['Symbol'] = (signal[0].split())[-1].upper()

    # Log the parsed signal
    logger.info('Parsed signal: %s', trade)

    # checks if the symbol is valid, if not, log and return an empty dictionary
    if trade['Symbol'] not in SYMBOLS:
        logger.error('Invalid symbol: %s', trade['Symbol'])
        return {}

    # checks whether or not to convert entry to float because of market execution option ("NOW")
    if trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Sell':
        trade['Entry'] = 'NOW'  # Set Entry to 'NOW' directly
    else:
        trade['Entry'] = float(signal[1].split()[-1])

    trade['StopLoss'] = float(signal[2].split()[-1])
    trade['TP'] = [float(signal[3].split()[-1])]

    # checks if there's a fourth line and parses it for TP2
    if len(signal) > 4:
        trade['TP'].append(float(signal[4].split()[-1]))

    # adds risk factor to trade
    trade['RiskFactor'] = risk_factor

    return trade

    # determines the order type of the trade
    order_keywords = ['Buy Limit', 'Sell Limit', 'Buy Stop', 'Sell Stop', 'Buy', 'Sell']
    for keyword in order_keywords:
        if keyword.lower() in signal[0].lower():
            trade['OrderType'] = keyword
            break
    else:
        # returns an empty dictionary if an invalid order type was given
        return {}

    # extracts symbol from trade signal
    trade['Symbol'] = (signal[0].split())[-1].upper()

    # checks if the symbol is valid, if not, returns an empty dictionary
    if trade['Symbol'] not in SYMBOLS:
        return {}

    # checks whether or not to convert entry to float because of market execution option ("NOW")
    if trade['OrderType'] == 'Buy' or trade['OrderType'] == 'Sell':
        trade['Entry'] = float(signal[1].split()[-1]) if signal[1].strip() != 'NOW' else 'NOW'
    else:
        trade['Entry'] = float(signal[1].split()[-1])

    trade['StopLoss'] = float(signal[2].split()[-1])
    trade['TP'] = [float(signal[3].split()[-1])]

    # checks if there's a fourth line and parses it for TP2
    if len(signal) > 4:
        trade['TP'].append(float(signal[4].split()[-1]))

    # adds risk factor to trade
    trade['RiskFactor'] = risk_factor

    return trade

# Helper Functions
def GetTradeInformation(update: Update, trade: dict, balance: float) -> None:
    """Calculates information from given trade including stop loss and take profit in pips, position size, and potential loss/profit.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
    """

    # ...

    # calculates the stop loss in pips
    if(trade['Symbol'] == 'XAUUSD'):
        multiplier = 0.1
    elif(trade['Symbol'] == 'XAGUSD'):
        multiplier = 0.001
    elif(str(trade['Entry']).index('.') >= 2):
        multiplier = 0.01
    else:
        multiplier = 0.0001

    # calculates the stop loss in pips
    stopLossPips = abs(round((trade['StopLoss'] - trade['Entry']) / multiplier))

    # sets the default risk factor for 0.01 lot size
    default_risk_factor = 0.01

    # calculates the position size using the default risk factor for 0.01 lot size
    trade['PositionSize'] = 0.01

    # calculates the take profit(s) in pips
    takeProfitPips = []
    for takeProfit in trade['TP']:
        takeProfitPips.append(abs(round((takeProfit - trade['Entry']) / multiplier)))

    # creates table with trade information
    table = CreateTable(trade, balance, stopLossPips, takeProfitPips)

    # sends user trade information and calculated risk
    update.effective_message.reply_text(f'<pre>{table}</pre>', parse_mode=ParseMode.HTML)

    return

def CreateTable(trade: dict, balance: float, stopLossPips: int, takeProfitPips: int) -> PrettyTable:
    """Creates PrettyTable object to display trade information to user.

    Arguments:
        trade: dictionary that stores trade information
        balance: current balance of the MetaTrader account
        stopLossPips: the difference in pips from stop loss price to entry price

    Returns:
        a Pretty Table object that contains trade information
    """

    # creates prettytable object
    table = PrettyTable()
    
    table.title = "Trade Information"
    table.field_names = ["Key", "Value"]
    table.align["Key"] = "l"  
    table.align["Value"] = "l" 

    table.add_row([trade["OrderType"] , trade["Symbol"]])
    table.add_row(['Entry\n', trade['Entry']])

    table.add_row(['Stop Loss', '{} pips'.format(stopLossPips)])

    for count, takeProfit in enumerate(takeProfitPips):
        table.add_row([f'TP {count + 1}', f'{takeProfit} pips'])

    table.add_row(['\nRisk Factor', '\n{:,.0f} %'.format(trade['RiskFactor'] * 100)])
    table.add_row(['Position Size', trade['PositionSize']])
    
    table.add_row(['\nCurrent Balance', '\n$ {:,.2f}'.format(balance)])
    table.add_row(['Potential Loss', '$ {:,.2f}'.format(round((trade['PositionSize'] * 10) * stopLossPips, 2))])

    # total potential profit from trade
    totalProfit = 0

    for count, takeProfit in enumerate(takeProfitPips):
        profit = round((trade['PositionSize'] * 10 * (1 / len(takeProfitPips))) * takeProfit, 2)
        table.add_row([f'TP {count + 1} Profit', '$ {:,.2f}'.format(profit)])
        
        # sums potential profit from each take profit target
        totalProfit += profit

    table.add_row(['\nTotal Profit', '\n$ {:,.2f}'.format(totalProfit)])

    return table

async def ConnectMetaTrader(update: Update, trade: dict, enterTrade: bool):
    """Attempts connection to MetaAPI and MetaTrader to place trade.

    Arguments:
        update: update from Telegram
        trade: dictionary that stores trade information

    Returns:
        A coroutine that confirms that the connection to MetaAPI/MetaTrader and trade placement were successful
    """

    # creates connection to MetaAPI
    api = MetaApi(API_KEY)
    
    try:
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        initial_state = account.state
        deployed_states = ['DEPLOYING', 'DEPLOYED']

        if initial_state not in deployed_states:
            #  wait until account is deployed and connected to broker
            logger.info('Deploying account')
            await account.deploy()

        logger.info('Waiting for API server to connect to broker ...')
        await account.wait_connected()

        # connect to MetaApi API
        connection = account.get_rpc_connection()
        await connection.connect()

        # wait until terminal state synchronized to the local state
        logger.info('Waiting for SDK to synchronize to terminal state ...')
        await connection.wait_synchronized()

        # obtains account information from MetaTrader server
        account_information = await connection.get_account_information()

        update.effective_message.reply_text("Successfully connected to MetaTrader!\nCalculating trade risk ... 🤔")

        # checks if the order is a market execution to get the current price of symbol
        if(trade['Entry'] == 'NOW'):
            price = await connection.get_symbol_price(symbol=trade['Symbol'])

            # uses bid price if the order type is a buy
            if(trade['OrderType'] == 'Buy'):
                trade['Entry'] = float(price['bid'])

            # uses ask price if the order type is a sell
            if(trade['OrderType'] == 'Sell'):
                trade['Entry'] = float(price['ask'])

        # produces a table with trade information
        GetTradeInformation(update, trade, account_information['balance'])
            
        # checks if the user has indicated to enter trade
        if(enterTrade == True):

            # enters trade on to MetaTrader account
            update.effective_message.reply_text("Entering trade on MetaTrader Account ... 👨🏾‍💻")

            try:
                # executes buy market execution order
                if(trade['OrderType'] == 'Buy'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)

                # executes buy limit order
                elif(trade['OrderType'] == 'Buy Limit'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_limit_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes buy stop order
                elif(trade['OrderType'] == 'Buy Stop'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_stop_buy_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes sell market execution order
                elif(trade['OrderType'] == 'Sell'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_market_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['StopLoss'], takeProfit)

                # executes sell limit order
                elif(trade['OrderType'] == 'Sell Limit'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_limit_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)

                # executes sell stop order
                elif(trade['OrderType'] == 'Sell Stop'):
                    for takeProfit in trade['TP']:
                        result = await connection.create_stop_sell_order(trade['Symbol'], trade['PositionSize'] / len(trade['TP']), trade['Entry'], trade['StopLoss'], takeProfit)
                
                # sends success message to user
                update.effective_message.reply_text("Trade entered successfully! 💰")
                
                # prints success message to console
                logger.info('\nTrade entered successfully!')
                logger.info('Result Code: {}\n'.format(result['stringCode']))
            
            except Exception as error:
                logger.info(f"\nTrade failed with error: {error}\n")
                update.effective_message.reply_text(f"There was an issue 😕\n\nError Message:\n{error}")
    
    except Exception as error:
        logger.error(f'Error: {error}')
        update.effective_message.reply_text(f"There was an issue with the connection 😕\n\nError Message:\n{error}")
    
    return


# Handler Functions
# ... (imports and configurations)

# Other functions (ParseSignal, GetTradeInformation, Calculation_Command, etc.) remain unchanged

# Handler Functions
def PlaceTrade(update: Update, context: CallbackContext) -> None:
    """Parses and places trade based on incoming signal.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    if not update.effective_message.chat.username == TELEGRAM_USER:
        update.effective_message.reply_text("You are not authorized to use this bot! 🙅🏽‍♂️")
        return

    try:
        # Parse signal directly from the message
        signal = update.effective_message.text
        trade = ParseSignal(signal, DEFAULT_RISK_FACTOR)

        if not trade:
            raise Exception('Invalid Trade')

        # Connect to MetaTrader and place the trade
        asyncio.run(ConnectMetaTrader(update, trade, True))

    except Exception as error:
        logger.error(f'Error: {error}')
        errorMessage = f"There was an error processing this trade 😕\n\nError: {error}\n\nPlease make sure your signal format is correct."
        update.effective_message.reply_text(errorMessage)

# Command Handlers
def Trade_Command(update: Update, context: CallbackContext) -> None:
    """Does not have any specific functionality. Trades are processed directly in MessageHandler.

    Arguments:
        update: update from Telegram
        context: CallbackContext object that stores commonly used objects in handler callbacks
    """
    pass

def main() -> None:
    """Starts the bot."""
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Message handler for processing signals directly
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, PlaceTrade))

    # Other handlers (welcome, help, unknown_command, error, etc.)
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
