import logging
import re
import requests
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
        return response
    except Exception as e:
        logging.error(f"Request failed: {e}")
        return None

def fetch_aliexpress_product_details(url):
    resolved_url = resolve_shortened_url(url)
    if resolved_url:
        product_id = get_product_id(resolved_url)
        if product_id:
            product_details = get_product_details(product_id)
            if product_details:
                product_info = product_details[0]
                return {
                    'product_id': product_info.product_id,
                    'product_title': product_info.product_title,
                    'small_image_urls': product_info.product_small_image_urls,
                    'promotion_link': product_info.promotion_link,
                }
    return None
