import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# TOKEN = os.getenv('DISCORD_TEST_TOKEN') # bot de test

BH_API_KEY = os.getenv('BH_API_KEY') 

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class BrawlBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None  
        )

    async def setup_hook(self):
        # Charge tous les fichiers .py dans le dossier cogs
        loaded = []
        failed = []
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                cog_name = f'cogs.{filename[:-3]}'
                try:
                    await self.load_extension(cog_name)
                    loaded.append(filename[:-3])
                    print(f"Loaded cog: {filename[:-3]}")
                except Exception as e:
                    failed.append((filename[:-3], str(e)))
                    print(f"Failed to load cog {filename[:-3]}: {e}")

        print(f"Loaded {len(loaded)} cogs: {', '.join(loaded)}")
        if failed:
            print(f"Failed to load {len(failed)} cogs:")
            for name, error in failed:
                print(f"  - {name}: {error}")

    async def on_ready(self):
        print(f'Bot connecté en tant que {self.user.name}')
        # Note : La synchro des commandes se fait maintenant via !sync dans general.py
        
bot = BrawlBot()

if __name__ == "__main__":
    bot.run(TOKEN)