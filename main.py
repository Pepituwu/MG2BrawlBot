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
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
        print("✅ Toutes les extensions sont chargées.")

    async def on_ready(self):
        print(f'Bot connecté en tant que {self.user.name}')
        # Note : La synchro des commandes se fait maintenant via !sync dans general.py
        
bot = BrawlBot()

if __name__ == "__main__":
    bot.run(TOKEN)