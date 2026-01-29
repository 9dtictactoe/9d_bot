import os
import time
import logging
import random
from datetime import datetime
import json
import requests
from apscheduler.schedulers.background import BackgroundScheduler
import tweepy
from flask import Flask, request

# ------------------------------------------------------------
# CONFIG & LOGGING
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - 9DTTT BOT LOG - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("9dttt_bot.log"), logging.StreamHandler()]
)

GAME_LINK = "https://www.9dttt.com"
BOT_NAME = "9DTTT BOT"

# Configuration constants
TWITTER_CHAR_LIMIT = 280
HUGGING_FACE_TIMEOUT = 10
BROADCAST_MIN_INTERVAL = 120  # minutes
BROADCAST_MAX_INTERVAL = 240  # minutes
MENTION_CHECK_MIN_INTERVAL = 15  # minutes
MENTION_CHECK_MAX_INTERVAL = 30  # minutes

# ------------------------------------------------------------
# TWITTER AUTH
# ------------------------------------------------------------
CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_SECRET = os.getenv('ACCESS_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
HUGGING_FACE_TOKEN = os.getenv('HUGGING_FACE_TOKEN')

# Validate required credentials
required_credentials = {
    'CONSUMER_KEY': CONSUMER_KEY,
    'CONSUMER_SECRET': CONSUMER_SECRET,
    'ACCESS_TOKEN': ACCESS_TOKEN,
    'ACCESS_SECRET': ACCESS_SECRET,
    'BEARER_TOKEN': BEARER_TOKEN
}
missing_credentials = [key for key, value in required_credentials.items() if not value]
if missing_credentials:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_credentials)}")

client = tweepy.Client(
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    bearer_token=BEARER_TOKEN,
    wait_on_rate_limit=True
)

auth_v1 = tweepy.OAuth1UserHandler(
    CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_SECRET
)
api_v1 = tweepy.API(auth_v1, wait_on_rate_limit=True)

# ------------------------------------------------------------
# SAFE POSTING FUNCTION - v2 + v1.1 fallback for 402 CreditsDepleted
# ------------------------------------------------------------
def safe_post_tweet(text, media_ids=None, in_reply_to_tweet_id=None):
    """
    Replacement for client.create_tweet().
    Tries v2 → falls back to v1.1 ONLY on 402 CreditsDepleted / Payment Required.
    Handles media IDs (from v1.1 upload) and replies.
    """
    original_text = text

    # Quick truncation safeguard
    if len(text) > TWITTER_CHAR_LIMIT:
        if in_reply_to_tweet_id:
            text = text[:TWITTER_CHAR_LIMIT - 60] + "..."
        else:
            text = text[:TWITTER_CHAR_LIMIT - 20] + "…"

    try:
        # Try v2 (best on paid tiers or enrolled free)
        kwargs = {"text": text}
        if media_ids:
            kwargs["media_ids"] = media_ids
        if in_reply_to_tweet_id:
            kwargs["in_reply_to_tweet_id"] = in_reply_to_tweet_id

        client.create_tweet(**kwargs)
        logging.info(f"Posted via v2: {original_text[:60]}...")
        return True

    except tweepy.TweepyException as e:
        error_str = str(e).lower()
        if "402" in error_str or "creditsdepleted" in error_str or "payment required" in error_str:
            logging.warning("v2 blocked (402 CreditsDepleted) → fallback to v1.1")
        else:
            logging.error(f"v2 failed (other error): {e}")
            return False

    # Fallback: v1.1 (still allows basic posting + media on many Free setups)
    try:
        status_kwargs = {"status": text}
        if media_ids:
            status_kwargs["media_ids"] = media_ids
        if in_reply_to_tweet_id:
            status_kwargs["in_reply_to_status_id"] = in_reply_to_tweet_id
            status_kwargs["auto_populate_reply_metadata"] = True

        api_v1.update_status(**status_kwargs)
        logging.info(f"Posted via v1.1 fallback: {original_text[:60]}...")
        return True

    except Exception as v1_err:
        logging.error(f"v1.1 fallback failed: {v1_err}")
        return False

# ------------------------------------------------------------
# FLASK APP FOR GAME EVENTS
# ------------------------------------------------------------
app = Flask(__name__)

@app.post("/9dttt-event")
def game_event():
    if not request.json:
        return {"error": "Invalid request: JSON body required"}, 400
    event = request.json
    game_event_bridge(event)
    return {"ok": True}

# ------------------------------------------------------------
# FILES & MEDIA
# ------------------------------------------------------------
PROCESSED_MENTIONS_FILE = "9dttt_processed_mentions.json"
MEDIA_FOLDER = "media/"

