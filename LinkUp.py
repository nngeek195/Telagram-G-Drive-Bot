import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import os
import pickle
import re
import mimetypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Global variables
FOLDER_ID = None  # Store the folder ID
UPLOAD_IN_PROGRESS = False

def authenticate_drive():
    """Authenticate with Google Drive."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Authentication failed or expired.")
    return build('drive', 'v3', credentials=creds)

async def start(update: Update, context: CallbackContext):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        'Hello! 👋\nSend me any file and I will upload it to your Google Drive folder.\n'
        'If this is your first time, please set your Google Drive folder link as follows:\n\n'
        '/setfolder <folder_link>.\n\n'
        'You can stop the process anytime by using /stop.'
    )

async def help_command(update: Update, context: CallbackContext):
    """Send a help message when the command /help is issued."""
    await update.message.reply_text(
        '📋 *Bot Instructions:*\n'
        '- Use /setfolder <folder_link> to set the Google Drive folder where files will be uploaded.\n'
        '- Send any file to upload it to Google Drive.\n'
        '- Use /stop to stop uploading files.'
    )

async def stop_upload(update: Update, context: CallbackContext):
    """Stop the current upload process."""
    global UPLOAD_IN_PROGRESS
    if UPLOAD_IN_PROGRESS:
        UPLOAD_IN_PROGRESS = False
        await update.message.reply_text('⛔ Upload process stopped. No more files will be uploaded.')
    else:
        await update.message.reply_text('❌ No upload process is currently running.')

async def set_folder(update: Update, context: CallbackContext):
    """Set the Google Drive folder where files will be uploaded."""
    global FOLDER_ID
    if context.args:
        folder_link = context.args[0]
        folder_id_match = re.search(r'\/folders\/([a-zA-Z0-9_-]+)', folder_link)
        if folder_id_match:
            FOLDER_ID = folder_id_match.group(1)
            await update.message.reply_text(f'✅ Folder set to: {folder_link}\nNow you can upload files to this folder.')
        else:
            await update.message.reply_text('❌ Invalid folder link. Please provide a valid Google Drive folder link.')
    else:
        await update.message.reply_text('❌ Please provide the Google Drive folder link using /setfolder <folder_link>.')

async def upload_file_to_drive(file_path, service):
    """Upload a file to Google Drive."""
    if not FOLDER_ID:
        raise Exception("No folder set. Use /setfolder to set a Google Drive folder.")

    # Detect MIME type dynamically
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'  # Default MIME type for unknown files

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [FOLDER_ID]  # Uploading to the specific folder
    }
    media = MediaFileUpload(file_path, mimetype=mime_type)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

async def handle_file(update: Update, context: CallbackContext):
    """Handle incoming files."""
    global UPLOAD_IN_PROGRESS
    if not FOLDER_ID:
        await update.message.reply_text('❌ Please set a Google Drive folder first using /setfolder <folder_link>.')
        return
    if UPLOAD_IN_PROGRESS:
        await update.message.reply_text('❗ Upload in progress. Please wait until the current upload is completed or use /stop to cancel.')
        return

    UPLOAD_IN_PROGRESS = True
    await update.message.reply_text('📥 Downloading your file, please wait...')

    # Get the file from Telegram
    if update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        file_name = update.message.document.file_name  # Original file name
    elif update.message.video:
        file = await context.bot.get_file(update.message.video.file_id)
        file_name = "video.mp4"  # Fallback name for videos (Telegram doesn't provide a file name for videos)
    else:
        await update.message.reply_text('❌ Unsupported file type.')
        UPLOAD_IN_PROGRESS = False
        return

    # Download the file with its original name
    file_path = file_name
    await file.download_to_drive(file_path)
    await update.message.reply_text('📤 Uploading to Google Drive, this might take a moment...')
    try:
        service = authenticate_drive()
        file_id = await upload_file_to_drive(file_path, service)
        os.remove(file_path)
        await update.message.reply_text(f'✅ File uploaded successfully!\n📄 *Google Drive File ID:* `{file_id}`\nThank you for using the bot! 🚀')
    except Exception as e:
        await update.message.reply_text(f'❌ Error during upload: {e}')
    finally:
        UPLOAD_IN_PROGRESS = False

def main():
    """Start the bot."""
    application = Application.builder().token('Telegram Token').build()

    # Command Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stop', stop_upload))
    application.add_handler(CommandHandler('setfolder', set_folder))

    # File Handler (supports all file types)
    application.add_handler(MessageHandler(filters.ALL, handle_file))

    application.run_polling()

if __name__ == '__main__':
    main()
