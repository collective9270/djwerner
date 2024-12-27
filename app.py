import discord
from discord.ext import commands
from discord import app_commands
from yt_dlp import YoutubeDL

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# YouTube Downloader Options
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {'options': '-vn'}

# Dictionary to store voice client state
voice_clients = {}
queues = {}

def add_to_queue(guild_id, song):
    if guild_id not in queues:
        queues[guild_id] = []
    queues[guild_id].append(song)

def get_next_in_queue(guild_id):
    if guild_id in queues and queues[guild_id]:
        return queues[guild_id].pop(0)
    return None

def is_queue_empty(guild_id):
    return not queues.get(guild_id)

# Events
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands synced: {len(synced)} commands available.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Slash Commands
@bot.tree.command(name="join", description="Join the voice channel of the user.")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()
        voice_clients[interaction.guild.id] = voice_client
        await interaction.response.send_message(f"Joined {channel.name}")
    else:
        await interaction.response.send_message("You need to be in a voice channel for me to join.")

@bot.tree.command(name="leave", description="Leave the voice channel.")
async def leave(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in voice_clients:
        await voice_clients[guild_id].disconnect()
        del voice_clients[guild_id]
        if guild_id in queues:
            del queues[guild_id]
        await interaction.response.send_message("Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("I'm not connected to a voice channel.")

@bot.tree.command(name="queue", description="Show the current music queue.")
async def show_queue(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if is_queue_empty(guild_id):
        await interaction.response.send_message("The queue is empty.")
    else:
        queue_list = [song['title'] for song in queues[guild_id]]
        queue_message = "\n".join([f"{i + 1}. {title}" for i, title in enumerate(queue_list)])
        await interaction.response.send_message(f"Current Queue:\n{queue_message}")

@bot.tree.command(name="skip", description="Skip the current song.")
async def skip(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    if guild_id in voice_clients:
        voice_client = voice_clients[guild_id]
        if voice_client.is_playing():
            voice_client.stop()
            await interaction.response.send_message("Skipped the current song.")
        else:
            await interaction.response.send_message("I'm not playing anything!")
    else:
        await interaction.response.send_message("I'm not connected to a voice channel.")

@bot.tree.command(name="play", description="Play a song from a YouTube URL.")
async def play(interaction: discord.Interaction, url: str):
    guild_id = interaction.guild.id
    if guild_id not in voice_clients:
        await interaction.response.send_message("I'm not connected to a voice channel. Use /join to invite me.")
        return

    # Extract song information
    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        url2 = info['url']
        title = info.get('title', 'Unknown Title')

    # Add the song to the queue
    add_to_queue(guild_id, {'title': title, 'url': url2})
    await interaction.response.send_message(f"Added to queue: {title}")

    # Play the song if not already playing
    voice_client = voice_clients[guild_id]
    if not voice_client.is_playing():
        await play_next(interaction, guild_id)

async def play_next(interaction: discord.Interaction, guild_id: int):
    voice_client = voice_clients[guild_id]
    if is_queue_empty(guild_id):
        await interaction.followup.send("Queue is empty. Add more songs!")
        return

    # Get the next song
    next_song = get_next_in_queue(guild_id)
    if next_song:
        title = next_song['title']
        url = next_song['url']

        # Play the next song
        voice_client.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: bot.loop.create_task(play_next(interaction, guild_id)))
        await interaction.followup.send(f"Now playing: {title}")

@bot.tree.command(name="stop", description="Stop the current playback.")
async def stop(interaction: discord.Interaction):
    if interaction.guild.id in voice_clients:
        voice_client = voice_clients[interaction.guild.id]
        voice_client.stop()
        await interaction.response.send_message("Stopped playback.")
    else:
        await interaction.response.send_message("I'm not playing anything.")


bot.run("zie discord channel")
