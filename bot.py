#J'ai ajouté ce code pour tester si le bot est bien connecté ou non et pour exécuter trois commandes :

#!hello : Le bot affiche le message "Hello, world !"
#!say "ton message ici" : Le bot affiche ton message
#!ping : Le bot affiche "Pong"
#remarque: n'oubilez pas d'enter votre bot token

from discord.ext import commands
from utils import jeson
from core import basic, time_management
import discord
import os

bot_config = jeson.parse_json('./data/config.json')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=bot_config['COMMAND_PREFIX'], intents=intents)

basic.setup(bot)
time_management.setup(bot)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print('=============================================')
    print(f'Bot connecté en tant que {bot.user}')
    print('=============================================')
    print("Hybrid commands have been synced successfully!")


bot.run(bot_config['BOT_TOKEN'])
