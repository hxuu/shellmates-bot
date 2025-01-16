import uuid
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from utils.reminders import load_reminders, save_reminders

async def setup(bot):
    """
    Configurer le Cog de gestion du temps pour le bot.
    """
    await bot.add_cog(TimeManagementCog(bot))


class TimeManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_notifications = set()

    async def cog_load(self):
        """
        Méthode appelée lorsque le Cog est chargé. Démarre la vérification des rappels.
        """
        self.bot.loop.create_task(self.check_reminders())

    async def check_reminders(self):
        """
        Tâche en arrière-plan pour vérifier les rappels périodiquement.
        """
        print("Reminder checker function has started!")
        await self.bot.wait_until_ready()
        while True:
            try:
                current_time = datetime.now()
                reminders = load_reminders()
                reminders_to_remove = []

                for reminder in reminders:
                    try:
                        reminder_datetime = datetime.strptime(
                            f"{reminder['date']} {reminder['time']}", "%Y-%m-%d %H:%M"
                        )
                        time_until_reminder = reminder_datetime - current_time
                        notification_key = f"{reminder['id']}_5min"

                        # Notification 5 minutes avant
                        if 4 <= time_until_reminder.total_seconds() / 60 <= 5 and notification_key not in self.sent_notifications:
                            channel = self.bot.get_channel(reminder["channel_id"])
                            if channel:
                                mentions = (
                                    ", ".join(f"<@{uid}>" for uid in reminder.get('mentions', []))
                                    if reminder.get('mentions')
                                    else "@everyone"
                                )
                                await channel.send(
                                    f"⏰ Rappel dans 5 minutes : **{reminder['title']}**\n\n"
                                    f"{mentions}\n\n📅 {reminder['date']} à {reminder['time']}"
                                )
                                self.sent_notifications.add(notification_key)

                        # Supprimer les rappels passés
                        if time_until_reminder.total_seconds() < -300:  # Supprime après 5 min passées
                            reminders_to_remove.append(reminder)
                            if notification_key in self.sent_notifications:
                                self.sent_notifications.remove(notification_key)

                    except Exception as e:
                        print(f"Error processing reminder {reminder.get('id', 'unknown')}: {e}")
                        continue

                if reminders_to_remove:
                    reminders = [r for r in reminders if r not in reminders_to_remove]
                    save_reminders(reminders)

            except Exception as e:
                print(f"Error in reminder checker: {e}")

            await asyncio.sleep(30)

    def format_time_until(self, time_delta):
        """
        Format a timedelta into a human-readable string.
        """
        total_seconds = int(time_delta.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        parts = []
        if days > 0:
            parts.append(f"{days} jour{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} heure{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} seconde{'s' if seconds > 1 else ''}")

        if not parts:
            return "moins d'une seconde"
        return ", ".join(parts)

    @commands.hybrid_command(
        name="schedule",
        description="Programme un rappel pour une date et heure spécifiques avec mentions optionnelles."
    )
    async def schedule(self, ctx, title: str, date: str, time: str, *, mentions: str = None):
        """
        Planifie un rappel.
        """
        try:
            reminder_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            if reminder_datetime < datetime.now():
                await ctx.send("❌ La date et l'heure doivent être dans le futur.")
                return

            mentioned_users = [mention.id for mention in ctx.message.mentions] if mentions else []
            reminder_id = str(uuid.uuid4())
            reminder = {
                "id": reminder_id,
                "user_id": ctx.author.id,
                "username": ctx.author.name,
                "channel_id": ctx.channel.id,
                "title": title,
                "date": date,
                "time": time,
                "mentions": mentioned_users if mentioned_users else None
            }

            reminders = load_reminders()
            reminders.append(reminder)
            save_reminders(reminders)

            time_until = reminder_datetime - datetime.now()
            formatted_time = self.format_time_until(time_until)

            response = (
                f"✅ Rappel planifié : {title}\n\n"
                f"📅 Date : {date} à {time}\n\n"
                f"⏰ Dans environ {formatted_time}\n\n"
                f"👥 Notification : {', '.join(f'<@{uid}>' for uid in mentioned_users) if mentioned_users else '@everyone' }"
                f"\n\n🆔 ID: {reminder_id}\n\n"
                f"📢 Les notifications seront envoyées dans ce canal"
            )
            await ctx.send(response)

        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.")
            print(f"Erreur : {e}")

    @commands.hybrid_command(
        name="reminders",
        description="Affiche tous vos rappels actifs."
    )
    async def reminders(self, ctx):
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == ctx.author.id]

            if not user_reminders:
                await ctx.send("Vous n'avez aucun rappel.")
                return

            user_reminders.sort(key=lambda r: f"{r['date']} {r['time']}")
            response = "**Vos rappels actifs :**\n\n"
            for i, reminder in enumerate(user_reminders, start=1):
                reminder_datetime = datetime.strptime(f"{reminder['date']} {reminder['time']}", "%Y-%m-%d %H:%M")
                time_until = reminder_datetime - datetime.now()
                response += (
                    f"{i}. **{reminder['title']}**\n\n"
                    f"📅 {reminder['date']} à {reminder['time']}\n\n"
                    f"⏰ Dans {self.format_time_until(time_until)}\n\n"
                    f"🆔 ID : {reminder['id']}\n\n"
                )
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.")
            print(f"Erreur : {e}")

    @commands.hybrid_command(
        name="delete",
        description="Supprime un rappel spécifique par son ID."
    )
    async def delete(self, ctx, reminder_id: str):
        try:
            reminders = load_reminders()
            reminder_to_delete = next((r for r in reminders if r["id"] == reminder_id and r["user_id"] == ctx.author.id), None)

            if not reminder_to_delete:
                await ctx.send("❌ Aucun rappel trouvé avec cet ID ou il ne vous appartient pas.")
                return

            reminders.remove(reminder_to_delete)
            save_reminders(reminders)
            await ctx.send(f"✅ Rappel supprimé : **{reminder_to_delete['title']}** (ID : {reminder_id})")

        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.")
            print(f"Erreur : {e}")

    @commands.hybrid_command(
        name="check_permissions",
        description="Vérifie les permissions du bot dans ce canal."
    )
    async def check_permissions(self, ctx):
        try:
            permissions = ctx.channel.permissions_for(ctx.guild.me)
            perms_list = [
                ("Send Messages", permissions.send_messages),
                ("Embed Links", permissions.embed_links),
                ("Attach Files", permissions.attach_files),
                ("Mention Everyone", permissions.mention_everyone),
                ("Manage Messages", permissions.manage_messages),
            ]
            response = "**Permissions du bot dans ce canal :**\n" + "\n".join(
                f"{'✅' if value else '❌'} {perm}" for perm, value in perms_list
            )
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.")
            print(f"Erreur : {e}")
