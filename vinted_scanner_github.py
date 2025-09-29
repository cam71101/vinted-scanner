import os
import json
import requests
import time
from datetime import datetime

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GIT_TOKEN = os.environ.get('GIT_TOKEN')
GIST_ID = os.environ.get('GIST_ID')

VINTED_API_URL = "https://www.vinted.co.uk/api/v2/catalog/items"

try:
    with open('queries.json', 'r') as f:
        QUERIES = json.load(f)
except Exception as e:
    print(f"Error loading queries.json: {e}")
    QUERIES = []

def load_seen_items():
    """Load previously seen items from GitHub Gist"""
    if not GIT_TOKEN or not GIST_ID:
        print("Warning: GitHub token or Gist ID not configured. Will check all items.")
        return set()
    
    try:
        headers = {
            'Authorization': f'token {GIT_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get(f'https://api.github.com/gists/{GIST_ID}', headers=headers)
        response.raise_for_status()
        
        gist_data = response.json()
        content = gist_data['files']['vinted_seen_items.json']['content']
        seen_items = json.loads(content)
        print(f"Loaded {len(seen_items)} previously seen items")
        return set(seen_items)
    except Exception as e:
        print(f"Error loading seen items: {e}")
        return set()

def save_seen_items(seen_items):
    """Save seen items to GitHub Gist"""
    if not GIT_TOKEN or not GIST_ID:
        print("Warning: Cannot save seen items - GitHub token or Gist ID not configured")
        return
    
    try:
        headers = {
            'Authorization': f'token {GIT_TOKEN}',
            'Accept': 'application/vnd.github.v3+json'
        }
        data = {
            'files': {
                'vinted_seen_items.json': {
                    'content': json.dumps(list(seen_items))
                }
            }
        }
        response = requests.patch(f'https://api.github.com/gists/{GIST_ID}', 
                                 headers=headers, 
                                 json=data)
        response.raise_for_status()
        print(f"Saved {len(seen_items)} seen items to Gist")
    except Exception as e:
        print(f"Error saving seen items: {e}")

def send_telegram_message(item):
    """Send notification via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured, skipping notification")
        return
    
    message = f"""
🆕 New Vinted Item!

Title: {item['title']}
Price: {item['price']}
Brand: {item.get('brand_title', 'N/A')}
Size: {item.get('size_title', 'N/A')}

Link: {item['url']}
"""
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        # Send photo if available
        if item.get('photo'):
            photo_url = item['photo'].get('full_size_url') or item['photo'].get('url')
            if photo_url:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={
                        'chat_id': TELEGRAM_CHAT_ID,
                        'photo': photo_url,
                        'caption': message
                    }
                )
        else:
            requests.post(url, json=data)
            
        print(f"Sent notification for item: {item['title']}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def search_vinted(query):
    """Search Vinted API"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(VINTED_API_URL, params=query, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching Vinted: {e}")
        return None

def main():
    print(f"Starting Vinted scanner at {datetime.now()}")
    print(f"Configured queries: {len(QUERIES)}")
    
    # Load previously seen items
    seen_items = load_seen_items()
    new_items_found = 0
    
    # Process each query
    for i, query in enumerate(QUERIES):
        print(f"\nProcessing query {i+1}/{len(QUERIES)}: {query.get('search_text', 'all items')}")
        
        result = search_vinted(query)
        if not result:
            continue
        
        items = result.get('items', [])
        print(f"Found {len(items)} items")
        
        # Check for new items
        for item in items:
            item_id = str(item['id'])
            
            if item_id not in seen_items:
                print(f"New item found: {item['title']} (ID: {item_id})")
                
                # Add full URL to item
                item['url'] = f"https://www.vinted.co.uk/items/{item_id}"
                
                # Send notification
                send_telegram_message(item)
                
                # Mark as seen
                seen_items.add(item_id)
                new_items_found += 1
                
                # Small delay to avoid rate limiting
                time.sleep(1)
        
        # Delay between queries
        time.sleep(2)
    
    # Save updated seen items
    save_seen_items(seen_items)
    
    print(f"\nScan complete! Found {new_items_found} new items")
    print(f"Total tracked items: {len(seen_items)}")

if __name__ == "__main__":
    main()
