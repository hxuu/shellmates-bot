#J'ai ajouté ce code pour tester si le bot est bien connecté ou non et pour exécuter trois commandes :

#!hello : Le bot affiche le message "Hello, world !"
#!say "ton message ici" : Le bot affiche ton message
#!ping : Le bot affiche "Pong"
#remarque: n'oubilez pas d'enter votre bot token

import discord
from discord.ext import commands

# Crée une instance du bot
intents = discord.Intents.default()
intents.message_content = True  # Assure-toi que ton bot peut lire le contenu des messages
bot = commands.Bot(command_prefix='!', intents=intents)

# Quand le bot est prêt, affiche un message dans la console
@bot.event
async def on_ready():
    print(f'Bot connecté en tant que {bot.user}')

# Un simple exemple de commande
@bot.command()
async def hello(ctx):
    await ctx.send('Hello, world!')
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

@bot.command()
async def say(ctx, *, message):
    await ctx.send(message)

# Lancer le bot avec ton token
bot.run('entrer votre bot token')
