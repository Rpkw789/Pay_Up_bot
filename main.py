from telegram import Update, File
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import io
import requests
import base64
from APIkeys import OPENAPI_API_KEY, BOT_USERNAME, TOKEN



# Commands
async def start_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I convert a picture of your receipt into polls! Type "/Usage" to know how to use this Bot!')

async def usage_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This bot helps you to convert a picture of your receipt into a poll! Thereafter, you can forward it to your groupchat and use the poll to track who has paid for what item! Upload a picture here and I will generate the poll for you.')

async def help_command(update: Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('If the generation of the poll is not working, upload a clearer picture!')



# Responses
async def query_ai(image):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAPI_API_KEY}"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "Read this Image. If each meal item has additional ingredients in it, group the meal and it's ingredients together instead of having them as separate items.  Reply strictly in this format: Item1 - Price1 (Quantity1), Item2 - Price2 (Quantity2), ... . If there is any issue with reading it, strictly reply with: Error"
                },
                {
                "type": "image_url",
                "image_url": 
                {
                    "url": f"data:image/jpeg;base64,{image}"
                }
                }
            ]
            }
        ],
        "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if response.status_code == 200:
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} - {response.text}"



async def process_photo(photo_URL: str, context: ContextTypes.DEFAULT_TYPE):
    file: File = await context.bot.get_file(photo_URL)
    file_data = await file.download_as_bytearray()
    image = Image.open(io.BytesIO(file_data)).convert("RGB")

    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    ai_processed_text: str = await query_ai(img_base64)
    return ai_processed_text



async def send_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    question = "Reply the poll with the item you bought after you pay me."
    options = text.split(",")
    await update.message.reply_poll(
        question=question,
        options= options,
        is_anonymous=False,
        type="regular",
    )
    await update.message.reply_text("You can now forward this to your groupchat!")



async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_URL: str = update.message.photo[-1].file_id
    processed_text: str = await process_photo(photo_URL, context)
    if processed_text.startswith("Error"):
        await update.message.reply_text("Please send your photo again!")
    elif processed_text.startswith("Retake"):
        await update.message.reply_text("Please send a clearer photo!")
    else:
        await send_poll(update, context, processed_text)



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    if message_type == 'group':
        if BOT_USERNAME in text:
            response: str = "Hi! I do not work in a group chat."
        else:
            return
    else:
        return

    await update.message.reply_text(response)



async def error(update: Update, context:ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')




if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('usage', usage_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    app.run_polling(poll_interval=2)