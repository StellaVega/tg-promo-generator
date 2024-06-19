## standalone-reference.py

import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import logging
import re
import requests
from aliexpress_api import AliexpressApi, models

# Load environment variables from .env file in the same directory as the script
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get the Telegram API token from environment variables
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

# AliExpress API credentials
ALIEXPRESS_KEY = os.getenv('ALIEXPRESS_KEY')
ALIEXPRESS_SECRET = os.getenv('ALIEXPRESS_SECRET')
ALIEXPRESS_TRACKING_ID = os.getenv('ALIEXPRESS_TRACKING_ID')

# Initialize the AliExpress API with your credentials
aliexpress = AliexpressApi(ALIEXPRESS_KEY, ALIEXPRESS_SECRET, models.Language.EN, models.Currency.USD, ALIEXPRESS_TRACKING_ID)

# Temporary storage for product details
product_cache = {}

def resolve_shortened_url(url):
    try:
        response = requests.head(url, allow_redirects=True)
        resolved_url = response.url
        logging.debug(f"Resolved URL: {resolved_url}")
        return resolved_url
    except Exception as e:
        logging.error(f"Failed to resolve shortened URL: {e}")
        return None

def get_product_id(url):
    match = re.search(r'/item/(\d+).html', url)
    if not match:
        match = re.search(r'/(\d+)\.html', url)
    if match:
        product_id = match.group(1)
        logging.debug(f"Extracted Product ID: {product_id}")
        return product_id
    else:
        logging.warning("No product ID found in the URL.")
        return None

def get_product_details(product_id):
    try:
        logging.debug(f"Fetching details for Product ID: {product_id}")
        response = aliexpress.get_products_details([product_id])
        logging.debug(f"API Response: {response}")
        if response:
            product_details = response[0]
            return product_details
        else:
            logging.error(f"No details found for Product ID: {product_id}")
            return None
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return None

def generate_affiliate_link(source_url):
    try:
        logging.debug(f"Generating affiliate link for URL: {source_url}")
        response = aliexpress.get_affiliate_links(source_url, tracking_id=ALIEXPRESS_TRACKING_ID)
        logging.debug(f"API Response: {response}")

        affiliate_link = None
        if isinstance(response, list):
            for link_info in response:
                if hasattr(link_info, 'promotion_link'):
                    affiliate_link = link_info.promotion_link
                    break
        if affiliate_link:
            logging.debug(f"Generated affiliate link: {affiliate_link}")
            return affiliate_link
        else:
            logging.warning("No affiliate links found.")
            return None
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return None

async def aliexpress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    url = 'https://a.aliexpress.com/_opN11Ia'  # Test AliExpress link for debugging
    await handle_aliexpress_link(update, context, url)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if 'aliexpress.com' in text:
        await handle_aliexpress_link(update, context, text)
    else:
        await update.message.reply_text("Please send a valid AliExpress link.")

async def handle_aliexpress_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    resolved_url = resolve_shortened_url(url)
    if resolved_url:
        product_id = get_product_id(resolved_url)
        if product_id:
            product_details = get_product_details(product_id)
            if product_details:
                affiliate_link = generate_affiliate_link(product_details.product_detail_url)
                if not affiliate_link:
                    affiliate_link = product_details.promotion_link
                
                product_cache[product_id] = {
                    'title': product_details.product_title,
                    'id': product_details.product_id,
                    'small_images': product_details.product_small_image_urls,
                    'promotion_link': affiliate_link
                }
                logger.info(f"Product ID: {product_details.product_id}")
                logger.info(f"Product Title: {product_details.product_title}")
                logger.info(f"Promotion Link: {affiliate_link}")
                logger.info(f"Number of Images: {len(product_details.product_small_image_urls)}")
                
                buttons = [
                    [InlineKeyboardButton("Cancel", callback_data=f"cancel_{product_id}"),
                     InlineKeyboardButton("Replace Image", callback_data=f"replace_{product_id}_0")]
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                initial_message = await update.message.reply_photo(
                    photo=product_details.product_small_image_urls[0],
                    caption=f"{product_details.product_title}\n\n[Buy Now]({affiliate_link})",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                context.chat_data['initial_message_id'] = initial_message.message_id
                context.chat_data['image_messages'] = []

            else:
                logger.error(f"Failed to fetch product details for Product ID: {product_id}")
                await update.message.reply_text("Failed to fetch product details.")
        else:
            logger.error(f"Failed to extract Product ID from URL: {resolved_url}")
            await update.message.reply_text("Failed to extract Product ID.")
    else:
        logger.error(f"Failed to resolve shortened URL: {url}")
        await update.message.reply_text("Failed to resolve shortened URL.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("cancel_"):
        product_id = data.split("_")[1]
        await query.message.delete()
        for msg_id in context.chat_data.get('image_messages', []):
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Failed to delete message ID {msg_id}: {e}")
        product_cache.pop(product_id, None)
        context.chat_data['image_messages'] = []

    elif data.startswith("replace_"):
        product_id = data.split("_")[1]
        images = product_cache[product_id]['small_images']
        for index, image_url in enumerate(images):
            buttons = [
                [InlineKeyboardButton("✅", callback_data=f"select_{product_id}_{index}"),
                 InlineKeyboardButton("❌", callback_data=f"delete_{product_id}_{index}")]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            message = await query.message.reply_photo(photo=image_url, reply_markup=reply_markup)
            context.chat_data['image_messages'].append(message.message_id)

    elif data.startswith("delete_"):
        _, product_id, image_index = data.split("_")
        try:
            await query.message.delete()
        except Exception as e:
            logger.error(f"Failed to delete message: {e}")

    elif data.startswith("select_"):
        _, product_id, selected_image_index = data.split("_")
        selected_image_index = int(selected_image_index)
        images = product_cache[product_id]['small_images']
        selected_image = images[selected_image_index]
        product = product_cache[product_id]

        # Delete initial message with outdated image
        initial_message_id = context.chat_data.get('initial_message_id')
        if initial_message_id:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=initial_message_id)
            except Exception as e:
                logger.error(f"Failed to delete initial message ID {initial_message_id}: {e}")

        for msg_id in context.chat_data.get('image_messages', []):
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Failed to delete message ID {msg_id}: {e}")

        context.chat_data['image_messages'] = []

        buttons = [
            [InlineKeyboardButton("Cancel", callback_data=f"cancel_{product_id}"),
             InlineKeyboardButton("Replace Image", callback_data=f"replace_{product_id}_0")]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        new_message = await query.message.reply_photo(
            photo=selected_image,
            caption=f"{product['title']}\n\n[Buy Now]({product['promotion_link']})",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        context.chat_data['initial_message_id'] = new_message.message_id

def main():
    logger.info("Starting bot...")
    try:
        application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
        logger.info("Bot started successfully")

        application.add_handler(CommandHandler("aliexpress", aliexpress_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))

        logger.info("Command handler added")
        application.run_polling()
        logger.info("Bot is polling for updates...")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
