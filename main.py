from telethon.sync import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import PeerChannel
import asyncio
import os
import requests
import re

# Debug environment variables
print("🔍 Debugging environment variables...")
print(f"API_ID: {'SET' if os.getenv('API_ID') else 'NOT SET'}")
print(f"API_HASH: {'SET' if os.getenv('API_HASH') else 'NOT SET'}")
print(f"STRING_SESSION: {'SET' if os.getenv('STRING_SESSION') else 'NOT SET'}")
print(f"BOT_TOKEN: {'SET' if os.getenv('BOT_TOKEN') else 'NOT SET'}")
print(f"CHANNEL_ID (destination): {'SET' if os.getenv('CHANNEL_ID') else 'NOT SET'}")
print(f"CHANNEL_USERNAME (source): {'SET' if os.getenv('CHANNEL_USERNAME') else 'NOT SET'}")

# Configuration from environment variables
api_id = int(os.getenv("API_ID", "27758818"))
api_hash = os.getenv("API_HASH", "f618d737aeaa7578fa0fa30c8c5572de")
string_session = os.getenv("STRING_SESSION", "").strip()
webhook_url = os.getenv("WEBHOOK_URL", "https://marisbriedis.app.n8n.cloud/webhook/fd2ddf25-4b6c-4d7b-9ee1-0d927fda2a41")

BOT_TOKEN = os.getenv("BOT_TOKEN", "7711621476:AAHPgGsxmviRFIRSHtZ8FlQdPdH7lbhrzuM")

# Source channel: where the bot listens for new messages (private channel)
source_channel_raw = os.getenv("CHANNEL_USERNAME", "-1002178767107")
source_channel_id = int(source_channel_raw.replace("-100", ""))  # e.g. 2178767107
source_channel_entity = PeerChannel(source_channel_id)

# Destination channel: where the bot sends reformatted messages
DEST_CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1002383089858"))

# Clean and validate session string
if string_session:
    string_session = string_session.strip()
    while string_session.startswith('='):
        string_session = string_session[1:]
    string_session = string_session.strip()

# Debug string session values
print(f"🔍 STRING_SESSION length: {len(string_session) if string_session else 0}")
print(f"🔍 STRING_SESSION starts with: {string_session[:10] if string_session else 'EMPTY'}...")
print(f"🔍 STRING_SESSION ends with: ...{string_session[-10:] if string_session and len(string_session) > 10 else 'EMPTY'}")

# Global variables
sequence = []
last_signal = None

def reformat_signal_message(original_message, is_result=False, win_type=None):
    if is_result:
        if win_type == "regular":
            return "🚨 AMO QUOTEX BOT 🚨\n✅ WIN"
        elif win_type == "win1":
            return "🚨 AMO QUOTEX BOT 🚨\n✅¹ WIN"
        elif win_type == "win2":
            return "🚨 AMO QUOTEX BOT 🚨\n✅² WIN"
        elif win_type == "loss":
            return "🚨 AMO QUOTEX BOT 🚨\n💔 LOSS"
        return None

    match_asset = re.search(r"Asset:\s*(.+)", original_message)
    match_timeframe = re.search(r"Timeframe:\s*(.+)", original_message)
    match_time = re.search(r"Signal Time:\s*(.+)", original_message)
    match_action = re.search(r"Action:\s*(PUT|CALL)", original_message, re.IGNORECASE)

    if match_asset and match_timeframe and match_time and match_action:
        asset = match_asset.group(1).strip()
        timeframe = match_timeframe.group(1).strip()
        signal_time = match_time.group(1).strip()
        action = match_action.group(1).strip().upper()
        arrow = "🔼" if action == "CALL" else "🔽"

        new_message = f"""👑 QUOTEX [{timeframe}] - Signal Alert

Asset: {asset}  
🔥 Timeframe: {timeframe}  
⌚ Signal Time: {signal_time}  
{arrow} Action: {action}  

🔗 OPEN BROKER HERE

🎯 Good luck, Traders!"""
        return new_message

    return None  # Not a valid signal

