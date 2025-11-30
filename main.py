import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, JobQueue
from flask import Flask
import threading
import re
import pytz

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8551726061:AAGawAjRX4wBjM8w6dHXfrJxVlUrWJU5EK4")
LAGOS_TZ = pytz.timezone('Africa/Lagos')

# Bot Identity
BOT_NAME = "🌟 EliteRank Bot"
BOT_EMOJI = "🌟"

# Admin Twitter links
ADMIN_TWITTER_LINKS = [
    "https://x.com/Kingcharlesd1st",
    "https://x.com/Chichiweb3_", 
    "https://x.com/g_amayaka"
]

# Train schedule for Lagos time
TRAIN_SCHEDULE = [
    {"hour": 10, "minute": 0, "name": "🌅 Morning Train"},
    {"hour": 14, "minute": 0, "name": "🌞 Afternoon Train"},
    {"hour": 18, "minute": 0, "name": "🌇 Evening Train"},
    {"hour": 22, "minute": 0, "name": "🌙 Night Train"}
]

# Chat IDs
GROUP_CHAT_ID = -1003348024403
CHANNEL_CHAT_ID = -1002144249593

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return f"""
    <html>
        <head>
            <title>{BOT_NAME}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }}
                .container {{ 
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 15px;
                    backdrop-filter: blur(10px);
                    max-width: 600px;
                    margin: 0 auto;
                }}
                h1 {{ 
                    color: #FFD700; 
                    font-size: 2.5em;
                    margin-bottom: 20px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }}
                .status {{
                    background: rgba(255, 215, 0, 0.2);
                    padding: 15px;
                    border-radius: 10px;
                    margin: 10px 0;
                    border: 1px solid rgba(255,215,0,0.3);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{BOT_EMOJI} {BOT_NAME}</h1>
                <div class="status">
                    <p>✅ Bot is running on Render.com</p>
                    <p>🚀 Status: Online 24/7</p>
                    <p>🌍 Region: Global (Works in Nigeria)</p>
                    <p>⏰ Lagos Time: {datetime.now(LAGOS_TZ).strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>⚡ Free Forever - No Credit Card Required</p>
                </div>
                <p>Your EliteRank Bot is successfully deployed and running 24/7!</p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return "✅ Healthy - " + datetime.now(LAGOS_TZ).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/ping')
def ping():
    return "🏓 PONG - " + datetime.now(LAGOS_TZ).strftime('%H:%M:%S')

@app.route('/keepalive')
def keepalive():
    return "🔒 Keep Alive Active"

# Database setup
def init_db():
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            twitter_handle TEXT,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            daily_xp INTEGER DEFAULT 0,
            comment_xp INTEGER DEFAULT 0,
            proof_xp INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_streak_date DATE,
            last_active TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Train participants
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS train_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            train_date DATE,
            train_time TEXT,
            twitter_handle TEXT,
            liked BOOLEAN DEFAULT FALSE,
            commented BOOLEAN DEFAULT FALSE,
            retweeted BOOLEAN DEFAULT FALSE,
            verified BOOLEAN DEFAULT FALSE,
            participated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Daily XP
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_xp (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            xp_earned INTEGER DEFAULT 0,
            trains_joined INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized!")

init_db()

# Database functions
def get_user(user_id):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'user_id': user[0], 'username': user[1], 'first_name': user[2],
            'twitter_handle': user[3], 'xp': user[4], 'level': user[5],
            'daily_xp': user[6], 'comment_xp': user[7], 'proof_xp': user[8],
            'streak_count': user[9], 'last_streak_date': user[10],
            'last_active': user[11], 'created_at': user[12]
        }
    return None

def create_user(user_id, username, first_name):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users 
        (user_id, username, first_name, xp, level, last_active) 
        VALUES (?, ?, ?, 0, 1, ?)
    ''', (user_id, username, first_name, datetime.now()))
    conn.commit()
    conn.close()

def update_twitter_handle(user_id, twitter_handle):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET twitter_handle = ?, last_active = ? WHERE user_id = ?',
                  (twitter_handle, datetime.now(), user_id))
    conn.commit()
    conn.close()

def update_xp(user_id, xp_to_add, xp_type="general"):
    user = get_user(user_id)
    if not user: 
        return 0
    
    new_xp = user['xp'] + xp_to_add
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    
    today = datetime.now(LAGOS_TZ).date()
    cursor.execute('''
        INSERT OR REPLACE INTO daily_xp (user_id, date, xp_earned)
        VALUES (?, ?, COALESCE((SELECT xp_earned FROM daily_xp WHERE user_id = ? AND date = ?), 0) + ?)
    ''', (user_id, today, user_id, today, xp_to_add))
    
    if xp_type == "proof":
        cursor.execute('UPDATE users SET xp = ?, proof_xp = proof_xp + ?, last_active = ? WHERE user_id = ?',
                      (new_xp, xp_to_add, datetime.now(), user_id))
    else:
        cursor.execute('UPDATE users SET xp = ?, last_active = ? WHERE user_id = ?',
                      (new_xp, datetime.now(), user_id))
    
    conn.commit()
    conn.close()
    return new_xp

def record_train_participation(user_id, twitter_handle, train_time):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    today = datetime.now(LAGOS_TZ).date()
    
    # Check if already participated
    cursor.execute('SELECT * FROM train_participants WHERE user_id = ? AND train_date = ? AND train_time = ?',
                  (user_id, today, train_time))
    
    if cursor.fetchone():
        conn.close()
        return False
    
    # Record participation
    cursor.execute('INSERT INTO train_participants (user_id, train_date, train_time, twitter_handle) VALUES (?, ?, ?, ?)',
                  (user_id, today, train_time, twitter_handle))
    
    # Update streak
    user = get_user(user_id)
    yesterday = (datetime.now(LAGOS_TZ) - timedelta(days=1)).date()
    
    if user['last_streak_date'] == str(yesterday):
        new_streak = user['streak_count'] + 1
    elif user['last_streak_date'] == str(today):
        new_streak = user['streak_count']
    else:
        new_streak = 1
    
    cursor.execute('UPDATE users SET streak_count = ?, last_streak_date = ? WHERE user_id = ?',
                  (new_streak, today, user_id))
    
    # Update daily train count
    cursor.execute('UPDATE daily_xp SET trains_joined = trains_joined + 1 WHERE user_id = ? AND date = ?',
                  (user_id, today))
    
    conn.commit()
    conn.close()
    return True

def has_participated_in_train(user_id, train_time):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    today = datetime.now(LAGOS_TZ).date()
    cursor.execute('SELECT * FROM train_participants WHERE user_id = ? AND train_date = ? AND train_time = ?',
                  (user_id, today, train_time))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def get_current_train_time():
    now = datetime.now(LAGOS_TZ)
    current_hour = now.hour
    
    for train in TRAIN_SCHEDULE:
        if train["hour"] == current_hour:
            return train["name"]
    return "🌅 Morning Train"

def update_engagement_verification(user_id, train_time, action):
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    today = datetime.now(LAGOS_TZ).date()
    
    if action == "like":
        cursor.execute('UPDATE train_participants SET liked = TRUE WHERE user_id = ? AND train_date = ? AND train_time = ?',
                      (user_id, today, train_time))
    elif action == "comment":
        cursor.execute('UPDATE train_participants SET commented = TRUE WHERE user_id = ? AND train_date = ? AND train_time = ?',
                      (user_id, today, train_time))
    elif action == "retweet":
        cursor.execute('UPDATE train_participants SET retweeted = TRUE WHERE user_id = ? AND train_date = ? AND train_time = ?',
                      (user_id, today, train_time))
    
    # Check if all engagements are complete
    cursor.execute('SELECT liked, commented, retweeted FROM train_participants WHERE user_id = ? AND train_date = ? AND train_time = ?',
                  (user_id, today, train_time))
    
    result = cursor.fetchone()
    if result and all(result):
        cursor.execute('UPDATE train_participants SET verified = TRUE WHERE user_id = ? AND train_date = ? AND train_time = ?',
                      (user_id, today, train_time))
        update_xp(user_id, 10, "proof")
    
    conn.commit()
    conn.close()

def get_daily_leaderboard():
    conn = sqlite3.connect('xp_bot.db')
    cursor = conn.cursor()
    today = datetime.now(LAGOS_TZ).date()
    
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.twitter_handle, dx.xp_earned, dx.trains_joined
        FROM daily_xp dx
        JOIN users u ON dx.user_id = u.user_id
        WHERE dx.date = ?
        ORDER BY dx.xp_earned DESC
        LIMIT 10
    ''', (today,))
    
    results = cursor.fetchall()
    conn.close()
    return results

# Bot commands
async def start(update: Update, context):
    user = update.effective_user
    create_user(user.id, user.username, user.first_name)
    user_data = get_user(user.id)
    
    twitter_status = "✅" if user_data.get('twitter_handle') else "❌"
    
    welcome_text = f"""
{BOT_EMOJI} **Welcome to {BOT_NAME}!** 

