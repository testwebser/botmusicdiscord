"""DISCORD MUSIC BOT with Lavalink - Version 3.0"""

# Importing libraries
import asyncio
import threading
import time
from flask import Flask, jsonify

import discord
from discord.ext import commands, tasks
import wavelink

from dotenv import load_dotenv
import os

load_dotenv()

# DISCORD API TOKEN FROM .ENV
DISCORD_API_TOKEN = os.getenv("DISCORD_API_TOKEN")

if not DISCORD_API_TOKEN:
    raise ValueError("DISCORD_API_TOKEN is not set in .env file")

# Global variables
is_looping_playlist = False

# Defining help command
help_command = commands.DefaultHelpCommand(no_category='Commands')

# Defining prefix of commands
bot = commands.Bot(command_prefix='-', intents=discord.Intents.all(), help_command=help_command)

# ===== HEALTH CHECK SERVER FOR MONITORING =====
app = Flask(__name__)
bot_start_time = time.time()

@app.route('/')
def home():
    """Home endpoint - แสดงสถานะ bot"""
    uptime_seconds = int(time.time() - bot_start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    
    return jsonify({
        'status': 'online',
        'bot_name': bot.user.name if bot.user else 'Starting...',
        'bot_id': str(bot.user.id) if bot.user else None,
        'latency_ms': round(bot.latency * 1000, 2) if bot.latency > 0 else 0,
        'uptime': {
            'seconds': uptime_seconds,
            'formatted': f'{uptime_days}d {uptime_hours % 24}h {uptime_minutes % 60}m'
        },
        'guilds': len(bot.guilds) if bot.guilds else 0,
        'music_system': 'Lavalink',
        'message': 'Bot is running!'
    })

@app.route('/health')
def health():
    """Simple health check - สำหรับ UptimeRobot/Betterstack"""
    return jsonify({'status': 'ok'}), 200

@app.route('/ping')
def ping():
    """Ping endpoint"""
    return 'pong', 200

def run_flask():
    """รัน Flask server ในอีก thread"""
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# เริ่ม Flask server ใน background thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
print(f'🌐 Health check server started on port {os.getenv("PORT", 8080)}')

# ===== END HEALTH CHECK SERVER =====


# When the bot is ready
@bot.event
async def on_ready():
    status.start()
    print('Bot is online')
    print('🎵 Connecting to Lavalink...')
    
    # Connect to Lavalink node
    node = wavelink.Node(uri='https://lavalinkv4.serenetia.com:443', password='https://dsc.gg/ajidevserver')
    await wavelink.Pool.connect(nodes=[node], client=bot, cache_capacity=100)
    print('✅ Connected to Lavalink!')


@tasks.loop(seconds=60)
async def status():
    """Update bot presence - runs every 60 seconds to avoid rate limits and connection issues"""
    try:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Music via Lavalink"))
    except Exception:
        # Ignore errors during reconnection (ClientConnectionResetError etc.)
        pass


# Event when track ends
@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    """Handle track end - play next in queue or loop"""
    player = payload.player
    
    if not player:
        return
    
    # ถ้าเปิด loop ให้เล่นซ้ำ
    if is_looping_playlist and payload.track:
        await player.play(payload.track)
    # ถ้าไม่ loop และมีเพลงต่อไปใน queue
    elif player.queue:
        next_track = player.queue.get()
        await player.play(next_track)


# Ping Command
@bot.command(name='ping', aliases=['PING'], help='Verifies the bot\'s latency')
async def ping(ctx):
    embed = discord.Embed(title="Pong!   🏓", description=f'{round(bot.latency * 1000)} ms', color=discord.Color.red())
    await ctx.send(embed=embed, delete_after=60)


# Play Command
@bot.command(name='play', aliases=['p', 'PLAY', 'Play', 'P'],
             help='Add a song to the queue (Example: -play dark necessities)')
async def play(ctx, *, query: str):
    """Play a song from YouTube"""
    
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a voice channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    # Get or create player
    try:
        if not ctx.voice_client:
            player: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            player: wavelink.Player = ctx.voice_client
            
            # Move to user's channel if different
            if player.channel != ctx.author.voice.channel:
                await player.move_to(ctx.author.voice.channel)
    except wavelink.exceptions.ChannelTimeoutException:
        embed = discord.Embed(
            description="❌ Could not connect to voice channel (timeout). Please try again.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
        return
    except Exception as e:
        embed = discord.Embed(
            description=f"❌ Failed to connect: {str(e)[:100]}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=15)
        return
    
    # Search for track
    tracks: wavelink.Search = await wavelink.Playable.search(query)
    
    if not tracks:
        embed = discord.Embed(description="Could not find that song", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    track = tracks[0]
    
    # If already playing, add to queue
    if player.playing:
        await player.queue.put_wait(track)
        embed = discord.Embed(title="Queued", color=discord.Color.green())
        embed.add_field(name="Song", value=track.title, inline=False)
        embed.add_field(name="Duration", value=f"{track.length // 60000}:{(track.length // 1000) % 60:02d}", inline=False)
        embed.add_field(name="By", value=ctx.author.mention, inline=False)
        await ctx.send(embed=embed, delete_after=120)
    else:
        # Play immediately
        await player.play(track)
        embed = discord.Embed(title="Now Playing", color=discord.Color.green())
        embed.add_field(name="Song", value=track.title, inline=False)
        embed.add_field(name="Duration", value=f"{track.length // 60000}:{(track.length // 1000) % 60:02d}", inline=False)
        embed.add_field(name="By", value=ctx.author.mention, inline=False)
        await ctx.send(embed=embed, delete_after=120)


# Queue Command
@bot.command(name='queue', aliases=['q', 'QUEUE', 'Queue', 'Q'], help='Shows the queue of songs')
async def queue(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not in a voice channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    
    embed = discord.Embed(title="Queue", color=discord.Color.green())
    
    # Show currently playing
    if player.current:
        embed.add_field(
            name=f"***Now Playing*** - {player.current.title}",
            value=f"Duration: {player.current.length // 60000}:{(player.current.length // 1000) % 60:02d}",
            inline=False
        )
    
    # Show queue
    if player.queue:
        for i, track in enumerate(player.queue[:25], 1):
            embed.add_field(
                name=f"{i}. {track.title}",
                value=f"{track.length // 60000}:{(track.length // 1000) % 60:02d}",
                inline=False
            )
        if len(player.queue) > 25:
            embed.set_footer(text=f"And {len(player.queue) - 25} more...")
    else:
        if not player.current:
            embed.description = "Queue is empty"
    
    await ctx.send(embed=embed, delete_after=3600)


# Skip Command
@bot.command(name='skip', aliases=['s', 'SKIP', 'Skip', 'S'], help='Skips the current song')
async def skip(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not playing anything", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if player.current:
        skipped_title = player.current.title
        await player.skip(force=True)
        embed = discord.Embed(title="Song skipped", description=skipped_title, color=discord.Color.green())
        await ctx.send(embed=embed, delete_after=120)
    else:
        embed = discord.Embed(description="Nothing is playing", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)


# Pause Command
@bot.command(name='pause', aliases=['pa', 'Pause', 'PAUSE'], help='Pause the song')
async def pause(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not in a voice channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if player.playing and not player.paused:
        await player.pause(True)
        embed = discord.Embed(description="Paused", color=discord.Color.blue())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="Nothing is playing to pause", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)


# Resume Command
@bot.command(name='resume', 
             aliases=['unpause', 're', 'un', 'Resume', 'Unpause', 'RESUME', 'UNPAUSE', 'RE'], 
             help='Resume the song')
async def resume(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not in a voice channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if player.paused:
        await player.pause(False)
        embed = discord.Embed(description="Resumed", color=discord.Color.blue())
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(description="The song is not paused", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)


# Loop Playlist Command
@bot.command(name='loop', aliases=['l', 'LOOP', 'Loop'], help='Loops the current song')
async def playlist_loop(ctx):
    global is_looping_playlist
    
    is_looping_playlist = not is_looping_playlist
    
    embed = discord.Embed(
        description=f"{'Loop **enabled**' if is_looping_playlist else 'Loop **disabled**'}",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)


# Leave Command
@bot.command(name='leave', aliases=['LEAVE', 'Leave', 'disconnect'], help='Leaves the Voice Channel')
async def leave(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not in a voice channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    await player.disconnect()
    
    embed = discord.Embed(description="Disconnected", color=discord.Color.dark_grey())
    await ctx.send(embed=embed, delete_after=15)


# Now Playing Command
@bot.command(name='nowplaying', aliases=['np', 'Nowplaying', 'NP', 'NOWPLAYING'],
             help='Shows the song that is playing')
async def nowplaying(ctx):
    if not ctx.author.voice:
        embed = discord.Embed(description="You're not in a Voice Channel", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    if not ctx.voice_client:
        embed = discord.Embed(description="Bot is not playing anything", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)
        return
    
    player: wavelink.Player = ctx.voice_client
    
    if player.current:
        track = player.current
        position = player.position
        duration = track.length
        
        # Progress bar
        progress = int((position / duration) * 20) if duration > 0 else 0
        bar = "▬" * progress + "🔘" + "▬" * (20 - progress)
        
        embed = discord.Embed(title="Now Playing", description=track.title, color=discord.Color.blue())
        embed.add_field(
            name="Progress",
            value=f"{position // 60000}:{(position // 1000) % 60:02d} {bar} {duration // 60000}:{(duration // 1000) % 60:02d}",
            inline=False
        )
        await ctx.send(embed=embed, delete_after=120)
    else:
        embed = discord.Embed(description="Nothing is playing", color=discord.Color.red())
        await ctx.send(embed=embed, delete_after=15)


# bot run logging in with token
bot.run(DISCORD_API_TOKEN)
