import os
import re
import json
import random
import string
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ============[LOGGING]============
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============[CONFIGURATION]============
# Railway pe environment variables se read karega
BOT_TOKEN = os.getenv('BOT_TOKEN', '#')  # Railway pe env variable set karein
STRIPE_SK = os.getenv('STRIPE_SK', 'sk_live_...')  # Railway pe env variable set karein
OWNER_IDS = list(map(int, os.getenv('OWNER_IDS', '1991559687,1386134927').split(',')))

# ============[HELPER FUNCTIONS]============
def get_str(string, start, end):
    try:
        return string.split(start)[1].split(end)[0]
    except:
        return ""

def multiexplode(delimiters, string):
    pattern = '|'.join(map(re.escape, delimiters))
    return re.split(pattern, string)

def random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def bin_lookup(bin_number):
    try:
        response = requests.get(
            f'https://lookup.binlist.net/{bin_number}',
            headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9'
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        logger.error(f"BIN Lookup Error: {e}")
        return None

def stripe_payment_method(cc, mes, ano, cvv, mail):
    try:
        response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            auth=(STRIPE_SK, ''),
            data={
                'type': 'card',
                'card[number]': cc,
                'card[exp_month]': mes,
                'card[exp_year]': ano,
                'card[cvc]': cvv,
                'billing_details[address][line1]': '36',
                'billing_details[address][line2]': 'Regent Street',
                'billing_details[address][city]': 'Jamestown',
                'billing_details[address][postal_code]': '14701',
                'billing_details[address][state]': 'New York',
                'billing_details[address][country]': 'US',
                'billing_details[email]': f'{mail}@gmail.com',
                'billing_details[name]': '@shadowdemon_xd Mittal'
            },
            timeout=15
        )
        return response.json()
    except Exception as e:
        logger.error(f"Stripe Payment Method Error: {e}")
        return None

def stripe_payment_intent(amount, payment_method_id, currency='usd'):
    try:
        response = requests.post(
            'https://api.stripe.com/v1/payment_intents',
            auth=(STRIPE_SK, ''),
            data={
                'amount': amount,
                'currency': currency,
                'payment_method_types[]': 'card',
                'description': '@shadowdemon_xd Donation',
                'payment_method': payment_method_id,
                'confirm': 'true',
                'off_session': 'true'
            },
            timeout=15
        )
        return response.json()
    except Exception as e:
        logger.error(f"Stripe Payment Intent Error: {e}")
        return None

# ============[COMMAND HANDLERS]============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    message = f"<b>Telegram ID:</b> <code>{user_id}</code>\n"
    message += f"<b>Group ID: </b><code>{chat_id}</code>\n"
    message += "<b>To Know Commands: /cmds</b>"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def cmds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = """<b><i>[Checker Gates]
    
STRIPE CUSTOM CHARGE -
/chk {Amount In $} - xxxxxxxxxxxxxxxx|xx|xx|xxx
/inr {Amount In ₹} - xxxxxxxxxxxxxxxx|xx|xx|xxx
BIN LOOKUP - /bin xxxxxx
SK CHECK - /sk sk_live_xxxxxxxxxx

[Tools]

TELEGRAM ID/GROUP ID - /id</i></b>"""
    await update.message.reply_text(message, parse_mode='HTML')