🎯 **Private Group Ranking System - Lagos Time (UTC+1)**

🐦 **Twitter Status**: {twitter_status} {'Linked: @' + user_data['twitter_handle'] if user_data.get('twitter_handle') else 'NOT LINKED - REQUIRED'}

🚂 **Automated Daily Trains (Lagos Time):**
⏰ 10:00 AM - 🌅 Morning Train
⏰ 2:00 PM - 🌞 Afternoon Train  
⏰ 6:00 PM - 🌇 Evening Train
⏰ 10:00 PM - 🌙 Night Train

📊 **Daily Leaderboards:**
🏆 Top 10 performers posted daily at 11:30 PM
📈 Real-time XP tracking
🎯 Compete with group members

🔒 **Engagement Verification System:**
After joining a train with `/joindaily`, verify your actions:
• `/verify like` - After liking admin posts
• `/verify comment` - After commenting
• `/verify retweet` - After retweeting
• Complete all 3 for +10 XP bonus!

🎮 **How to Participate:**
1. Link Twitter: `/linktwitter YOUR_HANDLE`
2. Join trains when announced
3. Engage with admin Twitter posts
4. Verify your engagement actions
5. Earn XP and climb ranks

⚡ **Status**: Auto-Trains Active • Lagos Time • Private Group
    """
    
    await update.message.reply_text(welcome_text)

async def linktwitter_cmd(update: Update, context):
    user = update.effective_user
    create_user(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            f"🚨 **TWITTER LINKING REQUIRED**\n\n"
            f"{BOT_EMOJI} You MUST link your Twitter account to join trains!\n\n"
            "🔗 **Command**: `/linktwitter YOUR_HANDLE`\n\n"
            "📝 **Examples:**\n"
            "• `/linktwitter elonmusk`\n"
            "• `/linktwitter @elonmusk`\n\n"
            "⚠️ **Required for train participation and leaderboards!**"
        )
        return
    
    twitter_handle = context.args[0].strip()
    clean_handle = twitter_handle.lstrip('@')
    
    if not re.match(r'^[A-Za-z0-9_]{1,15}$', clean_handle):
        await update.message.reply_text(
            f"❌ **Invalid Twitter Handle**\n\n"
            "✅ **Valid formats:**\n"
            "• `elonmusk`\n"
            "• `@elonmusk`\n"
            "• `john_doe123`\n\n"
            "Please try again with a valid handle!"
        )
        return
    
    update_twitter_handle(user.id, clean_handle)
    
    await update.message.reply_text(
        f"✅ **TWITTER ACCOUNT CONNECTED!** 🎉\n\n"
        f"👤 **Your Twitter**: @{clean_handle}\n"
        f"🔗 **Profile**: https://x.com/{clean_handle}\n\n"
        f"🎯 **Now You Can:**\n"
        f"• Join automated daily trains\n"
        f"• Appear on leaderboards\n"
        f"• Earn XP and level up\n"
        f"• Compete with group members\n\n"
        f"**Next Train Schedule:**\n"
        f"⏰ 10AM, 2PM, 6PM, 10PM Daily\n\n"
        f"Wait for train announcements!"
    )

async def myxp(update: Update, context):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        create_user(user.id, user.username, user.first_name)
        user_data = get_user(user.id)
    
    if not user_data.get('twitter_handle'):
        await update.message.reply_text(
            f"🚨 **TWITTER ACCOUNT REQUIRED**\n\n"
            f"You must link your Twitter account to view your stats!\n\n"
            f"Use: `/linktwitter YOUR_HANDLE`"
        )
        return
    
    level = (user_data['xp'] // 100) + 1
    next_level_xp = level * 100 - user_data['xp']
    
    xp_text = f"""
{BOT_EMOJI} **Your EliteRank Profile**

