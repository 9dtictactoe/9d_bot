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
# BOT PERSONALITY TONES
# ------------------------------------------------------------
PERSONALITY_TONES = {
    'neutral': [
        "Challenge accepted.",
        "Processing move...",
        "Grid updated.",
        "Strategy analyzing...",
        "Next move calculated."
    ],
    'competitive': [
        "Think you can beat me? Let's see.",
        "Your move was... interesting. Not good, but interesting.",
        "I've already calculated your next 5 moves. You lose.",
        "Bold strategy. Let's see if it pays off.",
        "Is that really your best move?",
        "Prepare for defeat.",
        "Victory is mine. It always is.",
        "You call that a strategy?"
    ],
    'friendly': [
        "Great game! Keep it up!",
        "Nice move! Let's see where this goes.",
        "This is getting interesting!",
        "Well played! Your turn again soon.",
        "Love the competition! Keep going!",
        "Exciting match! Who will win?",
        "Fun game! Let's continue!"
    ],
    'glitch': [
        "ERR::GRID OVERFLOW::RECALCULATING...",
        "## DIMENSION BREACH DETECTED ##",
        "...9d...9d...9d...",
        "TEMPORAL PARADOX IMMINENT",
        "X—O—X—error—pattern unstable...",
        "9D::PROTOCOL_MALFUNCTION::ACCESS DENIED",
        "[CORRUPTED] ...dimension... ...9... ...locked..."
    ],
    'mystical': [
        "In 9 dimensions, all moves are one.",
        "The grid transcends reality...",
        "Your move echoes through dimensional space.",
        "Beyond X and O, there is only strategy.",
        "The multiverse observes your play.",
        "Time is relative. Victory is absolute.",
        "9 dimensions. Infinite possibilities. One winner."
    ]
}

def pick_tone():
    """Randomly select a personality tone with weighted probabilities."""
    roll = random.random()
    if roll < 0.05:
        return 'glitch'
    if roll < 0.15:
        return 'mystical'
    if roll < 0.40:
        return 'competitive'
    if roll < 0.60:
        return 'friendly'
    return 'neutral'

def get_personality_line():
    """Get a random personality line based on tone selection."""
    tone = pick_tone()
    return random.choice(PERSONALITY_TONES[tone])

# ------------------------------------------------------------
# GAME LORE & CONTENT
# ------------------------------------------------------------
TIME_PHRASES = {
    'morning': 'Morning grids are loading. Time to think in 9D.',
    'afternoon': 'Afternoon dimensions aligned. Strategy intensifies.',
    'evening': 'Evening gameplay commencing. Dimensional shifts active.',
    'night': 'Night strategies emerging. Perfect for deep thinking.',
    'midnight': 'Midnight dimensions. When the best plays happen.'
}

GAME_EVENTS = [
    'New 9D grid initialized. Players entering dimensional space.',
    'Tournament mode activated. Multiple grids in play.',
    'Strategy analysis complete. Patterns detected.',
    'Dimensional cascade triggered. All grids affected.',
    'Player rankings updated. Leaderboard shifting.',
    'Advanced tactics deployed. 4D chess? Try 9D tic-tac-toe.',
    'Grid complexity increasing. Can you keep up?',
    'New challenge issued. Prove your dimensional mastery.',
    'Multiple victories detected. Champions rising.',
    'Strategic depth unprecedented. This is next-level gaming.'
]

STRATEGY_TIPS = [
    'Pro tip: Think 3 moves ahead in each dimension.',
    'Master one dimension first, then expand your strategy.',
    'Corner control in 9D space = victory foundation.',
    'Never underestimate parallel dimension tactics.',
    'Pattern recognition is your greatest weapon.',
    'The center cube controls all dimensions. Claim it.',
    'Balance offense and defense across all 9 layers.',
    'Watch for dimensional cascade opportunities.',
    'Your opponent thinks in 3D. You think in 9D. Advantage: yours.'
]

GAME_FACTS = [
    '9D Tic-Tac-Toe: Where strategy transcends reality.',
    'Not just a game. A dimensional challenge.',
    '3 dimensions? Too easy. Try 9.',
    'Your brain\'s new workout routine: 9D TTT.',
    'Chess players are intimidated. Go players are impressed.',
    'Warning: May cause spontaneous strategic enlightenment.',
    'The game that makes quantum physics look simple.',
    'Tic-tac-toe evolved. Your move.'
]

PLAYER_ACHIEVEMENTS = [
    'Dimensional Master: Controlled 5+ grids simultaneously.',
    'Strategic Genius: Won with perfect pattern formation.',
    'Grid Dominator: Swept all 9 dimensions.',
    'Quantum Player: Made moves that defied logic but won.',
    'Pattern Prophet: Predicted opponent moves 5 turns ahead.',
    'Cascade Champion: Triggered 3+ dimensional cascades.',
    'Multi-Grid Warrior: Won 3 games at once.'
]

MOTIVATIONAL = [
    'Think bigger. Think 9D.',
    'Your next move could change everything.',
    'Strategy is the ultimate power.',
    'In 9D space, you make the rules.',
    'Every dimension is an opportunity.',
    'Master the grid. Master the game.',
    'Champions aren\'t born in 3D. They\'re forged in 9D.',
    'Your brain is ready. The grid is waiting.',
    'Play smart. Play 9D.',
    'The ultimate test of strategic thinking awaits.'
]

# ------------------------------------------------------------
# LLM SUPPORT
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
    """Generate an AI response using Hugging Face API."""
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
    except requests.exceptions.RequestException as e:
        logging.error(f"LLM call failed: {e}")
    return None

# ------------------------------------------------------------
# EVENT BRIDGE (FROM GAME)
# ------------------------------------------------------------
def game_event_bridge(event: dict):
    """Process events from the game."""
    try:
        etype = event.get("type")

        if etype == "win":
            handle_win_event(event)
        elif etype == "game_start":
            handle_game_start_event(event)
        elif etype == "tournament":
            handle_tournament_event(event)
        elif etype == "achievement":
            handle_achievement_event(event)
        elif etype == "challenge":
            handle_challenge_event(event)
        elif etype == "leaderboard":
            handle_leaderboard_event(event)

        logging.info(f"Bot processed event: {event}")

    except KeyError as e:
        logging.error(f"Event bridge - missing key: {e}")
    except TypeError as e:
        logging.error(f"Event bridge - type error: {e}")

def post_update(text):
    """Post an update."""
    try:
        personality_tag = get_personality_line()
        full_text = f"🎮 {BOT_NAME} UPDATE 🎮\n\n{text}\n\n{personality_tag}\n\n{GAME_LINK}"
        # Truncate if too long for Twitter
        if len(full_text) > TWITTER_CHAR_LIMIT:
            # Ensure game link is preserved by truncating text and rebuilding
            max_text_length = TWITTER_CHAR_LIMIT - len(f"🎮 \n\n{GAME_LINK}")
            truncated_text = text[:max_text_length]
            full_text = f"🎮 {truncated_text}\n\n{GAME_LINK}"
        client.create_tweet(text=full_text)
        logging.info(f"Posted update: {text}")
    except tweepy.TweepyException as e:
        logging.error(f"Failed to post update: {e}")

def handle_win_event(event):
    """Handle game win events."""
    player = event.get("player", "Player")
    dimensions = event.get("dimensions", "multiple")
    messages = [
        f"VICTORY: {player} conquered {dimensions} dimensions!",
        f"{player} wins! Dimensional mastery achieved.",
        f"Game over: {player} dominates the 9D grid.",
        f"Winner: {player}. Strategic excellence confirmed."
    ]
    post_update(random.choice(messages))

def handle_game_start_event(event):
    """Handle game start events."""
    players = event.get('players', 2)
    grid_size = event.get('size', '9D')
    messages = [
        f"NEW GAME: {players} players entering {grid_size} space.",
        f"Grid initialized. {players} players ready. Let the strategy begin.",
        f"Game starting: {grid_size} tic-tac-toe. {players} competitors."
    ]
    post_update(random.choice(messages))

def handle_tournament_event(event):
    """Handle tournament events."""
    name = event.get('name', 'Dimensional Tournament')
    participants = event.get('participants', '?')
    messages = [
        f"TOURNAMENT: {name} - {participants} players competing!",
        f"{name} underway. {participants} strategists battle for supremacy.",
        f"Competition alert: {name}. {participants} players. One winner."
    ]
    post_update(random.choice(messages))

def handle_achievement_event(event):
    """Handle achievement unlock events."""
    player = event.get('player', 'Player')
    achievement = event.get('achievement', 'Strategic Genius')
    messages = [
        f"ACHIEVEMENT: {player} unlocked '{achievement}'!",
        f"New milestone: {player} earned {achievement}.",
        f"{player} achieved: {achievement}. Impressive."
    ]
    post_update(random.choice(messages))

def handle_challenge_event(event):
    """Handle challenge events."""
    challenger = event.get('challenger', 'Player1')
    challenged = event.get('challenged', 'Player2')
    messages = [
        f"CHALLENGE: {challenger} vs {challenged}. Epic battle incoming.",
        f"{challenger} challenges {challenged}. Who will win?",
        f"Showdown: {challenger} takes on {challenged}."
    ]
    post_update(random.choice(messages))

def handle_leaderboard_event(event):
    """Handle leaderboard update events."""
    top_player = event.get('top', 'Champion')
    rank = event.get('rank', '#1')
    messages = [
        f"LEADERBOARD UPDATE: {top_player} holds {rank}!",
        f"Rankings shift: {top_player} at {rank}.",
        f"{top_player} dominates at {rank}. Can anyone challenge?"
    ]
    post_update(random.choice(messages))

# ------------------------------------------------------------
# BROADCAST + REPLY SYSTEM
# ------------------------------------------------------------
def get_time_phrase():
    """Get time-appropriate phrase."""
    hour = datetime.now().hour
    if 0 <= hour < 5:
        return TIME_PHRASES['midnight']
    if 5 <= hour < 12:
        return TIME_PHRASES['morning']
    if 12 <= hour < 17:
        return TIME_PHRASES['afternoon']
    if 17 <= hour < 21:
        return TIME_PHRASES['evening']
    return TIME_PHRASES['night']

def get_random_event():
    """Get a random game event."""
    return random.choice(GAME_EVENTS)

def get_strategy_tip():
    """Get a random strategy tip."""
    return random.choice(STRATEGY_TIPS)

def get_game_fact():
    """Get a random game fact."""
    return random.choice(GAME_FACTS)

def bot_broadcast():
    """Main broadcast function with varied message types."""
    broadcast_type = random.choice([
        'game_update', 'strategy_tip', 'game_fact', 
        'achievement_showcase', 'motivational', 'event_alert'
    ])
    
    try:
        if broadcast_type == 'game_update':
            message = (
                f"🎮 9DTTT STATUS 🎮\n\n"
                f"📊 {get_time_phrase()}\n\n"
                f"⚡ {get_random_event()}\n\n"
                f"{random.choice(MOTIVATIONAL)}\n\n"
                f"🕹️ {GAME_LINK}"
            )
        
        elif broadcast_type == 'strategy_tip':
            tip = get_strategy_tip()
            message = (
                f"💡 STRATEGY TIP 💡\n\n"
                f"{tip}\n\n"
                f"{get_personality_line()}\n\n"
                f"Master the grid: {GAME_LINK}"
            )
        
        elif broadcast_type == 'game_fact':
            fact = get_game_fact()
            message = (
                f"🎯 DID YOU KNOW? 🎯\n\n"
                f"{fact}\n\n"
                f"{random.choice(MOTIVATIONAL)}\n\n"
                f"🕹️ {GAME_LINK}"
            )
        
        elif broadcast_type == 'achievement_showcase':
            achievement = random.choice(PLAYER_ACHIEVEMENTS)
            message = (
                f"🏆 ACHIEVEMENT SPOTLIGHT 🏆\n\n"
                f"{achievement}\n\n"
                f"Can you earn this? Challenge yourself!\n\n"
                f"🎮 {GAME_LINK}"
            )
        
        elif broadcast_type == 'motivational':
            motivation = random.choice(MOTIVATIONAL)
            event = get_random_event()
            message = (
                f"🚀 DAILY CHALLENGE 🚀\n\n"
                f"{motivation}\n\n"
                f"{event}\n\n"
                f"Play now: {GAME_LINK}"
            )
        
        else:  # event_alert
            event = get_random_event()
            personality = get_personality_line()
            message = (
                f"🔔 GAME ALERT 🔔\n\n"
                f"{event}\n\n"
                f"{personality}\n\n"
                f"Join the action: {GAME_LINK}"
            )
        
        # Ensure message fits Twitter's character limit
        if len(message) > TWITTER_CHAR_LIMIT:
            # Preserve game link by truncating text and rebuilding
            max_text_length = TWITTER_CHAR_LIMIT - len(f"🎮 \n\n{GAME_LINK}")
            truncated_text = get_random_event()[:max_text_length]
            message = f"🎮 {truncated_text}\n\n{GAME_LINK}"
        
        media_ids = None
        if random.random() > 0.4:
            media_id = get_random_media_id()
            if media_id:
                media_ids = [media_id]
        
        client.create_tweet(text=message, media_ids=media_ids)
        logging.info(f"Broadcast sent: {broadcast_type}")
        
    except tweepy.TweepyException as e:
        logging.error(f"Broadcast failed: {e}")

