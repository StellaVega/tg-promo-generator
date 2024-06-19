import logging
from telegram.ext import ApplicationBuilder
from config import TELEGRAM_API_TOKEN
from handlers import register_handlers

# Set up logging with a custom filter to exclude logs from httpcore and telegram.ext
class CustomFilter(logging.Filter):
    def filter(self, record):
        if record.name.startswith('httpcore'):
            return False
        return True

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.addFilter(CustomFilter())

# Set specific log levels for certain modules
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram.ext.ExtBot').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)

def main():
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
    register_handlers(application)
    application.run_polling()

if __name__ == "__main__":
    main()