🐦 **Twitter**: @{user_data['twitter_handle']} ✅

📊 **Ranking Progress:**
⭐ **Level**: {level}
💎 **Total XP**: {user_data['xp']}
📈 **Next Level**: {next_level_xp} XP needed

🎯 **XP Breakdown:**
💬 Engagement XP: {user_data['comment_xp']}
🚂 Train XP: {user_data['proof_xp']}
🌟 Bonus XP: {user_data['daily_xp']}

🔥 **Current Streak**: {user_data['streak_count']} days

💫 **Participate in daily trains to earn more XP!**
    """
    
    await update.message.reply_text(xp_text)

async def leaderboard(update: Update, context):
    users = []
    try:
        conn = sqlite3.connect('xp_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, twitter_handle, xp, streak_count FROM users WHERE twitter_handle IS NOT NULL ORDER BY xp DESC LIMIT 10')
        users = cursor.fetchall()
        conn.close()
    except:
        pass
    
    if not users:
        await update.message.reply_text(
            f"🚨 **No Active Rankings**\n\n"
            f"Users must link Twitter accounts to appear on leaderboard!\n\n"
            f"Use `/linktwitter YOUR_HANDLE` to join rankings."
        )
        return
    
    leaderboard_text = f"🏆 **{BOT_NAME} Community Rankings** 🏆\n\n"
    
    for i, (user_id, username, first_name, twitter_handle, xp, streak_count) in enumerate(users, 1):
        name = first_name or username or f"User {user_id}"
        twitter_badge = f" 🐦@{twitter_handle}" 
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        level = (xp // 100) + 1
        level_star = "⭐" * min(level, 3)
        
        leaderboard_text += f"{medal} {name}{twitter_badge} {level_star}\n   └─ {xp} XP • 🔥{streak_count}d\n"
    
    leaderboard_text += f"\n📊 **Ranked Members**: {len(users)}"
    
    await update.message.reply_text(leaderboard_text)

async def daily_leaderboard_cmd(update: Update, context):
    daily_leaders = get_daily_leaderboard()
    
    if not daily_leaders:
        await update.message.reply_text(
            f"📊 **Daily Leaderboard**\n\n"
            f"No XP earned today yet!\n\n"
            f"Join the next train to start earning!"
        )
        return
    
    leaderboard_text = f"🏆 **Daily Leaderboard - {datetime.now(LAGOS_TZ).strftime('%Y-%m-%d')}** 🏆\n\n"
    
    for i, (user_id, username, first_name, twitter_handle, xp_earned, trains_joined) in enumerate(daily_leaders, 1):
        name = first_name or username or f"User {user_id}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        leaderboard_text += f"{medal} {name} 🐦@{twitter_handle}\n   └─ {xp_earned} XP • {trains_joined} trains\n"
    
    leaderboard_text += f"\n⏰ **Next Update**: Next train session"
    
    await update.message.reply_text(leaderboard_text)

async def joindaily_cmd(update: Update, context):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        create_user(user.id, user.username, user.first_name)
        user_data = get_user(user.id)
    
    if not user_data.get('twitter_handle'):
        await update.message.reply_text(
            f"🚨 **TWITTER ACCOUNT REQUIRED**\n\n"
            f"You must link your Twitter account to join trains!\n\n"
            f"Use: `/linktwitter YOUR_HANDLE`"
        )
        return
    
    current_train = get_current_train_time()
    
    if has_participated_in_train(user.id, current_train):
        await update.message.reply_text(
            f"✅ **Already Participated**\n\n"
            f"You've already joined {current_train}!\n\n"
            f"🎯 Wait for the next train session:\n"
            f"⏰ 10AM, 2PM, 6PM, 10PM Daily"
        )
        return
    
    # Record participation
    if record_train_participation(user.id, user_data['twitter_handle'], current_train):
        # Award XP for train participation
        new_xp = update_xp(user.id, 50, "proof")
        
        await update.message.reply_text(
            f"🎉 **TRAIN JOINED!** 🚂\n\n"
            f"✅ **{current_train} Participation Recorded**\n"
            f"👤 **User**: {user.first_name}\n"
            f"🐦 **Twitter**: @{user_data['twitter_handle']}\n"
            f"💎 **XP Earned**: +50 XP\n"
            f"🏆 **Total XP**: {new_xp}\n"
            f"🔥 **Streak**: {user_data['streak_count'] + 1} days\n\n"
            f"📢 **Required Actions:**\n"
            f"1. Like all admin Twitter posts\n"
            f"2. Comment on admin posts\n"
            f"3. Retweet admin posts\n"
            f"4. Drop your Twitter link below\n\n"
            f"🔗 **Admin Twitter Links:**\n"
            f"{chr(10).join(ADMIN_TWITTER_LINKS)}\n\n"
            f"🔁 **Engage with other members too!**"
        )
    else:
        await update.message.reply_text("❌ **Error joining train. Please try again.**")

async def verify_engagement(update: Update, context):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data or not user_data.get('twitter_handle'):
        await update.message.reply_text("❌ Link your Twitter first using /linktwitter")
        return
    
    if not context.args:
        await update.message.reply_text(
            f"🔒 **Engagement Verification**\n\n"
            f"Verify your Twitter engagement actions:\n\n"
            f"**Usage:** `/verify ACTION`\n\n"
            f"**Available Actions:**\n"
            f"• `like` - Verify liking admin posts\n"
            f"• `comment` - Verify commenting\n"
            f"• `retweet` - Verify retweeting\n\n"
            f"**Example:** `/verify like`"
        )
        return
    
    action = context.args[0].lower()
    current_train = get_current_train_time()
    
    if action in ["like", "comment", "retweet"]:
        update_engagement_verification(user.id, current_train, action)
        
        actions = {
            "like": "liking",
            "comment": "commenting", 
            "retweet": "retweeting"
        }
        
        await update.message.reply_text(
            f"✅ **Engagement Verified!**\n\n"
            f"**Action**: {actions[action]} admin posts\n"
            f"**Train**: {current_train}\n"
            f"**User**: @{user_data['twitter_handle']}\n\n"
            f"🎯 Complete all 3 actions for bonus XP!\n"
            f"❤️ Like | 💬 Comment | 🔁 Retweet"
        )
    else:
        await update.message.reply_text("❌ Invalid action. Use: like, comment, or retweet")

# Scheduled functions
async def post_train_schedule(context):
    job = context.job
    train_info = job.data
    
    train_message = f"""
