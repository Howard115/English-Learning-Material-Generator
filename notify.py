from discordwebhook import Discord
import os
from dotenv import load_dotenv

load_dotenv()

discord = Discord(url=os.getenv("DISCORD_WEBHOOK_URL"))
discord.post(content=(
    f"""
    🔔 **New English Learning Material Generated!**
    "https://github.com/Howard115/English-Learning-Material-Generator/blob/main/demo/day{len([f for f in os.listdir('demo') if f.startswith('day')])}.md"
    """
))