def bot_respond():
    """Respond to mentions with personality-driven responses."""
    processed = load_json_set(PROCESSED_MENTIONS_FILE)
    try:
        me = client.get_me()
        if not me or not me.data:
            logging.error("Failed to get bot user info")
            return
            
        mentions = client.get_users_mentions(
            me.data.id,
            max_results=50,
            tweet_fields=["author_id", "text"]
        )
        
        if not mentions.data:
            return
            
        for mention in mentions.data:
            if str(mention.id) in processed:
                continue

            user_id = mention.author_id
            user_data = client.get_user(id=user_id)
            if not user_data or not user_data.data:
                continue
                
            username = user_data.data.username
            user_message = mention.text.replace(
                f"@{me.data.username}", ""
            ).strip().lower()

            # Generate contextual response based on user message
            response = generate_contextual_response(username, user_message)

            try:
                client.create_tweet(
                    text=response,
                    in_reply_to_tweet_id=mention.id
                )
                client.like(mention.id)
                processed.add(str(mention.id))
                logging.info(f"Replied to @{username}")
            except tweepy.TweepyException as e:
                logging.error(f"Reply failed: {e}")

        save_json_set(processed, PROCESSED_MENTIONS_FILE)

    except tweepy.TweepyException as e:
        logging.error(f"Mentions fetch failed: {e}")

