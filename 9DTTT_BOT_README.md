# 9DTTT Twitter Bot

A standalone Twitter bot for promoting and engaging with players of www.9dttt.com (9-Dimensional Tic-Tac-Toe).

## Overview

This bot is designed to:
- Post automated updates about the 9D Tic-Tac-Toe game
- Respond to user mentions with strategic tips and game information
- Share game events, achievements, and leaderboard updates
- Engage with the gaming community on Twitter

## Features

- **Personality System**: Multiple tones (competitive, friendly, mystical, glitchy, neutral)
- **Automated Broadcasting**: Posts game updates every 2-4 hours
- **Mention Responses**: Replies to users who mention the bot
- **Event Integration**: Webhook endpoint for game events
- **Strategy Tips**: Shares helpful tips for playing 9D TTT
- **Achievement Tracking**: Announces player milestones
- **Retweet Functionality**: Finds and retweets relevant gaming content

## Requirements

The bot requires the following Python packages (install with `pip install -r requirements.txt`):
- `tweepy>=4.14.0` - Twitter API integration
- `apscheduler>=3.10.4` - Task scheduling
- `requests>=2.31.0` - HTTP requests
- `flask>=3.0.0` - Web server for event webhooks

## Setup Instructions

### 1. Twitter Developer Account Setup

1. Go to https://developer.twitter.com and create a developer account
2. Create a new app in the Twitter Developer Portal
3. Generate the following credentials:
   - Consumer Key (API Key)
   - Consumer Secret (API Secret)
   - Access Token
   - Access Token Secret
   - Bearer Token

### 2. Environment Variables

Set the following environment variables with your Twitter credentials:

```bash
export CONSUMER_KEY="your_consumer_key"
export CONSUMER_SECRET="your_consumer_secret"
export ACCESS_TOKEN="your_access_token"
export ACCESS_SECRET="your_access_secret"
export BEARER_TOKEN="your_bearer_token"
export HUGGING_FACE_TOKEN="your_hf_token"  # Optional for AI responses
```

Or create a `.env` file and load it with a library like `python-dotenv`.

### 3. Media Folder (Optional)

If you want the bot to post images:
1. Create a `media/` folder in the same directory as the bot
2. Add images (PNG, JPG, JPEG, GIF) or videos (MP4) to the folder
3. The bot will randomly select media to attach to some tweets

### 4. Running the Bot

```bash
python3 9dttt_bot.py
```

The bot will:
- Post an activation message to Twitter
- Start the scheduler for automated tasks
- Begin monitoring for mentions
- Run continuously until stopped

### 5. Game Event Integration (Optional)

The bot includes a Flask webhook endpoint at `/9dttt-event` that can receive game events.

**Note:** The Flask app is defined in the bot but not automatically started. You have two options:

**Option A: Run Flask separately (recommended for production)**
```bash
# Install gunicorn
pip install gunicorn

# Run the Flask app on port 5000
gunicorn -w 4 -b 0.0.0.0:5000 "9dttt_bot:app"

# Run the bot separately
python3 9dttt_bot.py
```

**Option B: Modify the bot to run Flask in a thread**
Add this code before the main loop in `9dttt_bot.py`:
```python
import threading
flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
flask_thread.daemon = True
flask_thread.start()
```

To use this feature:
1. Deploy the bot to a server with a public URL
2. Configure your game to send POST requests to `https://your-server.com/9dttt-event`

Event types supported:
- `win` - Player wins a game
- `game_start` - New game begins
- `tournament` - Tournament events
- `achievement` - Player unlocks achievement
- `challenge` - Player challenges another
- `leaderboard` - Leaderboard updates

Example event payload:
```json
{
  "type": "win",
  "player": "PlayerName",
  "dimensions": "5"
}
```

## Customization

### Adjusting Broadcast Frequency

Edit these constants in the bot file:
```python
BROADCAST_MIN_INTERVAL = 120  # minutes (2 hours)
BROADCAST_MAX_INTERVAL = 240  # minutes (4 hours)
MENTION_CHECK_MIN_INTERVAL = 15  # minutes
MENTION_CHECK_MAX_INTERVAL = 30  # minutes
```

### Modifying Personality

The bot has multiple personality tones defined in `PERSONALITY_TONES`. You can:
- Add new personality types
- Modify existing messages
- Adjust tone probabilities in the `pick_tone()` function

### Customizing Content

Edit these lists to change bot content:
- `GAME_EVENTS` - Game-related events
- `STRATEGY_TIPS` - Strategy advice
- `GAME_FACTS` - Interesting facts about the game
- `MOTIVATIONAL` - Motivational messages
- `PLAYER_ACHIEVEMENTS` - Achievement descriptions

## File Structure

```
9dttt_bot.py                    # Main bot file
9DTTT_BOT_README.md            # This file
9dttt_processed_mentions.json  # Tracks processed mentions (auto-generated)
9dttt_bot.log                  # Log file (auto-generated)
media/                         # Optional folder for images/videos
```

## Logging

The bot creates a log file `9dttt_bot.log` that tracks:
- Bot initialization
- Tweet posts and responses
- Errors and exceptions
- Event processing

## Deployment Options

### Local Development
```bash
python3 9dttt_bot.py
```

### Linux Server (with systemd)
Create a systemd service file:
```ini
[Unit]
Description=9DTTT Twitter Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/bot
Environment="CONSUMER_KEY=..."
Environment="CONSUMER_SECRET=..."
Environment="ACCESS_TOKEN=..."
Environment="ACCESS_SECRET=..."
Environment="BEARER_TOKEN=..."
ExecStart=/usr/bin/python3 9dttt_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Cloud Platforms
The bot can be deployed to:
- Heroku
- Railway
- Render
- DigitalOcean
- AWS EC2
- Google Cloud
- Any platform that supports Python applications

## Troubleshooting

### Bot doesn't post tweets
- Check Twitter API credentials
- Verify rate limits haven't been exceeded
- Check `9dttt_bot.log` for errors

### Mentions not being replied to
- Ensure the bot account has proper permissions
- Check that mention detection is working in logs
- Verify Twitter API v2 access

### Import errors
- Install all requirements: `pip install -r requirements.txt`
- Use Python 3.8 or higher

## Support

For issues with:
- The bot code: Check the logs and error messages
- Twitter API: Visit https://developer.twitter.com/docs
- The 9DTTT game: Visit www.9dttt.com

## License

This bot is provided as-is for promoting www.9dttt.com. Modify as needed for your use case.

## Notes

- This is a standalone bot that can be dropped into any repository
- It's independent of the atomicfizzcaps.xyz bot in this repo
- All configuration is done through environment variables
- No database required - uses simple JSON file for tracking
- Minimal dependencies for easy deployment
