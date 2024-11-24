from telethon import TelegramClient, events
import asyncio
import requests
import threading
from flask import Flask, jsonify

# Telegram API credentials
api_id = 'your_api_id'  # Replace with your API ID
api_hash = 'your_api_hash'  # Replace with your API hash

# Channel names (replace with actual usernames or IDs)
source_channel_name = 'your_source_channel'  # Replace with your source channel
target_channel_name = 'your_target_channel'  # Replace with your target channel

# Google Drive file link for session file
drive_link = "your_google_drive_link"  # Replace with your Google Drive link

# Function to download session file from Google Drive
def download_session_file():
    response = requests.get(drive_link)
    
    if response.status_code == 200:
        with open('session_name.session', 'wb') as f:
            f.write(response.content)
        print("Session file downloaded.")
    else:
        print("Failed to download session file. Status code:", response.status_code)

async def start_bot():
    # Download the session file before creating the Telegram client
    download_session_file()

    async with TelegramClient('session_name', api_id, api_hash) as client:
        print("Bot started.")

        # Fetch all dialogs (chats, groups, and channels the bot has access to)
        dialogs = await client.get_dialogs()

        # Find the channels by their names
        source_channel = None
        target_channel = None
        for dialog in dialogs:
            if dialog.name == source_channel_name:
                source_channel = dialog.entity
            if dialog.name == target_channel_name:
                target_channel = dialog.entity

        if source_channel and target_channel:
            print(f"Found source channel: {source_channel_name}")
            print(f"Found target channel: {target_channel_name}", flush=True)
        else:
            print(f"Could not find one or both channels. Available channels:")
            for dialog in dialogs:
                print(f"- {dialog.name} (ID: {dialog.id})")
            return

        # Handler for new messages
        @client.on(events.NewMessage(chats=source_channel))
        async def handler(event):
            await forward_message(event)

        # Handler for edited messages
        @client.on(events.MessageEdited(chats=source_channel))
        async def edit_handler(event):
            await forward_message(event, is_edit=True)

        async def forward_message(event, is_edit=False):
            message = event.message
            try:
                if message.text and not message.photo:  # Text message (no photo)
                    formatted_text = re.sub(r'(\d+)', r' \1 ', message.text)
                    sent_message = await client.send_message(target_channel, formatted_text)
                    print(f"{'Edited' if is_edit else 'Text'} message sent to {target_channel_name}: {formatted_text}")
                    
                elif message.photo:  # Photo message with or without caption
                    file_path = await message.download_media()
                    caption = message.text or ""
                    await client.send_file(target_channel, file_path, caption=caption)
                    print(f"{'Edited' if is_edit else 'Photo'} sent to {target_channel_name} with caption: {caption}")
                
                elif message.voice:  # Voice message
                    file_path = await message.download_media()
                    await client.send_file(target_channel, file_path)
                    print(f"{'Edited' if is_edit else 'Voice'} message sent to {target_channel_name}")

                elif message.document:  # Document message
                    file_path = await message.download_media()
                    await client.send_file(target_channel, file_path)
                    print(f"{'Edited' if is_edit else 'Document'} sent to {target_channel_name}")

                else:
                    print("Message type not supported.")
                    
            except Exception as e:
                print(f"Failed to forward message: {e}")

        # Keep the bot running
        await client.run_until_disconnected()

# Flask app setup
app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, this is the home page of the bot!"

# Health check route to avoid inactivity
@app.route('/health_check', methods=['GET'])
def health_check():
    return jsonify({"status": "OK"}), 200

# Function to run the bot in a separate thread
def run_bot():
    asyncio.run(start_bot())

if __name__ == '__main__':
    # Start the bot in a separate thread
    threading.Thread(target=run_bot).start()
    # Start the Flask server
    app.run(host='0.0.0.0', port=8000)
