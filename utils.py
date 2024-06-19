import os
import base64
import logging
import requests
from config import GIT_TOKEN, GITHUB_REPOSITORY, RSS_FEED_PATH, CACHE_DIR

logger = logging.getLogger(__name__)

temporary_storage = {}

def update_github_file(content):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/{RSS_FEED_PATH}"
    headers = {
        "Authorization": f"token {GIT_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()['sha']
    else:
        sha = None

    data = {
        "message": "Update RSS feed",
        "content": content,
        "sha": sha
    }

    response = requests.put(url, json=data, headers=headers)
    if response.status_code in [200, 201]:
        logger.info("RSS feed updated on GitHub.")
    else:
        logger.error(f"Failed to update RSS feed on GitHub: {response.json()}")

async def download_image(context, file_id, file_name):
    file = await context.bot.get_file(file_id)
    file_path = os.path.join(CACHE_DIR, file_name)
    await file.download_to_drive(file_path)
    logger.info(f"Photo downloaded to {file_path}")
    return file_path

def upload_to_github(file_path, file_name):
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/contents/cache-image/{file_name}"
    
    with open(file_path, 'rb') as file:
        content = base64.b64encode(file.read()).decode('utf-8')
    
    data = {
        "message": f"Add {file_name}",
        "committer": {
            "name": "Your Name",
            "email": "your-email@example.com"
        },
        "content": content
    }
    
    headers = {
        "Authorization": f"token {GIT_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 201:
        logger.info("File uploaded to GitHub successfully")
        return response.json()['content']['download_url']
    else:
        logger.error(f"Failed to upload file to GitHub: {response.status_code}, {response.json()}")
        return None
