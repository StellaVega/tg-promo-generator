## config.py

import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
GIT_TOKEN = os.getenv('GIT_TOKEN')
GITHUB_REPOSITORY = os.getenv('GITHUB_REPOSITORY')
RSS_FEED_PATH = 'rss-feed_promo.xml'

# Ensure the cache directory exists
CACHE_DIR = "C:\\Bots\\cache-promo"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
