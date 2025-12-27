import discord
from settings import Settings
from discord.ext import commands


intents = discord.Intents.default()
intents.message_content = True

class MusicBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension('cogs.music_cog')

bot = MusicBot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()
    print("✅ Slash commands synced.")


bot.run(Settings.DISCORD_TOKEN)
