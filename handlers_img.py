import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils import temporary_storage  # Add this line to import temporary_storage

logger = logging.getLogger(__name__)

async def replace_image(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    if message_id in temporary_storage:
        small_images = temporary_storage[message_id].get('small_images', [])
        current_photo = temporary_storage[message_id].get('photo')
        logger.info(f"Current photo: {current_photo}")
        for idx, img_id in enumerate(small_images):
            if img_id != current_photo:
                callback_data_select = f"select_image:{message_id}:{idx}"
                callback_data_remove = f"remove_image:{message_id}:{idx}"

                keyboard = [
                    [InlineKeyboardButton("✅", callback_data=callback_data_select), InlineKeyboardButton("❌", callback_data=callback_data_remove)]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                try:
                    await update.callback_query.message.reply_photo(photo=img_id, reply_markup=reply_markup)
                    logger.info(f"Displayed image option: {img_id}")
                except Exception as e:
                    logger.error(f"Error displaying image option {img_id}: {e}")

async def handle_image_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    action, message_id, img_idx = data.split(":")
    message_id = int(message_id)
    img_idx = int(img_idx)

    logger.info(f"Image selection action: {action}, message_id: {message_id}, img_idx: {img_idx}")

    if action == "select_image":
        small_images = temporary_storage[message_id]['small_images']
        selected_image = small_images[img_idx]
        temporary_storage[message_id]['photo'] = selected_image
        logger.info(f"Selected image: {selected_image}")
        await refresh_main_reply(update, context, message_id)
    elif action == "remove_image":
        logger.info(f"Removing image message: {query.message.message_id}")
        try:
            await query.message.delete()
            logger.info(f"Image message {query.message.message_id} removed successfully.")
        except Exception as e:
            logger.error(f"Failed to remove image message {query.message.message_id}: {e}")

async def refresh_main_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, message_id: int) -> None:
    if message_id in temporary_storage:
        content = temporary_storage[message_id]['converted']
        chat_id = temporary_storage[message_id]['chat_id']
        photo = temporary_storage[message_id]['photo']

        keyboard = [
            [InlineKeyboardButton("Replace Image", callback_data=f"replace_image:{message_id}")],
            [InlineKeyboardButton("Edit Text", callback_data=f"edit_text:{message_id}")],
            [InlineKeyboardButton("Publish", callback_data=f"publish:{message_id}")],
            [InlineKeyboardButton("Cancel", callback_data=f"cancel:{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        bot = context.bot
        logger.info(f"Refreshing main reply with new photo: {photo}")
        try:
            if photo:
                sent_message = await bot.send_photo(chat_id=chat_id, photo=photo, caption=content, reply_markup=reply_markup)
            else:
                sent_message = await bot.send_message(chat_id=chat_id, text=content, reply_markup=reply_markup)
            
            message_ids = temporary_storage[message_id]['message_ids']
            for msg_id in message_ids:
                try:
                    await bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    logger.info(f"Deleted message with ID: {msg_id}")
                except Exception as e:
                    logger.error(f"Failed to delete message {msg_id}: {e}")

            temporary_storage[message_id]['message_ids'] = [sent_message.message_id]
        except Exception as e:
            logger.error(f"Error refreshing main reply: {e}")