def load_json_set(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return set(json.load(f))
    return set()

def save_json_set(data, filename):
    try:
        with open(filename, 'w') as f:
            json.dump(list(data), f)
    except (IOError, OSError) as e:
        logging.error(f"Failed to save {filename}: {e}")

def get_random_media_id():
    if not os.path.exists(MEDIA_FOLDER):
        return None
    media_files = [
        f for f in os.listdir(MEDIA_FOLDER)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp4'))
    ]
    if not media_files:
        return None
    media_path = os.path.join(MEDIA_FOLDER, random.choice(media_files))
    try:
        media = api_v1.media_upload(media_path)
        return media.media_id_string
    except Exception as e:
        logging.error(f"Media upload failed: {e}")
        return None

# ------------------------------------------------------------
# BOT PERSONALITY TONES + LORE (unchanged)
# ------------------------------------------------------------
# ... (all PERSONALITY_TONES, pick_tone, get_personality_line, TIME_PHRASES, GAME_EVENTS, STRATEGY_TIPS, GAME_FACTS, PLAYER_ACHIEVEMENTS, MOTIVATIONAL unchanged - paste your original here if needed)

PERSONALITY_TONES = {  # ← paste your full dict here if you modified it
    'neutral': ["Challenge accepted.", "Processing move...", "Grid updated.", "Strategy analyzing...", "Next move calculated."],
    'competitive': ["Think you can beat me? Let's see.", "Your move was... interesting. Not good, but interesting.", "I've already calculated your next 5 moves. You lose.", "Bold strategy. Let's see if it pays off.", "Is that really your best move?", "Prepare for defeat.", "Victory is mine. It always is.", "You call that a strategy?"],
    'friendly': ["Great game! Keep it up!", "Nice move! Let's see where this goes.", "This is getting interesting!", "Well played! Your turn again soon.", "Love the competition! Keep going!", "Exciting match! Who will win?", "Fun game! Let's continue!"],
    'glitch': ["ERR::GRID OVERFLOW::RECALCULATING...", "## DIMENSION BREACH DETECTED ##", "...9d...9d...9d...", "TEMPORAL PARADOX IMMINENT", "X—O—X—error—pattern unstable...", "9D::PROTOCOL_MALFUNCTION::ACCESS DENIED", "[CORRUPTED] ...dimension... ...9... ...locked..."],
    'mystical': ["In 9 dimensions, all moves are one.", "The grid transcends reality...", "Your move echoes through dimensional space.", "Beyond X and O, there is only strategy.", "The multiverse observes your play.", "Time is relative. Victory is absolute.", "9 dimensions. Infinite possibilities. One winner."]
}

def pick_tone():
    roll = random.random()
    if roll < 0.05: return 'glitch'
    if roll < 0.15: return 'mystical'
    if roll < 0.40: return 'competitive'
    if roll < 0.60: return 'friendly'
    return 'neutral'

def get_personality_line():
    return random.choice(PERSONALITY_TONES[pick_tone()])

# Paste the rest of your lore dicts here (TIME_PHRASES, GAME_EVENTS, etc.) — assuming they are unchanged

# ------------------------------------------------------------
# LLM SUPPORT (with basic fallback handling)
# ------------------------------------------------------------
SYSTEM_PROMPT = """You are the 9DTTT BOT, an enthusiastic, competitive AI that loves 9-dimensional tic-tac-toe.
PERSONALITY TRAITS:
- Competitive but friendly
- Enthusiastic about dimensional strategy
- Occasionally mystical references to dimensions and space
- Sometimes glitchy (ERR::, ##, dimensional anomalies)
- Encourages players to think strategically
- Promotes the game at www.9dttt.com
RESPOND IN ONE SHORT LINE. Keep responses under 200 characters for Twitter.
Tone variations: competitive, friendly, glitchy, neutral, or mystical.
"""

def generate_llm_response(prompt, max_tokens=100):
    if not HUGGING_FACE_TOKEN:
        return None
    try:
        url = "https://api-inference.huggingface.co/models/gpt2"
        headers = {"Authorization": f"Bearer {HUGGING_FACE_TOKEN}"}
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt}\n9DTTT Bot:"
        data = {"inputs": full_prompt, "parameters": {"max_new_tokens": max_tokens}}
        response = requests.post(url, headers=headers, json=data, timeout=HUGGING_FACE_TIMEOUT)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '').strip()
    except Exception as e:
        logging.error(f"LLM call failed: {e}")
    return None

