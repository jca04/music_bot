
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN")