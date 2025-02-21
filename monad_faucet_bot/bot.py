import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Bot token (replace with a new one after revoking the old one)
API_TOKEN = '8058204307:AAElCDVKYKT0EBxmaRC5IS1y2v0EaT5XuX0'  # REVOKE THIS VIA BOTFATHER AND UPDATE!

# Channel chat ID and link
CHANNEL_CHAT_ID = '-1002376642664'
CHANNEL_LINK = 'https://t.me/TheAirdropHunt90'

# Your TON mainnet wallet address
TON_WALLET_ADDRESS = 'UQCv5TnQvkqdcICkoUu42CTCu5k_OnV-0P2sG_v2pHS6ELxs'

# TON API configuration (Mainnet)
TON_API_KEY = '981abb7d7eed00cf5a94c3cf878df29b4a07f73df0231abf0dac9e79f69d779c'  # Your key from @tonapibot
TON_API_URL = 'https://tonapi.io/v2'  # Mainnet endpoint

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Package options (Monad tokens for TON)
PACKAGES = {
    "pkg1": {"monad": 5, "ton": 2.5},
    "pkg2": {"monad": 10, "ton": 4.5},
    "pkg3": {"monad": 20, "ton": 8.0}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "Welcome to the Monad Faucet Bot! 🎉\n"
        f"To buy Monad testnet tokens, join our channel: {CHANNEL_LINK}\n"
        "After joining, use /claim to see package options."
    )
    await update.message.reply_text(welcome_message)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_CHAT_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            keyboard = [
                [InlineKeyboardButton("5 Monad - 2.5 TON", callback_data="pkg1")],
                [InlineKeyboardButton("10 Monad - 4.5 TON", callback_data="pkg2")],
                [InlineKeyboardButton("20 Monad - 8.0 TON", callback_data="pkg3")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Choose a package to buy Monad testnet tokens:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                f"You need to join our channel to buy tokens. Join here: {CHANNEL_LINK}"
            )
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        await update.message.reply_text("Oops! Something went wrong. Make sure I’m an admin in the channel.")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    package = PACKAGES[query.data]
    context.user_data['selected_package'] = query.data
    await query.edit_message_text(
        f"You’ve selected: {package['monad']} Monad tokens for {package['ton']} TON.\n"
        f"Please send {package['ton']} TON to this address: `{TON_WALLET_ADDRESS}`\n"
        "After payment, reply with the Transaction ID (TRX ID)."
    )

def verify_ton_payment(trx_id: str, expected_amount: float) -> bool:
    try:
        headers = {'Authorization': f'Bearer {TON_API_KEY}'}
        url = f"{TON_API_URL}/blockchain/accounts/{TON_WALLET_ADDRESS}/transactions"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        transactions = response.json().get('transactions', [])
        expected_nano_ton = int(expected_amount * 1_000_000_000)  # TON to nanoTON
        for tx in transactions:
            if tx['transaction_id']['hash'] == trx_id:
                amount = int(tx['in_msg']['value'])
                sender = tx['in_msg']['source']
                if amount >= expected_nano_ton and sender != TON_WALLET_ADDRESS:
                    logger.info(f"Payment verified: {amount} nanoTON for TRX ID {trx_id}")
                    return True
        logger.warning(f"Payment not found or insufficient for TRX ID {trx_id}")
        return False
    except Exception as e:
        logger.error(f"Error verifying TON payment: {e}")
        return False

async def receive_trx_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('selected_package') and not context.user_data.get('expecting_wallet'):
        trx_id = update.message.text.strip()
        package = PACKAGES[context.user_data['selected_package']]
        if verify_ton_payment(trx_id, package['ton']):
            context.user_data['trx_id'] = trx_id
            await update.message.reply_text(
                "Payment verified! Please provide your Monad wallet address to receive the testnet tokens."
            )
            context.user_data['expecting_wallet'] = True
        else:
            await update.message.reply_text(
                "Payment not verified. Please ensure the TRX ID is correct and matches the required amount."
            )
    elif context.user_data.get('expecting_wallet'):
        await receive_wallet(update, context)
    else:
        await update.message.reply_text("Please use /claim to select a package first.")

async def receive_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('expecting_wallet'):
        wallet_address = update.message.text.strip()
        package = PACKAGES[context.user_data['selected_package']]
        with open("purchases.txt", "a") as f:
            f.write(f"User: {update.message.from_user.id}, TRX ID: {context.user_data['trx_id']}, "
                    f"Wallet: {wallet_address}, Package: {package['monad']} Monad for {package['ton']} TON\n")
        await update.message.reply_text(
            f"Congrats! The {package['monad']} Monad testnet tokens will arrive shortly at {wallet_address}. "
            "Thanks for purchasing!"
        )
        context.user_data.clear()
    else:
        await update.message.reply_text("Please use /claim to start the purchase process.")

def main() -> None:
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("claim", claim))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_trx_id))
    application.run_polling()

if __name__ == '__main__':
    main()