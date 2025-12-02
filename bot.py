import tweepy
import requests
import xml.etree.ElementTree as ET
import time
import os
import random
import re
from html import unescape
from io import BytesIO

# ================================
# X (Twitter) API KEYS
# ================================
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# ================================
# API v2 Client (for tweeting)
# ================================
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

# ================================
# API v1.1 (for media upload)
# ================================
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api_v1 = tweepy.API(auth)

# ================================
# TRENDING TOPICS (Google News RSS)
# ================================
def fetch_trending_topics():
    try:
        url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        r = requests.get(url)
        r.raise_for_status()

        root = ET.fromstring(r.content)

        items = []
        for item in root.findall("./channel/item"):
            title = item.find("title").text
            desc = item.find("description").text

            if title and desc:
                items.append({
                    "title": title,
                    "description": desc
                })

        return items[:10] if items else []

    except Exception as e:
        print("⚠️ RSS fetch error:", e)
        return []

def clean_html(raw_html):
    clean = re.sub(r"<.*?>", "", raw_html)
    return unescape(clean)

previous_titles = set()

def search_image_bing(query):
    try:
        q = query.replace(" ", "+")
        url = f"https://www.bing.com/images/search?q={q}&form=HDRSC2"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)
        html = r.text

        matches = re.findall(r"murl&quot;:&quot;(.*?)&quot;", html)
        if matches:
            return matches[0]
        return None

    except Exception as e:
        print("⚠️ Image scrape failed:", e)
        return None

def download_image_memory(url):
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return BytesIO(r.content)
    except Exception:
        pass
    return None

def upload_image_memory(image_bytes):
    try:
        media = api_v1.media_upload(filename="image.jpg", file=image_bytes)
        return media.media_id_string
    except Exception as e:
        print("❌ Image upload error:", e)
        return None

def create_tweet_text(topic):
    title = clean_html(topic["title"])
    description = clean_html(topic["description"])

    if description.lower().startswith(title.lower()[:20]):
        description = ""

    if title in previous_titles:
        return None
    previous_titles.add(title)

    intros = [
        "🔥 Breaking Khabar!",
        "📰 Aaj Ki Taaza Update!",
        "📢 Trending News Alert!",
        "⚡ Fact Check This!",
        "🚨 Big Update!"
    ]

    hashtags = [
        "#Trending", "#IndiaNews", "#Breaking",
        "#LatestUpdate", "#TopStory", "#InShorts"
    ]

    intro = random.choice(intros)
    tag_string = " ".join(random.sample(hashtags, 3))

    tweet = (
        f"{intro}\n\n"
        f"👉 {title}\n\n"
        f"{description}\n\n"
        f"{tag_string}"
    )

    tweet += f"\n\n⏳ {int(time.time())}"

    return tweet[-275:]

# ================================
# MAIN BOT (Single-run mode)
# ================================
def run_bot(interval=3600):
    print("🚀 Bot started with Safety Mode ON.")

    # Run only ONE cycle for GitHub Actions
    for _ in range(1):

        topics = fetch_trending_topics()

        if not topics:
            print("⚠️ No topics returned.")
            return

        topic = random.choice(topics)
        tweet_text = create_tweet_text(topic)

        if not tweet_text:
            print("⚠️ Skipping empty or duplicate tweet.")
            return

        try:
            image_url = search_image_bing(topic["title"])
            media_id = None

            if image_url:
                img_bytes = download_image_memory(image_url)
                if img_bytes:
                    media_id = upload_image_memory(img_bytes)

            if media_id:
                client.create_tweet(text=tweet_text, media_ids=[media_id])
            else:
                client.create_tweet(text=tweet_text)

            print("✅ Tweet posted successfully!")
            print("Tweet:", tweet_text)

        except Exception as e:
            print("❌ Tweet error:", e)
            return

# ================================
# START BOT
# ================================
if __name__ == "__main__":
    run_bot(interval=3600)
