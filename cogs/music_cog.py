import discord
import yt_dlp
import asyncio
import random
from discord.ext import commands
from discord import app_commands
from music.music_state import MusicState
from music.repository import MusicRepository
from utils.music_state_serializer import hydrate_state, serializer_state

from constants import queue, force_skip_votes, force_skip_probability
from ui.music_controls import MusicControls

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.states = {}

        self.repo = MusicRepository()

        self.ytdl_options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'noplaylist': True,
            'default_search': 'ytsearch1', ## Buscar en YouTube si no es URL
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            }
        }

        self.ffmpeg_opts = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_options)
    
    async def play_next(self, interaction: discord.Interaction):

        vc = interaction.guild.voice_client
        state = self.get_state(interaction.guild.id)
        self.repo.save(interaction.guild.id, serializer_state(state))

        if state.loop and state.current:
            song = state.current
        elif state.queue:
            song = state.queue.pop(0)
            state.current = song
        else:
            state.current = None
            return


        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song['url']),
            volume=state.volume
        )

        vc.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(interaction), self.bot.loop
            )
        )

        # await ctx.send(f"🎶 Reproduciendo: **{song['title']}**", view=MusicControls(ctx))
    
    @app_commands.command(name="play", description="Reproduce una canción desde YouTube")
    @app_commands.describe(search="Título o URL de la canción")
    async def play(self, interaction: discord.Interaction, search: str):

        await interaction.response.defer(thinking=True) ## Para evitar timeouts

        if not interaction.user.voice:
            await interaction.response.send_message("❌ Parcero metase a la llamada.")
            return

        channel = interaction.user.voice.channel

        if not interaction.guild.voice_client:
            await channel.connect()

        song = self.extract_song(search)
        state = self.get_state(interaction.guild.id)
        state.queue.append(song) ## Agregar a la cola del estado
        self.repo.save(interaction.guild.id, serializer_state(state)) ## Guardar estado actualizado

        with self.ytdl:
            info = self.ytdl.extract_info(search, download=False)
            song = {
                'title': info['title'],
                'url': info['url']
            }

        if interaction.guild.voice_client.is_playing() or interaction.guild.voice_client.is_paused():
            queue.append(song)
            await interaction.followup.send(f"➕ Agregado a la cola: **{song['title']}**", view=MusicControls(interaction))
        else:
            source = discord.FFmpegPCMAudio(song['url'], **self.ffmpeg_opts)
            interaction.guild.voice_client.play(
                source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(interaction),
                    self.bot.loop
                )
            )

            await interaction.followup.send(
                f"🎶 Reproduciendo: **{song['title']}**",
                view=MusicControls(interaction)
            )
    
    @app_commands.command(name="queue", description="Muestra la cola de reproducción")
    async def queue_list(self, interaction: discord.Interaction):

        if not queue:
            await interaction.response.send_message("La cola está vacía.")
            return

        message = "🎵 Cola de reproducción:\n"
        for i, song in enumerate(queue, start=1):
            message += f"{i}. {song['title']}\n"

        await interaction.response.send_message(message, view=MusicControls(interaction))

    @app_commands.command(name="skip", description="Salta la canción actual")
    async def skip(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Canción saltada.", view=MusicControls(interaction))
        else:
            await interaction.response.send_message("❌ No hay ninguna canción reproduciéndose.", view=MusicControls(interaction))
    
    @app_commands.command(name="stop", description="Detiene la reproducción y desconecta al bot")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            interaction.guild.voice_client.stop()
            await interaction.guild.voice_client.disconnect()
        
    
    @app_commands.command(name="forceskip", description="Forzar el salto de la canción actual")
    async def force_skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Parcero metase a la llamada.", view=MusicControls(interaction))
            return

        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ No hay ninguna canción reproduciéndose.", view=MusicControls(interaction))
            return

        user_id = interaction.user.id
        
        if user_id in force_skip_votes:
            await interaction.response.send_message("⛔ Ya intentaste forzar skip en esta canción.")
            return
        
        force_skip_votes.add(user_id)

        chance = random.randint(1, 100)

        if chance <= force_skip_probability:
            vc.stop()
            await interaction.response.send_message(f"🎲 **{interaction.user.display_name}**\n⏭️ Skip concedido.", view=MusicControls(interaction))
        else:
            await interaction.response.send_message(f"🎲 **{interaction.user.display_name} BURRO 😈**\n", view=MusicControls(interaction))

    @play.autocomplete('search')
    async def play_autocomplete(self, interaction: discord.Interaction, current: str):

        if len(current) < 3:
            return []

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ytdl:
            info = ytdl.extract_info(
                f"ytsearch5:{current}",
                download=False
            )


        print(info)

        return [
            app_commands.Choice(
                name=video["title"][:100],
                value=video["url"]
            )
            for video in info.get("entries", [])
            if video
        ]


    def extract_song(self, query: str) -> dict:
        info = self.ytdl.extract_info(query, download=False)

        if 'entries' in info:
            info = info['entries'][0]

        return {
            'title': info['title'],
            'url': info['url'],
            'webpage_url': info['webpage_url'],
            'duration': info['duration']
        }

    def get_state(self, guild_id: int) -> MusicState:
        if guild_id not in self.states:
            data = self.repo.load(guild_id)

            if data:
                self.states[guild_id] = hydrate_state(data)
            else:
                self.states[guild_id] = MusicState()
        
        return self.states[guild_id]
    

async def setup(bot: commands.Bot):
        await bot.add_cog(MusicCog(bot))