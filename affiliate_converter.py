import logging
import re
from aliexpress_api import AliexpressApi, models
from dotenv import load_dotenv
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
ALIEXPRESS_KEY = os.getenv('ALIEXPRESS_KEY')
ALIEXPRESS_SECRET = os.getenv('ALIEXPRESS_SECRET')
ALIEXPRESS_TRACKING_ID = os.getenv('ALIEXPRESS_TRACKING_ID')

# Initialize the AliExpress API with your credentials
aliexpress = AliexpressApi(ALIEXPRESS_KEY, ALIEXPRESS_SECRET, models.Language.EN, models.Currency.USD, ALIEXPRESS_TRACKING_ID)

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

def is_aliexpress_affiliate_link(url, tracking_id):
    return any(part in url for part in [tracking_id, 's.click.aliexpress.com'])

def convert_affiliate_links(content):
    # Regex to identify links in the message
    url_pattern = re.compile(r'https?://[^\s]+')
    urls = url_pattern.findall(content)

    for url in urls:
        if "aliexpress.com" in url:
            if not is_aliexpress_affiliate_link(url, ALIEXPRESS_TRACKING_ID):
                affiliate_url = generate_affiliate_link(url)
                if affiliate_url:
                    content = content.replace(url, affiliate_url)
    
    return content
