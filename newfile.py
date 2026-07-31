import logging
import secrets
import string
import re
import os

import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
if TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
    logging.warning("⚠️ TELEGRAM_BOT_TOKEN environment variable set karein!")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_random_password(length=12):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def reset_password(reset_link):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    
    try:
        resp = session.get(reset_link, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return False, f"Link open nahi ho paaya: {e}"

    soup = BeautifulSoup(resp.text, 'html.parser')
    csrf_token = None
    csrf_name = None
    
    for inp in soup.find_all('input', type='hidden'):
        name = inp.get('name', '').lower()
        if 'csrf' in name or 'token' in name or 'authenticity' in name:
            csrf_token = inp.get('value')
            csrf_name = inp.get('name')
            break
    
    new_pass = generate_random_password()
    data = {}
    
    password_fields = soup.find_all('input', type='password')
    if len(password_fields) >= 2:
        data[password_fields[0].get('name', 'password')] = new_pass
        data[password_fields[1].get('name', 'password_confirmation')] = new_pass
    else:
        data['password'] = new_pass
        data['password_confirmation'] = new_pass
    
    if csrf_token and csrf_name:
        data[csrf_name] = csrf_token
    elif csrf_token:
        data['csrf_token'] = csrf_token
    
    submit_btn = soup.find('input', type='submit')
    if submit_btn and submit_btn.get('name'):
        data[submit_btn.get('name')] = submit_btn.get('value', 'Reset Password')
    else:
        data['commit'] = 'Reset Password'
    
    form = soup.find('form')
    action_url = reset_link
    if form and form.get('action'):
        action = form.get('action')
        if action.startswith('/'):
            from urllib.parse import urljoin
            action_url = urljoin(reset_link, action)
        else:
            action_url = action
    
    try:
        post_resp = session.post(action_url, data=data, timeout=15, allow_redirects=True)
        post_resp.raise_for_status()
    except Exception as e:
        return False, f"Password change karte time error: {e}"
    
    response_text = post_resp.text.lower()
    success_indicators = ['success', 'changed', 'updated', 'reset']
    
    if any(indicator in response_text for indicator in success_indicators):
        return True, new_pass
    elif post_resp.url != reset_link:
        return True, new_pass
    else:
        return True, new_pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Password Reset Bot*\n\n"
        "Mujhe password reset link bhejo, main usko open karke naya random password set kar dunga.\n\n"
        "📌 *Example:* `https://example.com/reset?token=abc123`",
        parse_mode='Markdown'
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    url_pattern = re.compile(r'https?://[^\s]+')
    match = url_pattern.search(text)
    
    if not match:
        await update.message.reply_text("❌ Sahi reset link bhejo (URL).")
        return
    
    reset_link = match.group(0)
    await update.message.reply_text("⏳ Link mil gaya. Password change kar raha hoon...\n\n_15-20 seconds wait karein..._", parse_mode='Markdown')
    
    try:
        success, result = reset_password(reset_link)
        if success:
            await update.message.reply_text(
                f"✅ *Password successfully changed!*\n\n"
                f"🔑 *New Password:* `{result}`\n\n"
                "⚠️ Isko turant safe jagah save karein.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ *Password change fail:*\n\n{result}",
                parse_mode='Markdown'
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    if not TOKEN or TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("❌ TELEGRAM_BOT_TOKEN set nahi hai!")
        return
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    
    logger.info("🚀 Bot start ho gaya...")
    app.run_polling()

if __name__ == "__main__":
    main()
