import discord
from discord.ext import commands
from utils import jeson
from core import basic, time_management

# Charger la configuration du bot
bot_config = jeson.parse_json('./data/config.json')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=bot_config['COMMAND_PREFIX'], intents=intents)

# Configuration des modules
basic.setup(bot)

@bot.event
async def on_ready():
    await bot.tree.sync()  # Synchronise les commandes hybrides
    print('=============================================')
    print(f'Bot connecté en tant que {bot.user}')
    print('=============================================')
    print("Hybrid commands have been synced successfully!")
    print('=============================================')

# Commandes simples pour tester le bot
# @bot.command()
# async def hello(ctx):
#     await ctx.send("Hello, world!")

# @bot.command()
# async def say(ctx, *, message):
#     await ctx.send(message)

# @bot.command()
# async def ping(ctx):
#     await ctx.send("Pong!")

# Charger le module de gestion du temps
async def main():
    async with bot:
        await time_management.setup(bot)  
        await bot.start(bot_config['BOT_TOKEN'])

# Lancer le bot
import asyncio
asyncio.run(main())