async def send_to_telegram_channel(message):
    if not message or message.strip() == "":
        print("⚠️ Empty message - not sending")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": DEST_CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram API response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Error sending to Telegram channel: {str(e)}")
        return None

def is_valid_session_string(session_str):
    if not session_str:
        return False
    if len(session_str) < 200:
        print(f"❌ Session string too short: {len(session_str)} characters")
        return False
    if not session_str.startswith('1'):
        print(f"❌ Session string doesn't start with '1': starts with '{session_str[:5]}'")
        return False
    print("✅ Session string format looks valid")
    return True

async def test_session_connection(client):
    try:
        print("🔗 Testing session connection...")
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Session is not authorized")
            return False
        me = await client.get_me()
        print(f"✅ Session is valid! Connected as: {me.first_name} (@{me.username})")
        return True
    except Exception as e:
        print(f"❌ Session connection test failed: {str(e)}")
        return False

async def main():
    print("📡 Starting Telegram Bot...")
    print(f"📡 Listening for messages on SOURCE_CHANNEL_ID: {source_channel_entity}...")

    client = None

    if string_session and is_valid_session_string(string_session):
        print("🔐 Attempting to use string session...")
        try:
            client = TelegramClient(StringSession(string_session), api_id, api_hash)
            if await test_session_connection(client):
                print("✅ String session is working!")
            else:
                print("❌ String session failed authorization test")
                await client.disconnect()
                client = None
        except Exception as e:
            print(f"❌ Error creating client with string session: {str(e)}")
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            client = None
    else:
        print("❌ No valid session string provided")

    if client is None:
        print("📁 No valid session available...")
        print("⚠️ Cannot create new session in Railway environment (no interactive input).")
        return

    @client.on(events.NewMessage(chats=source_channel_entity))
    async def handler(event):
        global sequence, last_signal

        message_text = event.message.message.strip()
        print(f"📨 Original message: {message_text}")

        if "✅" in message_text and "WIN" in message_text:
            sequence.append("win")
            win_type = "regular"
            if "✅¹" in message_text:
                win_type = "win1"
                print("✅¹ Detected: WIN 1")
            elif "✅²" in message_text:
                win_type = "win2"
                print("✅² Detected: WIN 2")
            else:
                print("✅ Detected: WIN")
            result_message = reformat_signal_message(None, True, win_type)
            await send_to_telegram_channel(result_message)
            return

        if "✖️ Loss" in message_text:
            sequence.append("loss")
            print("✖️ Detected: Loss")
            result_message = reformat_signal_message(None, True, "loss")
            await send_to_telegram_channel(result_message)
            return

        if "DOJI ⚖" in message_text:
            print("⚖️ Detected: DOJI - ignoring")
            return

        if all(keyword in message_text for keyword in ["Asset:", "Timeframe:", "Signal Time:", "Action:"]):
            formatted_message = reformat_signal_message(message_text)
            if formatted_message:
                print(f"🔄 Reformatted message: {formatted_message}")
                await send_to_telegram_channel(formatted_message)
                sequence.append("call")
                last_signal = formatted_message
                print("📈 Detected: SIGNAL")
            else:
                print("⚠️ Not a valid signal format - ignoring")
        else:
            print("⚠️ Message doesn't match expected format - ignoring")

        if len(sequence) > 12:
            sequence.pop(0)

        if sequence == ["call", "win"] * 6:
            print("🔥 Detected 6 consecutive SIGNAL → WIN pairs. Sending webhook...")
            try:
                requests.post(webhook_url, json={"message": "6 consecutive trading wins detected on M5!"})
                print("✅ Webhook sent.")
            except Exception as e:
                print("❌ Webhook failed:", str(e))
            sequence = []

    try:
        print("🚀 Starting client...")
        if not client.is_connected():
            await client.start()
        print("✅ Bot started successfully!")
        print("👂 Listening for messages...")
        await client.run_until_disconnected()
    except Exception as e:
        print(f"❌ Error running bot: {str(e)}")
        raise
    finally:
        if client and client.is_connected():
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
