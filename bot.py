import discord
import yt_dlp
import asyncio
import random
from settings import Settings
from discord.ext import commands
from music_controls import MusicControls
from constants import queue, force_skip_votes, force_skip_probability


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_options = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['android']
        }
    }
}

ffmpeg_opts = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_options)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def play_next(ctx):
    if not queue:
        return
    
    force_skip_votes.clear() # reset por canción

    song = queue.pop(0)
    source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_opts)

    ctx.voice_client.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            play_next(ctx),
            bot.loop
        )
    )

    await ctx.send(f"🎶 Reproduciendo: **{song['title']}**", view=MusicControls(ctx))

@bot.command()
async def play(ctx, *, search: str):
    if not ctx.author.voice:
        await ctx.send("❌ Parcero metase a la llamada.")
        return

    channel = ctx.author.voice.channel

    if not ctx.voice_client:
        await channel.connect()

    with ytdl:
        info = ytdl.extract_info(search, download=False)
        song = {
            'title': info['title'],
            'url': info['url']
        }

    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        queue.append(song)
        await ctx.send(f"➕ Agregado a la cola: **{song['title']}**")
    else:
        source = discord.FFmpegPCMAudio(song['url'], **ffmpeg_opts)
        ctx.voice_client.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx),
                bot.loop
            )
        )

        await ctx.send(
            f"🎶 Reproduciendo: **{song['title']}**",
            view=MusicControls(ctx)
        )

@bot.command(name='cola')
async def queue_list(ctx):
    if not queue:
        await ctx.send("La cola está vacía.")
        return

    message = "🎵 Cola de reproducción:\n"
    for i, song in enumerate(queue, start=1):
        message += f"{i}. {song['title']}\n"

    await ctx.send(message, view=MusicControls(ctx))

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada.", view=MusicControls(ctx))
    else:
        await ctx.send("❌ No hay ninguna canción reproduciéndose.", view=MusicControls(ctx))

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()

@bot.command(name='forceskip')
async def force_skip(ctx: commands.Context):
    vc = ctx.voice_client

    if not ctx.author.voice:
        await ctx.send("❌ Parcero metase a la llamada.", view=MusicControls(ctx))
        return

    if not vc or not vc.is_playing():
        await ctx.send("❌ No hay ninguna canción reproduciéndose.", view=MusicControls(ctx))
        return

    user_id = ctx.author.id
    
    if user_id in force_skip_votes:
        await ctx.send("⛔ Ya intentaste forzar skip en esta canción.")
        return
    
    force_skip_votes.add(user_id)

    chance = random.randint(1, 100)

    if chance <= force_skip_probability:
        vc.stop()
        await ctx.send(f"🎲 **{ctx.author.display_name}**\n⏭️ Skip concedido.", view=MusicControls(ctx))
    else:
        await ctx.send(f"🎲 **{ctx.author.display_name} BURRO 😈**\n", view=MusicControls(ctx))


bot.run(Settings.DISCORD_TOKEN)