async def chk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Invalid format!\nUse: /chk amount cc|mm|yy|cvv")
        return
    
    try:
        args = context.args[0]
        parts = multiexplode(["/", ":", " ", "|"], args)
        
        amt = parts[0] if len(parts) > 0 else '1'
        cc = parts[1] if len(parts) > 1 else ''
        mes = parts[2] if len(parts) > 2 else ''
        ano = parts[3] if len(parts) > 3 else ''
        cvv = parts[4] if len(parts) > 4 else ''
        
        if not all([cc, mes, ano, cvv]):
            await update.message.reply_text("❌ Invalid card format!")
            return
        
        amount = int(amt) * 100
        mail = f'shadowdemo2w{random_string()}'
        lista = f'{cc}|{mes}|{ano}|{cvv}'
        
        # BIN Lookup
        bin_info = bin_lookup(cc[:6])
        
        # Stripe Payment Method
        pm_response = stripe_payment_method(cc, mes, ano, cvv, mail)
        if not pm_response:
            await update.message.reply_text("❌ Stripe API error!")
            return
        
        payment_method_id = pm_response.get('id')
        msg1 = pm_response.get('error', {}).get('message', '')
        
        if not payment_method_id:
            await update.message.reply_text(f"❌ Payment method creation failed!\nError: {msg1}")
            return
        
        # Stripe Payment Intent
        pi_response = stripe_payment_intent(amount, payment_method_id)
        if not pi_response:
            await update.message.reply_text("❌ Payment processing error!")
            return
        
        msg2 = pi_response.get('error', {}).get('message', '')
        
        # Determine response
        username = update.effective_user.username or "Unknown"
        response_text = f"<b>Card: <code>{lista}</code></b>\n"
        
        if "seller_message" in str(pi_response) and "Payment complete" in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Successfully Charged ${amt} ✅</b>\n"
        elif "insufficient_funds" in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Insufficient Funds</b>\n"
        elif "card_error_authentication_required" in str(pi_response) or "card_error_authentication_required" in str(pm_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» 3D Card</b>\n"
        elif '"cvc_check": "pass"' in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Payment Cannot Be Completed</b>\n"
        elif '"code": "incorrect_cvc"' in str(pi_response) or '"code": "incorrect_cvc"' in str(pm_response):
            response_text += f"<b>Status -» CCN Matched ✅</b>\n<b>Response -» CVV MISSMATCH</b>\n"
        elif "transaction_not_allowed" in str(pi_response) or "transaction_not_allowed" in str(pm_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Transaction Not Allowed</b>\n"
        elif "fraudulent" in str(pi_response) or "fraudulent" in str(pm_response):
            response_text += f"<b>Status -» Fraudulent</b>\n<b>Response -» Declined ❌</b>\n"
        elif "expired_card" in str(pi_response) or "expired_card" in str(pm_response):
            response_text += f"<b>Status -» Expired Card</b>\n<b>Response -» Declined ❌</b>\n"
        elif "generic_declined" in str(pi_response) or "generic_declined" in str(pm_response):
            response_text += f"<b>Status -» Generic Declined</b>\n<b>Response -» Declined ❌</b>\n"
        elif "do_not_honor" in str(pi_response) or "do_not_honor" in str(pm_response):
            response_text += f"<b>Status -» Do Not Honor</b>\n<b>Response -» Declined ❌</b>\n"
        else:
            response_text += f"<b><u><i>Unknown Error. {msg1} - {msg2}</i></u></b>\n"
        
        response_text += f"<b>Gateway -» Stripe Charge ${amt} </b>\n\n"
        response_text += f"<b>⋆ Checked By:</b> @{username}\n\n"
        response_text += f"<b>⋆ Bot By: @shadowdemon_xd</b>"
        
        await update.message.reply_text(response_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Chk Command Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def inr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Similar to chk_command but with INR currency
    if not context.args:
        await update.message.reply_text("❌ Invalid format!\nUse: /inr amount cc|mm|yy|cvv")
        return
    
    try:
        args = context.args[0]
        parts = multiexplode(["/", ":", " ", "|"], args)
        
        amt = parts[0] if len(parts) > 0 else '100'
        cc = parts[1] if len(parts) > 1 else ''
        mes = parts[2] if len(parts) > 2 else ''
        ano = parts[3] if len(parts) > 3 else ''
        cvv = parts[4] if len(parts) > 4 else ''
        
        if not all([cc, mes, ano, cvv]):
            await update.message.reply_text("❌ Invalid card format!")
            return
        
        amount = int(amt) * 100
        mail = f'shadowdemo2w{random_string()}'
        lista = f'{cc}|{mes}|{ano}|{cvv}'
        
        # BIN Lookup
        bin_info = bin_lookup(cc[:6])
        
        # Stripe Payment Method
        pm_response = stripe_payment_method(cc, mes, ano, cvv, mail)
        if not pm_response:
            await update.message.reply_text("❌ Stripe API error!")
            return
        
        payment_method_id = pm_response.get('id')
        msg1 = pm_response.get('error', {}).get('message', '')
        
        if not payment_method_id:
            await update.message.reply_text(f"❌ Payment method creation failed!\nError: {msg1}")
            return
        
        # Stripe Payment Intent with INR
        pi_response = stripe_payment_intent(amount, payment_method_id, 'inr')
        if not pi_response:
            await update.message.reply_text("❌ Payment processing error!")
            return
        
        msg2 = pi_response.get('error', {}).get('message', '')
        
        username = update.effective_user.username or "Unknown"
        response_text = f"<b>Card: <code>{lista}</code></b>\n"
        
        if "seller_message" in str(pi_response) and "Payment complete" in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Successfully Charged ₹{amt} ✅</b>\n"
        elif "insufficient_funds" in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Insufficient Funds</b>\n"
        elif "card_error_authentication_required" in str(pi_response) or "card_error_authentication_required" in str(pm_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» 3D Card</b>\n"
        elif '"cvc_check": "pass"' in str(pi_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Payment Cannot Be Completed</b>\n"
        elif '"code": "incorrect_cvc"' in str(pi_response) or '"code": "incorrect_cvc"' in str(pm_response):
            response_text += f"<b>Status -» CCN Matched ✅</b>\n<b>Response -» CVV MISSMATCH</b>\n"
        elif "transaction_not_allowed" in str(pi_response) or "transaction_not_allowed" in str(pm_response):
            response_text += f"<b>Status -» CVV Matched ✅</b>\n<b>Response -» Transaction Not Allowed</b>\n"
        elif "fraudulent" in str(pi_response) or "fraudulent" in str(pm_response):
            response_text += f"<b>Status -» Fraudulent</b>\n<b>Response -» Declined ❌</b>\n"
        elif "expired_card" in str(pi_response) or "expired_card" in str(pm_response):
            response_text += f"<b>Status -» Expired Card</b>\n<b>Response -» Declined ❌</b>\n"
        elif "generic_declined" in str(pi_response) or "generic_declined" in str(pm_response):
            response_text += f"<b>Status -» Generic Declined</b>\n<b>Response -» Declined ❌</b>\n"
        elif "do_not_honor" in str(pi_response) or "do_not_honor" in str(pm_response):
            response_text += f"<b>Status -» Do Not Honor</b>\n<b>Response -» Declined ❌</b>\n"
        else:
            response_text += f"<b><u><i>Unknown Error. {msg1} - {msg2}</i></u></b>\n"
        
        response_text += f"<b>Gateway -» Stripe Charge ₹{amt} </b>\n\n"
        response_text += f"<b>⋆ Checked By:</b> @{username}\n\n"
        response_text += f"<b>⋆ Bot By: @shadowdemon_xd</b>"
        
        await update.message.reply_text(response_text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"INR Command Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def bin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Invalid Bin\nFormat: /bin xxxxxx")
        return
    
    bin_number = context.args[0]
    bin_info = bin_lookup(bin_number)
    
    if not bin_info:
        await update.message.reply_text("❌ Invalid BIN or API error!")
        return
    
    bank = bin_info.get('bank', {}).get('name', 'N/A')
    name = bin_info.get('country', {}).get('name', 'N/A')
    emoji = bin_info.get('country', {}).get('emoji', '')
    brand = bin_info.get('brand', 'N/A')
    scheme = bin_info.get('scheme', 'N/A')
    card_type = bin_info.get('type', 'N/A')
    
    message = f"<b>✅ Valid Bin</b>\n"
    message += f"<b>⋆ Bank:</b> {bank}\n"
    message += f"<b>⋆ Country:</b> {name} {emoji}\n"
    message += f"<b>⋆ Brand:</b> {brand}\n"
    message += f"<b>⋆ Card:</b> {scheme}\n"
    message += f"<b>⋆ Type:</b> {card_type}\n"
    message += f"<b>⋆ Checked By:</b> @{update.effective_user.username or 'Unknown'}\n\n"
    message += f"<b>⋆ Bot By: @shadowdemon_xd</b>"
    
    await update.message.reply_text(message, parse_mode='HTML')

async def sk_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ No Sk Provided\nFormat: /sk sk_live_xxxxxxxxxxx")
        return
    
    sk = context.args[0]
    sk_hidden = sk[:12] + 'x' * (len(sk) - 12) if len(sk) > 12 else sk
    
    try:
        response = requests.post(
            'https://api.stripe.com/v1/tokens',
            auth=(sk, ''),
            data={
                'card[number]': '4912461004526326',
                'card[exp_month]': '04',
                'card[exp_year]': '2024',
                'card[cvc]': '011'
            },
            timeout=10
        )
        result = response.json()
        
        username = update.effective_user.username or "Unknown"
        message = ""
        
        if 'id' in result and result['id'].startswith('tok_'):
            message = f"<b>✅ LIVE KEY</b>\n<u>⋆ KEY:</u> <code>{sk_hidden}</code>\n<u>⋆ RESPONSE:</u> SK LIVE!!\n"
        elif 'error' in result:
            error_msg = result['error'].get('message', '')
            if 'Invalid API Key provided' in error_msg:
                message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk}</code>\n<u>⋆ RESPONSE:</u> INVALID KEY\n"
            elif 'You did not provide an API key' in error_msg:
                message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk}</code>\n<u>⋆ RESPONSE:</u> No Sk Key Provided\n"
            elif 'rate_limit' in error_msg:
                message = f"<b>⚠️ LIVE KEY</b>\n<u>⋆ KEY:</u> <code>{sk}</code>\n<u>⋆ RESPONSE:</u> Rate Limited Key\n"
            elif 'testmode_charges_only' in error_msg or 'test_mode_live_card' in error_msg:
                message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk}</code>\n<u>⋆ RESPONSE:</u> Testmode Charges Only\n"
            elif 'api_key_expired' in error_msg:
                message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk}</code>\n<u>⋆ RESPONSE:</u> Api Key Expired\n"
            else:
                message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk_hidden}</code>\n<u>⋆ RESPONSE:</u> Unknown Error.\n"
        else:
            message = f"<b>❌ DEAD KEY</b>\n<u>⋆ KEY:</u> <code>{sk_hidden}</code>\n<u>⋆ RESPONSE:</u> Unknown Error.\n"
        
        message += f"<u>⋆ Checked By:</u> @{username}\n\n"
        message += f"<b>⋆ Bot By: @shadowdemon_xd</b>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"SK Command Error: {e}")
        await update.message.reply_text(f"❌ Error checking SK: {str(e)}")

async def key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await sk_command(update, context)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ============[MAIN APPLICATION]============

def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("id", start_command))
    application.add_handler(CommandHandler("info", start_command))
    application.add_handler(CommandHandler("me", start_command))
    application.add_handler(CommandHandler("cmds", cmds_command))
    application.add_handler(CommandHandler("commands", cmds_command))
    application.add_handler(CommandHandler("cmd", cmds_command))
    application.add_handler(CommandHandler("chk", chk_command))
    application.add_handler(CommandHandler("inr", inr_command))
    application.add_handler(CommandHandler("bin", bin_command))
    application.add_handler(CommandHandler("sk", sk_command))
    application.add_handler(CommandHandler("key", key_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    port = int(os.environ.get('PORT', 8080))
    
    # Railway ke liye webhook setup (optional)
    # application.run_webhook(listen="0.0.0.0", port=port)
    
    # Ya polling mode (recommended for Railway)
    print("Bot is running on Railway...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
