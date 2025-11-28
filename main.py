from disnake.ext import commands
import disnake
import os
from dotenv import load_dotenv
import keepalive
import traceback
import keepalive

load_dotenv()

class Bot(commands.Bot):

    def __init__(self):

        super().__init__(command_prefix="!", intents=disnake.Intents.all(), command_sync_flags=commands.CommandSyncFlags.all())
        

Bot = Bot()

@Bot.event
async def on_ready():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                Bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog: {filename}")
                traceback.print_exc()

    await Bot.change_presence(activity=disnake.Game("Mangaging clockings!"))
    print("'Grove is ready to serve!' - AtomicPotassium")

if __name__ == "__main__":
    print("Starting API and bot...")
    keepalive.keep_alive()

    bot_app = Bot.run(os.getenv("BOT_TOKEN"))