🚂 **{train_info['name']} IS HERE!** 🚂

⏰ **Time**: {datetime.now(LAGOS_TZ).strftime('%I:%M %p')}
📅 **Date**: {datetime.now(LAGOS_TZ).strftime('%Y-%m-%d')}

🎯 **How to Join:**
1. Use `/joindaily` to register
2. Engage with ALL admin Twitter posts:
{chr(10).join(['   • ' + link for link in ADMIN_TWITTER_LINKS])}
3. Like, comment, and retweet each post
4. Drop your Twitter link below
5. Engage with other members' posts

💎 **Rewards:**
• 50 XP for participation
• Bonus XP for complete verification
• Streak bonuses for daily participation

🔒 **Verification Required:**
Use `/verify like`, `/verify comment`, `/verify retweet`
after completing each action!

🏆 **Daily Leaderboard Updates After This Train!**

👇 **Click below to join now!**
    """
    
    # Create join button
    keyboard = [[InlineKeyboardButton("🚂 Join Daily Train", callback_data="join_daily")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=train_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Posted {train_info['name']} at {datetime.now(LAGOS_TZ)}")
    except Exception as e:
        logger.error(f"❌ Failed to post train: {e}")

async def post_daily_leaderboard(context):
    daily_leaders = get_daily_leaderboard()
    
    if not daily_leaders:
        logger.info("No daily leaderboard data yet")
        return
    
    leaderboard_text = f"🏆 **DAILY LEADERBOARD - {datetime.now(LAGOS_TZ).strftime('%Y-%m-%d')}** 🏆\n\n"
    leaderboard_text += "**Top 10 Performers Today:**\n\n"
    
    for i, (user_id, username, first_name, twitter_handle, xp_earned, trains_joined) in enumerate(daily_leaders, 1):
        name = first_name or username or f"User {user_id}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        leaderboard_text += f"{medal} **{name}** 🐦@{twitter_handle}\n"
        leaderboard_text += f"   └─ {xp_earned} XP • {trains_joined} trains\n\n"
    
    leaderboard_text += "💫 **Keep grinding! Next trains at 10AM, 2PM, 6PM, 10PM**"
    
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_CHAT_ID,
            text=leaderboard_text,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Posted daily leaderboard to channel at {datetime.now(LAGOS_TZ)}")
    except Exception as e:
        logger.error(f"❌ Failed to post leaderboard: {e}")

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "join_daily":
        mock_update = Update(update.update_id, message=query.message)
        await joindaily_cmd(mock_update, context)

async def handle_message(update: Update, context):
    user = update.effective_user
    create_user(user.id, user.username, user.first_name)
    
    # Only give XP if user has linked Twitter
    user_data = get_user(user.id)
    if user_data and user_data.get('twitter_handle'):
        update_xp(user.id, 1, "comment")

def run_bot():
    # Use Updater for version 13.15 compatibility
    from telegram.ext import Updater
    
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("linktwitter", linktwitter_cmd))
    dispatcher.add_handler(CommandHandler("myxp", myxp))
    dispatcher.add_handler(CommandHandler("leaderboard", leaderboard))
    dispatcher.add_handler(CommandHandler("dailyleaderboard", daily_leaderboard_cmd))
    dispatcher.add_handler(CommandHandler("joindaily", joindaily_cmd))
    dispatcher.add_handler(CommandHandler("verify", verify_engagement))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Setup job queue for scheduled tasks
    job_queue = updater.job_queue
    
    # Schedule train posts
    for train in TRAIN_SCHEDULE:
        job_queue.run_daily(
            post_train_schedule,
            time=datetime.strptime(f"{train['hour']}:{train['minute']}", "%H:%M").time(),
            days=(0, 1, 2, 3, 4, 5, 6),
            context=train
        )
        logger.info(f"✅ Scheduled {train['name']} at {train['hour']}:{train['minute']:02d}")
    
    # Daily leaderboard at 11:30 PM
    job_queue.run_daily(
        post_daily_leaderboard,
        time=datetime.strptime("23:30", "%H:%M").time(),
        days=(0, 1, 2, 3, 4, 5, 6)
    )
    logger.info("✅ Scheduled daily leaderboard at 23:30")
    
    logger.info("🚀 Bot starting on Render.com...")
    updater.start_polling()
    updater.idle()

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    logger.info("🤖 Starting Elite XP Bot on Render...")
    
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start Telegram bot
    run_bot()
