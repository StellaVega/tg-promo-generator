from feedgen.feed import FeedGenerator
from xml.etree import ElementTree as ET
import os

RSS_FEED_PATH = 'rss-feed_promo.xml'  # Place the file at the root level

def create_feed():
    fg = FeedGenerator()
    fg.title('Promotion Feed')
    fg.link(href='http://example.com', rel='alternate')
    fg.description('Latest promotions and deals')
    fg.language('en')
    return fg

def add_to_rss_feed(content, title=None, description=None, image_url=None):
    if os.path.exists(RSS_FEED_PATH):
        tree = ET.parse(RSS_FEED_PATH)
        root = tree.getroot()
        
        # Create a new feed generator and load the existing feed
        fg = FeedGenerator()
        fg.title(root.find('channel/title').text)
        fg.link(href=root.find('channel/link').text, rel='alternate')
        fg.description(root.find('channel/description').text)
        fg.language('en')
        fg.rss_str(ET.tostring(root, encoding='utf-8', method='xml'))
    else:
        fg = create_feed()

    fe = fg.add_entry()
    fe.title(title if title else content[:30])  # Use provided title or first 30 characters of the content
    fe.link(href='http://example.com')  # Replace with the actual link
    fe.description(description if description else content)
    
    if image_url:
        fe.enclosure(image_url, 0, 'image/jpeg')  # Add image URL

    fg.rss_file(RSS_FEED_PATH)
