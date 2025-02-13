from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os, pickle

SCOPES = ['https://www.googleapis.com/auth/drive.file']
AUTH_CODE = 0

def authenticate_drive(auth_code=None):
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            if auth_code:
                creds = flow.fetch_token(code=auth_code)
            else:
                auth_url, _ = flow.authorization_url(prompt='consent')
                return auth_url  # Return the URL to the user
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! 👋\nSend me a video and I will upload it to Google Drive for you.\nIf you are using this bot for the first time, please authenticate using /auth.')

async def auth(update: Update, context: CallbackContext):
    auth_url = authenticate_drive()
    if auth_url:
        await update.message.reply_text(f'🔗 Please authorize the bot by visiting this link:\n{auth_url}\n\nThen send me the authorization code using /code <your_code>.')

async def receive_code(update: Update, context: CallbackContext):
    code = ' '.join(context.args)
    try:
        service = authenticate_drive(code)
        if service:
            await update.message.reply_text('✅ Authorization successful! You can now upload videos.')
        else:
            await update.message.reply_text('❌ Authorization failed. Please try again.')
    except Exception as e:
        await update.message.reply_text(f'❌ Error: {e}')

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text('📋 *Bot Instructions:*\n- Use /auth to authorize Google Drive access.\n- Send any video file to upload it directly to your Google Drive.\n- Use /status to check the current upload progress.\n- Use /cancel to stop an ongoing upload.\n- Need assistance? Contact support@example.com')

async def upload_video_to_drive(file_path, service):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

async def handle_video(update: Update, context: CallbackContext):
    await update.message.reply_text('📥 Downloading your video, please wait...')
    video = update.message.video
    file = await context.bot.get_file(video.file_id)
    file_path = 'video.mp4'
    await file.download_to_drive(file_path)

    await update.message.reply_text('📤 Uploading to Google Drive, this might take a moment...')
    service = authenticate_drive()
    file_id = await upload_video_to_drive(file_path, service)
    os.remove(file_path)

    await update.message.reply_text(f'✅ Video uploaded successfully!\n📄 *Google Drive File ID:* `{file_id}`\nThank you for using the bot! 🚀')

def main():
    application = Application.builder().token('7550334516:AAGxKa9Y2FPu1CgnfTyGaqr2BaSNglHQzZ0').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('auth', auth))
    application.add_handler(CommandHandler('code', receive_code))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))

    application.run_polling()

if __name__ == '__main__':
    main()
