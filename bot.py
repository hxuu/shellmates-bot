#J'ai ajouté ce code pour tester si le bot est bien connecté ou non et pour exécuter trois commandes :

#!hello : Le bot affiche le message "Hello, world !"
#!say "ton message ici" : Le bot affiche ton message
#!ping : Le bot affiche "Pong"
#remarque: n'oubilez pas d'enter votre bot token

import discord
from discord.ext import commands
import json
import os
print("Répertoire courant :", os.getcwd())


# Crée une instance du bot
intents = discord.Intents.default()
intents.message_content = True  # Assure-toi que ton bot peut lire le contenu des messages
bot = commands.Bot(command_prefix='!', intents=intents)
# Chemin pour le fichier JSON
REMINDER_FILE = "data/reminders.json"

# Fonction pour vérifier ou créer le fichier reminders.json
def ensure_data_file():
    """
    Vérifie l'existence du répertoire et du fichier JSON.
    Si le fichier n'existe pas, il est créé avec une structure initiale.
    """
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Répertoire 'data' créé.")  # Message pour vérifier si le répertoire est créé

    if not os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "w") as file:
            json.dump({"REMINDERS": []}, file)  # Structure initiale
        print(f"Fichier '{REMINDER_FILE}' créé avec une structure vide.")  # Message pour vérifier la création du fichier


def load_reminders():
    """
    Charge les rappels depuis le fichier JSON.
    """
    ensure_data_file()
    try:
        with open(REMINDER_FILE, "r") as file:
            data = json.load(file)
            return data.get("REMINDERS", [])  # Retourne les rappels
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_reminders(reminders):
    """
    Sauvegarde les rappels dans le fichier JSON.
    """
    ensure_data_file()
    try:
        with open(REMINDER_FILE, "w") as file:
            json.dump({"REMINDERS": reminders}, file, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")



# Fonction pour sauvegarder les rappels
def save_reminders(reminders):
    ensure_data_file()
    try:
        with open(REMINDER_FILE, "r") as file:
            data = json.load(file)

        data["REMINDERS"] = reminders  # Sauvegarde les rappels dans la clé "REMINDERS"

        with open(REMINDER_FILE, "w") as file:
            json.dump(data, file, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des rappels : {e}")



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

# Commande myhelp au lieu de !help car elle existe par defaut dans la  bibliothèque discord.py
@bot.command()
async def myhelp(ctx):
    help_text = """
    **Commandes disponibles :**
    - `!schedule <title> <date> <time>` : Planifier un rappel.
    - `!reminders` : Voir tous vos rappels.
    - `!delete <ID>` : Supprimer un rappel spécifique.
    """
    await ctx.send(help_text)

# Commande !schedule
import uuid

@bot.command()
async def schedule(ctx, title: str, date: str, time: str):
    try:
        # Générer un ID unique pour le rappel
        reminder_id = str(uuid.uuid4())  # Utilisation de uuid pour créer un identifiant unique
        reminder = {
            "id": reminder_id,  # Ajouter l'ID
            "user": ctx.author.name,
            "title": title,
            "date": date,
            "time": time
        }
        reminders = load_reminders()
        reminders.append(reminder)
        save_reminders(reminders)
        await ctx.send(f"✅ Rappel planifié : {title} le {date} à {time}. (ID: {reminder_id})")
    except Exception as e:
        await ctx.send("❌ Une erreur est survenue lors de la planification du rappel.")
        print(f"Erreur dans la commande schedule : {e}")


#commande reminders
@bot.command()
async def reminders(ctx):
    try:
        reminders = load_reminders()
        user_reminders = [r for r in reminders if r["user"] == ctx.author.name]

        if user_reminders:
            response = "**Vos rappels :**\n"
            for i, reminder in enumerate(user_reminders, start=1):
                response += f"{i}. **{reminder['title']}** - {reminder['date']} {reminder['time']} (ID: {reminder['id']})\n"
        else:
            response = "Vous n'avez aucun rappel."
        await ctx.send(response)
    except Exception as e:
        await ctx.send("❌ Une erreur est survenue lors de l'affichage des rappels.")
        print(f"Erreur dans la commande reminders : {e}")


#commande delete 
@bot.command()
async def delete(ctx, reminder_id: str):
    try:
        reminders = load_reminders()
        user_reminders = [r for r in reminders if r["user"] == ctx.author.name]

        # Chercher le rappel avec l'ID correspondant
        reminder_to_delete = None
        for reminder in user_reminders:
            if reminder['id'] == reminder_id:
                reminder_to_delete = reminder
                break

        if reminder_to_delete:
            reminders.remove(reminder_to_delete)
            save_reminders(reminders)
            await ctx.send(f"✅ Rappel supprimé : {reminder_to_delete['title']} (ID: {reminder_id})")
        else:
            await ctx.send("❌ ID de rappel invalide. Veuillez vérifier vos rappels avec !reminders.")
    except Exception as e:
        await ctx.send("❌ Une erreur est survenue lors de la suppression du rappel.")
        print(f"Erreur dans la commande delete : {e}")

  

# Lancer le bot avec ton token
bot.run('your token ')
