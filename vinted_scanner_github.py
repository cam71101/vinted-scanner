import os
import json
import requests
import sys
from datetime import datetime

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GIST_ID = os.environ.get('GIST_ID')

# Load queries from file
try:
    with open('queries.json', 'r') as f:
        QUERIES = json.load(f)
except Exception as e:
    print(f"Error loading queries.json: {e}")
    QUERIES = []

def load_seen_items():
    """Load previously seen items from GitHub Gist"""
    if not GITHUB_TOKEN or not GIST_ID:
        return set()
    
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
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
    if not GITHUB_TOKEN or not GIST_ID:
        return
    
    try:
        headers = {
            'Authorization': f'token {GITHUB_TOKEN}',
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

def get_item_details(session, item_id):
    """Fetch full item details including description"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Referer': 'https://www.vinted.co.uk/',
        }
        
        url = f'https://www.vinted.co.uk/api/v2/items/{item_id}'
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('item', {})
        else:
            print(f"Failed to get item details: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error fetching item details: {e}")
        return None

def send_telegram_message(item):
    """Send notification via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return
    
    # Get description and truncate if too long
    description = item.get('description', 'No description')
    if len(description) > 300:
        description = description[:297] + '...'
    
    # Get color info
    color = 'N/A'
    if item.get('color'):
        color = item['color']
    
    # Get price - extract amount from nested dict
    price = 'N/A'
    if item.get('price'):
        price_data = item['price']
        if isinstance(price_data, dict) and 'amount' in price_data:
            price = f"£{price_data['amount']}"
        else:
            price = str(price_data)
    
    message = f"""🆕 New Vinted Item!

📌 {item['title']}
💰 Price: {price}
👕 Brand: {item.get('brand_title', 'N/A')}
📏 Size: {item.get('size_title', 'N/A')}
✨ Condition: {item.get('status', 'N/A')}

📝 Description:
{description}

🔗 {item['url']}
"""
    
    try:
        # Try to send with photo
        if item.get('photo'):
            photo_url = item['photo'].get('url', '')
            if photo_url:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={
                        'chat_id': TELEGRAM_CHAT_ID,
                        'photo': photo_url,
                        'caption': message
                    },
                    timeout=10
                )
                print(f"Sent notification with photo for: {item['title']}")
                return
        
        # Fallback to text only
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message
            },
            timeout=10
        )
        print(f"Sent notification for: {item['title']}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def get_vinted_session():
    """Create a session with proper headers to bypass bot detection"""
    session = requests.Session()
    
    # First, visit the homepage to get cookies
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        # Visit homepage first
        response = session.get('https://www.vinted.co.uk/', headers=headers, timeout=10)
        print(f"Homepage status: {response.status_code}")
        return session
    except Exception as e:
        print(f"Error creating session: {e}")
        return session

def search_vinted(session, query):
    """Search Vinted API with proper session"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Referer': 'https://www.vinted.co.uk/',
        }
        
        url = 'https://www.vinted.co.uk/api/v2/catalog/items'
        response = session.get(url, params=query, headers=headers, timeout=30)
        
        print(f"API Response status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API returned status {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"Error searching Vinted: {e}")
        return None

def main():
    print(f"Starting Vinted scanner at {datetime.now()}")
    print(f"Configured queries: {len(QUERIES)}")
    
    if not QUERIES:
        print("No queries configured!")
        return
    
    # Load previously seen items
    seen_items = load_seen_items()
    new_items_found = 0
    
    # Create session
    session = get_vinted_session()
    
    # Process each query
    for i, query in enumerate(QUERIES):
        search_term = query.get('search_text', 'all items')
        print(f"\nProcessing query {i+1}/{len(QUERIES)}: {search_term}")
        
        result = search_vinted(session, query)
        
        if not result:
            print("No results returned")
            continue
        
        items = result.get('items', [])
        print(f"Found {len(items)} items in results")
        
        # Check for new items
        for item in items:
            item_id = str(item['id'])
            
            if item_id not in seen_items:
                print(f"NEW ITEM: {item['title']} (ID: {item_id})")
                
                # Fetch full item details to get description
                full_item = get_item_details(session, item_id)
                if full_item:
                    # Merge full details with basic item info
                    item.update(full_item)
                
                # Add full URL
                item['url'] = f"https://www.vinted.co.uk/items/{item_id}"
                
                # Send notification
                send_telegram_message(item)
                
                # Mark as seen
                seen_items.add(item_id)
                new_items_found += 1
            else:
                print(f"Already seen: {item['title']} (ID: {item_id})")
    
    # Save updated seen items
    save_seen_items(seen_items)
    
    print(f"\nScan complete!")
    print(f"New items found: {new_items_found}")
    print(f"Total tracked items: {len(seen_items)}")

if __name__ == "__main__":
    main()
