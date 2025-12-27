import discord
import random
from constants import force_skip_probability, force_skip_votes

class QueueSelect(discord.ui.Select):
    def __init__(self, queue):
        options = [
            discord.SelectOption(
                label=song['title'][:100],
                description=f"Posición {i + 1}",
                value=str(i)
            )
            for i, song in enumerate(queue[:25])
        ]

        super().__init__(
            placeholder="Escoja mostro",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        from constants import queue

        index = int(self.values[0])
        song = queue.pop(index)

        vc = interaction.guild.voice_client
        vc.stop()

        queue.insert(0, song)

        await interaction.response.send_message(
            f"🎶 Seleccionada: **{song['title']}**",
            ephemeral=True
        )

class QueueView(discord.ui.View):
    def __init__(self, queue):
        super().__init__(timeout=30)

        if queue:
            self.add_item(QueueSelect(queue))

class MusicControls(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.voice is None:
            await interaction.response.send_message(
                "❌ Debes estar en un canal de voz.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⏯️ Pausa", style=discord.ButtonStyle.primary)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client

        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado", ephemeral=False)
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=False)
        else:
            await interaction.response.send_message("❌ No hay audio.", ephemeral=False)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client

        if not vc or not vc.is_playing():
            await interaction.response.send_message("❌ No hay ninguna canción reproduciéndose.", ephemeral=False)
            return
        
        if not interaction.user.voice or interaction.user.voice.channel != vc.channel:
            await interaction.response.send_message("❌ Debes estar en un canal de voz para saltar la canción.", ephemeral=False)
            return
        
        user_id = interaction.user.id

        if user_id in force_skip_votes:
            await interaction.response.send_message(
                "⛔ Ya intentaste forzar skip en esta canción.",
                ephemeral=True
            )
            return
    
        force_skip_votes.add(user_id)

        roll = random.randint(1, 100)

        if roll <= force_skip_probability:
            vc.stop()
            await interaction.response.send_message(
                f"🎲 **{interaction.user.display_name}** 🎉\n"
                "⏭️ Skip concedido.",
                ephemeral=False
            )
        else:
            await interaction.response.send_message(
                f"🎲 **{interaction.user.display_name}** 😢\n"
                "⏭️ Skip denegado burrooo.",
                ephemeral=False
            )

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        vc = interaction.guild.voice_client

        if vc:
            vc.stop()
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Música detenida", ephemeral=True)

    @discord.ui.button(label="📜 Cola", style=discord.ButtonStyle.success)
    async def show_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        from constants import queue

        if not queue:
            await interaction.response.send_message("📭 La cola está vacía.", ephemeral=True)
            return
    
        await interaction.response.send_message(
            "Seleccione una canción de la cola:",
            view=QueueView(queue),
            ephemeral=False
        )
