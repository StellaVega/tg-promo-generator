import logging
import base64
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from affiliate_converter import convert_affiliate_links, generate_affiliate_link
from rss_feed_generator import add_to_rss_feed
from utils import update_github_file, temporary_storage, download_image, upload_to_github
from aliexpress_scraper import fetch_aliexpress_product_details
import re
from handlers_img import handle_image_selection, replace_image

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! I am your promotion bot.')

async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    content = message.caption if message.caption else message.text

    if content:
        logger.info(f"Received forwarded message: {content}")

        # Extract URL from the message content
        url_pattern = re.compile(r'https?://[^\s]+')
        url_match = url_pattern.search(content)
        if not url_match:
            logger.error("No URL found in the message.")
            return

        url = url_match.group(0)

        # Generate the affiliate link
        affiliate_link = generate_affiliate_link(url)
        if not affiliate_link:
            logger.error("Failed to generate affiliate link.")
            return

        # Fetch product details
        product_details = fetch_aliexpress_product_details(url)

        if product_details:
            product_id = product_details['product_id']
            product_title = product_details['product_title']
            small_images = product_details['small_image_urls']

            # Add the Telegram photo URL to the list of small images
            if message.photo:
                telegram_photo_url = await context.bot.get_file(message.photo[-1].file_id)
                small_images.append(telegram_photo_url.file_path)
                logger.info(f"Telegram Photo URL: {telegram_photo_url.file_path}")

            logger.info(f"Product ID: {product_id}")
            logger.info(f"Product Title: {product_title}")
            logger.info(f"Product Small Images: {small_images}")
            logger.info(f"Affiliate Link: {affiliate_link}")

            # Ensure temporary_storage is correctly initialized before appending
            temporary_storage[message.message_id] = {
                'original': content,
                'converted': convert_affiliate_links(content),
                'photo': message.photo[-1].file_id if message.photo else None,
                'chat_id': message.chat_id,
                'message_ids': [message.message_id],
                'product_id': product_id,
                'product_title': product_title,
                'small_images': small_images,
                'affiliate_link': affiliate_link
            }

            keyboard = [
                [InlineKeyboardButton("Replace Image", callback_data=f"replace_image:{message.message_id}")],
                [InlineKeyboardButton("Edit Text", callback_data=f"edit_text:{message.message_id}")],
                [InlineKeyboardButton("Publish", callback_data=f"publish:{message.message_id}")],
                [InlineKeyboardButton("Cancel", callback_data=f"cancel:{message.message_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if message.photo:
                sent_message = await message.reply_photo(
                    message.photo[-1].file_id,
                    caption=f"{convert_affiliate_links(content)}",
                    reply_markup=reply_markup
                )
            else:
                sent_message = await message.reply_text(
                    text=f"{convert_affiliate_links(content)}",
                    reply_markup=reply_markup
                )
        
            temporary_storage[message.message_id]['message_ids'].append(sent_message.message_id)
        else:
            logger.error("Failed to fetch product details from AliExpress.")

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split(":")
    command, message_id = parts[0], int(parts[1])
    
    logger.info(f"Button click received: {command}, message_id: {message_id}")

    if command == "replace_image":
        await replace_image(update, context, message_id)
    elif command == "edit_text":
        await query.message.reply_text(text="Please send the new text for the message.")
        context.user_data['editing_message_id'] = message_id
    elif command == "publish":
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f"confirm_publish:{message_id}")],
            [InlineKeyboardButton("No", callback_data=f"deny_publish:{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await query.message.reply_text(text="Are you sure you want to publish this message?", reply_markup=reply_markup)
        temporary_storage[message_id]['message_ids'].append(sent_message.message_id)
    elif command == "cancel":
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f"confirm_cancel:{message_id}")],
            [InlineKeyboardButton("No", callback_data=f"deny_cancel:{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        sent_message = await query.message.reply_text(text="Are you sure you want to cancel? This will delete all related messages.", reply_markup=reply_markup)
        temporary_storage[message_id]['message_ids'].append(sent_message.message_id)
    elif command == "confirm_publish":
        await confirm_publish(update, context, message_id)
    elif command == "deny_publish":
        await query.message.delete()
    elif command == "confirm_cancel":
        await confirm_cancel(update, context, message_id)
    elif command == "deny_cancel":
        await query.message.delete()
        original_message_id = temporary_storage[message_id]['message_ids'][-2]
        await context.bot.edit_message_reply_markup(
            chat_id=query.message.chat_id, 
            message_id=original_message_id, 
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Replace Image", callback_data=f"replace_image:{message_id}")],
                [InlineKeyboardButton("Edit Text", callback_data=f"edit_text:{message_id}")],
                [InlineKeyboardButton("Publish", callback_data=f"publish:{message_id}")],
                [InlineKeyboardButton("Cancel", callback_data=f"cancel:{message_id}")]
            ])
        )

async def receive_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'editing_message_id' in context.user_data:
        message_id = context.user_data['editing_message_id']
        new_text = update.message.text
        if message_id in temporary_storage:
            temporary_storage[message_id]['converted'] = new_text
            await update.message.reply_text('Text updated. Use Publish to publish the final message or Cancel to cancel it.')

async def confirm_publish(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    if message_id in temporary_storage:
        chat_id = temporary_storage[message_id]['chat_id']
        content = temporary_storage[message_id]['converted']
        original_content = temporary_storage[message_id]['original']
        photo_id = temporary_storage[message_id]['photo']
        product_id = temporary_storage[message_id]['product_id']

        image_url = None
        if photo_id:
            file_path = await download_image(context, photo_id, f"{product_id}-01.jpg")
            image_url = upload_to_github(file_path, f"{product_id}-01.jpg")

        add_to_rss_feed(
            content=content,
            title=original_content[:30] if len(original_content) > 30 else None,
            description=content,
            image_url=image_url
        )
        
        with open('rss-feed_promo.xml', 'r', encoding='utf-8') as file:
            rss_feed_content = file.read()
        
        rss_feed_content_base64 = base64.b64encode(rss_feed_content.encode('utf-8')).decode('utf-8')
        update_github_file(rss_feed_content_base64)
        
        bot = context.bot
        if photo_id:
            await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=content)
        else:
            await bot.send_message(chat_id=chat_id, text=content)
        
        message_ids = temporary_storage[message_id]['message_ids']
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Failed to delete message {msg_id}: {e}")
        del temporary_storage[message_id]
        await bot.send_message(chat_id, text='Message published and all related messages have been deleted.')

async def confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    if message_id in temporary_storage:
        chat_id = temporary_storage[message_id]['chat_id']
        message_ids = temporary_storage[message_id]['message_ids']
        bot = context.bot
        for msg_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                logger.error(f"Failed to delete message {msg_id}: {e}")
        del temporary_storage[message_id]
        await bot.send_message(chat_id, text='All related messages have been deleted.')

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    bot = context.bot

    async for message in bot.get_chat(chat_id).iter_history():
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
        except Exception as e:
            logger.error(f"Failed to delete message {message.message_id}: {e}")

def register_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded_message))
    application.add_handler(CallbackQueryHandler(handle_button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_text))
    application.add_handler(CallbackQueryHandler(handle_image_selection, pattern="^(select_image|remove_image):"))