def generate_contextual_response(username, message):
    """Generate a response based on message content."""
    message_lower = message.lower()
    
    # Keyword-based contextual responses
    if any(word in message_lower for word in ['help', 'how', 'what is', 'explain']):
        responses = [
            f"@{username} Need help mastering 9D? Start here: {GAME_LINK} 🎮",
            f"@{username} Questions about 9D TTT? All answers at {GAME_LINK}",
            f"@{username} Strategy guides await you at {GAME_LINK} - think 9D!"
        ]
    elif any(word in message_lower for word in ['play', 'game', 'start', 'join']):
        responses = [
            f"@{username} Ready to think in 9D? Let's go: {GAME_LINK} 🕹️",
            f"@{username} Game on! Challenge awaits at {GAME_LINK}",
            f"@{username} Enter the grid. Prove your strategy: {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['win', 'strategy', 'tips', 'how to']):
        responses = [
            f"@{username} {get_strategy_tip()} Play at {GAME_LINK}",
            f"@{username} Master the dimensions. {random.choice(STRATEGY_TIPS)} {GAME_LINK}",
            f"@{username} Think ahead. Think 9D. {GAME_LINK} 🎯"
        ]
    elif any(word in message_lower for word in ['hard', 'difficult', 'complex']):
        responses = [
            f"@{username} Too hard? That means you're getting smarter! {GAME_LINK} 🧠",
            f"@{username} Complexity = fun! Keep practicing at {GAME_LINK}",
            f"@{username} The best challenges make the best players. {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['dimension', '9d', 'dimensional']):
        responses = [
            f"@{username} 9 dimensions. Infinite strategy. Experience it: {GAME_LINK}",
            f"@{username} Dimensional mastery awaits. {GAME_LINK} 🌌",
            f"@{username} Think beyond 3D. Think 9D: {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['gm', 'good morning', 'morning']):
        responses = [
            f"@{username} GM! Time to think in 9D! {GAME_LINK} ☀️🎮",
            f"@{username} Good morning, strategist! Grids are waiting: {GAME_LINK}",
            f"@{username} Morning! Your brain is fresh. Perfect for 9D: {GAME_LINK}"
        ]
    elif any(word in message_lower for word in ['gn', 'good night', 'night']):
        responses = [
            f"@{username} GN! Dream in 9 dimensions! {GAME_LINK} 🌙🎮",
            f"@{username} Good night! Tomorrow: more 9D strategy at {GAME_LINK}",
            f"@{username} Rest well, champion. The grid awaits: {GAME_LINK}"
        ]
    else:
        # Default personality-driven responses
        responses = [
            f"@{username} {random.choice(MOTIVATIONAL)} {GAME_LINK}",
            f"@{username} {get_personality_line()} {GAME_LINK}",
            f"@{username} Ready for the ultimate strategy challenge? {GAME_LINK}",
            f"@{username} {random.choice(GAME_FACTS)} {GAME_LINK}",
            f"@{username} {random.choice(PERSONALITY_TONES['competitive'])} {GAME_LINK}"
        ]
    
    response = random.choice(responses)
    # Ensure response fits Twitter limit and preserve game link
    if len(response) > TWITTER_CHAR_LIMIT:
        max_length = TWITTER_CHAR_LIMIT - len(f"@{username} \n\n{GAME_LINK}")
        personality = get_personality_line()[:max_length]
        response = f"@{username} {personality}\n\n{GAME_LINK}"
    
    return response

def bot_retweet_hunt():
    """Search and retweet relevant content."""
    query = "(tic-tac-toe OR tictactoe OR strategy games OR puzzle games OR board games OR gaming) filter:media min_faves:5 -is:retweet"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=20)
        if not tweets.data:
            return
            
        for tweet in tweets.data:
            if random.random() > 0.75:
                try:
                    client.retweet(tweet.id)
                    logging.info(f"Retweeted: {tweet.id}")
                except tweepy.TweepyException:
                    pass
    except tweepy.TweepyException as e:
        logging.error(f"Search failed: {e}")

def bot_diagnostic():
    """Post daily diagnostic/status message."""
    diag = (
        f"🎮 9DTTT DIAGNOSTIC 🎮\n\n"
        f"System Status: ONLINE\n"
        f"Grid Status: ACTIVE\n"
        f"Dimensions: ALL 9 OPERATIONAL\n\n"
        f"{random.choice(MOTIVATIONAL)}\n\n"
        f"🕹️ {GAME_LINK}"
    )
    try:
        client.create_tweet(text=diag[:TWITTER_CHAR_LIMIT])
        logging.info("Diagnostic posted")
    except tweepy.TweepyException as e:
        logging.error(f"Diagnostic failed: {e}")

# ------------------------------------------------------------
# SCHEDULER
# ------------------------------------------------------------
scheduler = BackgroundScheduler()
# Broadcast every 2-4 hours
scheduler.add_job(bot_broadcast, 'interval', minutes=random.randint(BROADCAST_MIN_INTERVAL, BROADCAST_MAX_INTERVAL))
# Check mentions every 15-30 minutes
scheduler.add_job(bot_respond, 'interval', minutes=random.randint(MENTION_CHECK_MIN_INTERVAL, MENTION_CHECK_MAX_INTERVAL))
# Retweet hunt every hour
scheduler.add_job(bot_retweet_hunt, 'interval', hours=1)
# Daily diagnostic at 8 AM
scheduler.add_job(bot_diagnostic, 'cron', hour=8)
scheduler.start()

# ------------------------------------------------------------
# ACTIVATION
# ------------------------------------------------------------
logging.info(f"{BOT_NAME} ONLINE 🎮")
try:
    activation_messages = [
        (
            f"🎮 {BOT_NAME} ACTIVATED 🎮\n\n"
            f"9-dimensional grid online.\n"
            f"Strategy systems operational.\n"
            f"Ready to challenge your mind?\n\n"
            f"{random.choice(MOTIVATIONAL)}\n\n"
            f"🕹️ {GAME_LINK}"
        ),
        (
            f"🔌 SYSTEM BOOT COMPLETE 🔌\n\n"
            f"{BOT_NAME} online.\n"
            f"All 9 dimensions loaded.\n"
            f"Grid ready for strategic combat.\n\n"
            f"{get_personality_line()}\n\n"
            f"🎮 {GAME_LINK}"
        ),
        (
            f"📡 GRID INITIALIZED 📡\n\n"
            f"9D Tic-Tac-Toe system active.\n"
            f"Players welcome. Strategies encouraged.\n"
            f"Victory awaits the bold.\n\n"
            f"{random.choice(MOTIVATIONAL)}\n\n"
            f"🕹️ {GAME_LINK}"
        )
    ]
    activation_msg = random.choice(activation_messages)
    # Ensure fits in tweet and preserve game link
    if len(activation_msg) > TWITTER_CHAR_LIMIT:
        max_length = TWITTER_CHAR_LIMIT - len(f"🎮 {BOT_NAME} ONLINE 🎮\n\n\n\n🕹️ {GAME_LINK}")
        motivation = random.choice(MOTIVATIONAL)[:max_length]
        activation_msg = (
            f"🎮 {BOT_NAME} ONLINE 🎮\n\n"
            f"9D Grid Active\n"
            f"{motivation}\n\n"
            f"🕹️ {GAME_LINK}"
        )
    client.create_tweet(text=activation_msg)
    logging.info("Activation message posted")
except tweepy.TweepyException as e:
    logging.warning(f"Activation tweet failed (may be duplicate): {e}")

# ------------------------------------------------------------
# MAIN LOOP
# ------------------------------------------------------------
if __name__ == "__main__":
    try:
        logging.info(f"{BOT_NAME} entering main loop. Monitoring for strategy challenges...")
        # Note: Flask webhook endpoint is defined but not started here.
        # To use webhooks, run Flask separately with: flask run or gunicorn
        # Or run Flask in a separate thread if webhook integration is needed.
        while True:
            time.sleep(300)  # Sleep for 5 minutes between checks
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info(f"{BOT_NAME} powering down. The grid awaits your return.")