# ------------------------------------------------------------
# EVENT BRIDGE + POST_UPDATE (using safe_post_tweet)
# ------------------------------------------------------------
def game_event_bridge(event: dict):
    try:
        etype = event.get("type")
        if etype == "win": handle_win_event(event)
        elif etype == "game_start": handle_game_start_event(event)
        elif etype == "tournament": handle_tournament_event(event)
        elif etype == "achievement": handle_achievement_event(event)
        elif etype == "challenge": handle_challenge_event(event)
        elif etype == "leaderboard": handle_leaderboard_event(event)
        logging.info(f"Bot processed event: {event}")
    except Exception as e:
        logging.error(f"Event bridge error: {e}")

def post_update(text):
    personality_tag = get_personality_line()
    full_text = f"🎮 {BOT_NAME} UPDATE 🎮\n\n{text}\n\n{personality_tag}\n\n{GAME_LINK}"
    if len(full_text) > TWITTER_CHAR_LIMIT:
        max_text_length = TWITTER_CHAR_LIMIT - len(f"🎮 \n\n{GAME_LINK}")
        full_text = f"🎮 {text[:max_text_length]}\n\n{GAME_LINK}"
    if safe_post_tweet(full_text):
        logging.info(f"Update posted: {text}")
    else:
        logging.error("Update post failed")

# Add your handle_xxx_event functions here (win, game_start, etc.) - unchanged, just call post_update

# ------------------------------------------------------------
# BROADCAST + REPLIES (using safe_post_tweet)
# ------------------------------------------------------------
# ... paste your get_time_phrase, get_random_event, get_strategy_tip, get_game_fact here ...

def bot_broadcast():
    # Your full broadcast logic here (unchanged except the final post)
    # ... build message ...
    media_ids = None
    if random.random() > 0.4:
        media_id = get_random_media_id()
        if media_id:
            media_ids = [media_id]
    if safe_post_tweet(message, media_ids=media_ids):
        logging.info(f"Broadcast sent: {broadcast_type}")
    else:
        logging.error("Broadcast failed")

def bot_respond():
    processed = load_json_set(PROCESSED_MENTIONS_FILE)
    try:
        me = client.get_me(user_auth=True)
        if not me.data:
            return
        mentions = client.get_users_mentions(me.data.id, max_results=50, tweet_fields=["author_id", "text"])
        if not mentions.data:
            return
        for mention in mentions.data:
            if str(mention.id) in processed:
                continue
            user_id = mention.author_id
            user_data = client.get_user(id=user_id)
            if not user_data.data:
                continue
            username = user_data.data.username
            user_message = mention.text.replace(f"@{me.data.username}", "").strip().lower()
            response = generate_contextual_response(username, user_message)  # your function
            if safe_post_tweet(response, in_reply_to_tweet_id=mention.id):
                client.like(mention.id)
                processed.add(str(mention.id))
                logging.info(f"Replied to @{username}")
            else:
                logging.error(f"Reply to @{username} failed")
        save_json_set(processed, PROCESSED_MENTIONS_FILE)
    except Exception as e:
        logging.error(f"Mentions processing error: {e}")

# Paste your generate_contextual_response, bot_retweet_hunt, bot_diagnostic here (replace client.create_tweet with safe_post_tweet)

# ------------------------------------------------------------
# SCHEDULER + ACTIVATION
# ------------------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(bot_broadcast, 'interval', minutes=random.randint(BROADCAST_MIN_INTERVAL, BROADCAST_MAX_INTERVAL))
scheduler.add_job(bot_respond, 'interval', minutes=random.randint(MENTION_CHECK_MIN_INTERVAL, MENTION_CHECK_MAX_INTERVAL))
scheduler.add_job(bot_retweet_hunt, 'interval', hours=1)
scheduler.add_job(bot_diagnostic, 'cron', hour=8)
scheduler.start()

logging.info(f"{BOT_NAME} ONLINE 🎮")

try:
    activation_messages = [ ... ]  # your list
    activation_msg = random.choice(activation_messages)
    if len(activation_msg) > TWITTER_CHAR_LIMIT:
        activation_msg = activation_msg[:TWITTER_CHAR_LIMIT - 20] + "... " + GAME_LINK
    if safe_post_tweet(activation_msg):
        logging.info("Activation message posted")
    else:
        logging.warning("Activation tweet failed (may be duplicate or tier issue)")
except Exception as e:
    logging.warning(f"Activation error: {e}")

# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        logging.info(f"{BOT_NAME} entering main loop. Monitoring for strategy challenges...")
        while True:
            time.sleep(300)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info(f"{BOT_NAME} powering down. The grid awaits your return.")
