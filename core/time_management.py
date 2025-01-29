import uuid
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from utils.reminders import load_reminders, save_reminders
from utils.time_manager import *

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
    
        # Initialize sent_notifications set if it doesn't exist
        if not hasattr(self, 'sent_notifications'):
            self.sent_notifications = set()

        while True:
            try:
                current_time = datetime.now()
                reminders = load_reminders()
                reminders_to_remove = []

                for reminder in reminders:
                    try:
                        reminder_datetime = datetime.fromisoformat(reminder["main_time"])
                        time_until_reminder = reminder_datetime - current_time

                    # Skip processing if the reminder is too old (more than 5 minutes past)
                        if time_until_reminder.total_seconds() < -300:
                            reminders_to_remove.append(reminder)
                            continue

                    # Check for reminder times
                        remaining_times = []
                        for rt in reminder.get("reminder_times", []):
                            reminder_time = datetime.fromisoformat(rt)
                            time_until_notification = reminder_time - current_time
                        
                            # Only process future notifications or very recent ones (within last minute)
                            if time_until_notification.total_seconds() > -60:
                                notification_key = f"{reminder['id']}_{rt}"
                            
                                # If it's time to send and we haven't sent it yet
                                if time_until_notification.total_seconds() <= 0 and notification_key not in self.sent_notifications:
                                    await self.send_reminder(reminder)
                                    self.sent_notifications.add(notification_key)
                            
                                # If it's still in the future, keep it
                                if time_until_notification.total_seconds() > 0:
                                    remaining_times.append(rt)

                        # Update reminder with remaining future notification times
                        reminder["reminder_times"] = remaining_times

                        # Check main reminder time
                        if 0 <= time_until_reminder.total_seconds() <= 60:
                            main_notification_key = f"{reminder['id']}_main"
                            if main_notification_key not in self.sent_notifications:
                                isMain = True
                                await self.send_reminder(reminder, isMain)
                                self.sent_notifications.add(main_notification_key)
                    
                        # If main time has passed and no remaining notifications, mark for removal
                        if time_until_reminder.total_seconds() < 0 and not remaining_times:
                            reminders_to_remove.append(reminder)

                    except Exception as e:
                        print(f"Error processing reminder {reminder.get('id', 'unknown')}: {e}")
                        continue

            # Clean up reminders and sent_notifications
                if reminders_to_remove:
                    # Remove old reminders
                    reminders = [r for r in reminders if r not in reminders_to_remove]
                
                    # Clean up sent_notifications for removed reminders
                    for reminder in reminders_to_remove:
                        # Remove all notification keys for this reminder
                        self.sent_notifications = {
                            key for key in self.sent_notifications 
                            if not key.startswith(f"{reminder['id']}_")
                        }
                
                    save_reminders(reminders)

                    # Log cleanup
                    print(f"Cleaned up {len(reminders_to_remove)} old reminders")

            except Exception as e:
                print(f"Error in reminder checker: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

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
    description="📅 Planifie un rappel personnalisé avec mention(s) et rappels anticipés optionnels"
    )
    @commands.has_permissions(mention_everyone=True)
    async def schedule(
        self,
        ctx,
        title: str = commands.param(
        description="Le titre ou sujet du rappel (ex: 'Réunion d'équipe', 'Deadline projet')"
    ),
        time_spec: str = commands.param(
            description="Format: '2024-01-28 15:30' pour date précise OU '30 minutes', '2h', '1 jour', '1 semaine' pour durée relative"
        ),
        remind_before: str = commands.param(
            default="5m",
            description="Quand envoyer les rappels (ex: '30m,1h,1j' pour rappels à 30min, 1h et 1 jour avant)"
        ),
        description: str = commands.param(
            default=None,
            description="Description détaillée optionnelle (ordre du jour, contexte, liens importants)"
        ),
        mentions: str = commands.param(
            default=None,
            description="Mentionnez des utilisateurs/rôles (ex: @Team @John) - nécessite des permissions"
        )
):
        try:
        # Check permissions for mentions
            if mentions:
        # Split the mentions string and extract user IDs
                mentioned_users = []
                mention_parts = mentions.split()
                for mention in mention_parts:
                # Remove <@, <@!, and > from the mention to get the ID
                    user_id = ''.join(filter(str.isdigit, mention))
                    if user_id:
                        mentioned_users.append(int(user_id))
            else:
                mentioned_users = []
        
            is_dm_reminder = len(mentioned_users) == 1
            

            # Permission checks
            # if is_dm_reminder:
            #     # Check DM permission
            #     dm_allowed_role = discord.utils.get(ctx.guild.roles, name="DM Permission")
            #     if not dm_allowed_role or dm_allowed_role not in ctx.author.roles:
            #         await ctx.send("❌ Vous n'avez pas la permission d'envoyer des rappels en message privé", ephemeral=True)
            #         return
            # else:
                # Check mention permissions for non-DM reminders
            if mentioned_users:
                if(len(mentioned_users) == 1) and mentioned_users[0] != ctx.author.id:
                    await ctx.send("❌ Vous ne pouvez planifier un rappel en message privé que pour vous-même.", ephemeral=True)
                    return
            # Check if the user has permission to mention others
                if not ctx.author.guild_permissions.mention_everyone:
                    await ctx.send("❌ Vous n'avez pas la permission de mentionner d'autres utilisateurs", ephemeral=True)
                    return
            else:
                #If no specific users are mentioned, check if the user has permission to mention @everyone
                if not ctx.author.guild_permissions.mention_everyone:
                    await ctx.send("❌ Vous n'avez pas la permission de mentionner @everyone", ephemeral=True)
                    return

            # Parse main event time
            if any(unit in time_spec.lower() for unit in ['minute', 'hour', 'day', 'week', 'min', 'hr', 'm', 'h', 'd', 'w']):
                time_delta = TimeManagement.parse_relative_time(time_spec)
                reminder_datetime = datetime.now() + time_delta
                date = reminder_datetime.strftime("%Y-%m-%d")
                time = reminder_datetime.strftime("%H:%M")
            else:
                try:
                    reminder_datetime = datetime.strptime(time_spec, "%Y-%m-%d %H:%M")
                    date = reminder_datetime.strftime("%Y-%m-%d")
                    time = reminder_datetime.strftime("%H:%M")
                except ValueError:
                    await ctx.send("❌ Format de date/heure invalide. Utilisez YYYY-MM-DD HH:MM ou un temps relatif (ex: 30 minutes)", ephemeral=True)
                    return

            if reminder_datetime < datetime.now():
                await ctx.send("❌ La date et l'heure doivent être dans le futur.", ephemeral=True)
                return

            # Parse reminder times
            reminder_times = []
            for time_str in remind_before.split(','):
                try:
                    delta = TimeManagement.parse_relative_time(time_str.strip())
                    reminder_time = reminder_datetime - delta
                    if reminder_time > datetime.now():
                        reminder_times.append(reminder_time)
                except ValueError as e:
                    await ctx.send(f"❌ Format de rappel invalide : {time_str}", ephemeral=True)
                    return

            # Sort reminder times chronologically
            reminder_times.sort()

            # Set up reminder data
            reminder_id = str(uuid.uuid4())
            channel_id = None if is_dm_reminder else ctx.channel.id
        
            reminder = {
                "id": reminder_id,
                "user_id": ctx.author.id,
                "username": ctx.author.name,
                "channel_id": channel_id,
                "title": title,
                "description": description,
                "date": date,
                "time": time,
                "mentions": mentioned_users if is_dm_reminder else (mentioned_users if mentioned_users else "everyone"),
                "is_dm": is_dm_reminder,
                "reminder_times": [rt.isoformat(' ') for rt in reminder_times],
                "main_time": reminder_datetime.isoformat(' ')
            }

            reminders = load_reminders()
            reminders.append(reminder)
            save_reminders(reminders)

            # Format response message
            time_until = reminder_datetime - datetime.now()
            formatted_time = self.format_time_until(time_until)

            reminder_times_text = "\n".join([
                f"⏰ Rappel dans {self.format_time_until(rt - datetime.now())}"
                for rt in reminder_times
            ])

            if is_dm_reminder:
                # For DM reminders, send confirmation only to the author and mentioned user
                target_user = ctx.guild.get_member(mentioned_users[0])
                response = (
                    f"✅ Rappel privé planifié : {title}\n\n"
                    f"📅 Date : {date} à {time}\n\n"
                    f"⏳ Dans environ {formatted_time}\n\n"
                    f"Rappels programmés :\n\n{reminder_times_text}\n\n"
                    f"👤 Message privé à {target_user.mention}\n\n"
                    f"📢 Les rappels seront envoyés en message privé"
                )
                if description:
                    response += f"\n\n📝 Description : {description}"
            
                # Send ephemeral confirmation to command author
                await ctx.send(response, ephemeral=True)
            else:
                # For channel reminders, send public confirmation
                notification_text = f"👥 Notification : {', '.join(f'<@{uid}>' for uid in mentioned_users) if mentioned_users else '@everyone'}"
                response = (
                    f"✅ Événement planifié : {title}\n\n"
                    f"📅 Date : {date} à {time}\n\n"
                    f"⏳ Dans environ {formatted_time}\n\n"
                    f"Rappels programmés :\n{reminder_times_text}\n\n"
                    f"{notification_text}\n\n"
                    f"📢 Les rappels seront envoyés dans ce canal"
                )
                if description:
                    response += f"\n\n📝 Description : {description}"
                await ctx.send(response)

        except discord.Forbidden:
            await ctx.send("❌ Je n'ai pas les permissions nécessaires pour effectuer cette action.", ephemeral=True)
        except ValueError as ve:
            await ctx.send(f"❌ {str(ve)}", ephemeral=True)
        except Exception as e:
            await ctx.send("❌ Une erreur est survenue.", ephemeral=True)
            print(f"Erreur : {e}")

    @schedule.error
    async def schedule_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette commande.")
        else:
            await ctx.send("❌ Une erreur est survenue lors de l'exécution de la commande.")

    async def send_reminder(self, reminder, isMain = False):
        """Helper function to send the reminder with time left"""
        try:
            if(not isMain):
        # Calculate time left until the event
                reminder_datetime = datetime.fromisoformat(reminder["main_time"])
                time_left = reminder_datetime - datetime.now()
                time_left_str = self.format_time_until(time_left)

        # Prepare the reminder message with time left
                reminder_message = (
                f"⏰ Rappel: {reminder['title']}\n\n"
                )
            else:
                reminder_message = (
                    f"⏰ The event: {reminder['title']} starts now\n\n"
                )
            if(reminder.get('description')):
                reminder_message += f"📝 Description: {reminder.get('description')}\n\n"
            if(not isMain):
                reminder_message+= f"⏳ Temps restant: {time_left_str}\n\n"
            

            if reminder["is_dm"] and len(reminder["mentions"]) == 1:
                # Send DM
                user = self.bot.get_user(reminder["mentions"][0])
                if user:
                    await user.send(reminder_message)
            else:
                # Send to channel
                channel = self.bot.get_channel(reminder["channel_id"])
                if channel:
                    mentions = " ".join(f"<@{uid}>" for uid in reminder['mentions']) if isinstance(reminder['mentions'], list) else "@everyone"
                    reminder_message += "\n"
                    await channel.send(f"{reminder_message}\n{mentions}\n\n")
        except Exception as e:
            print(f"Erreur lors de l'envoi du rappel: {e}")

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
                reminder_datetime = datetime.fromisoformat(reminder["main_time"])
                time_until = reminder_datetime - datetime.now()
                response += (
                    f"{i}. **{reminder['title']}**\n\n"
                    f"📅 {reminder['date']} à {reminder['time']}\n\n"
                    f"⏰ Dans {self.format_time_until(time_until)}\n\n"
                    f"📝 Description: {reminder.get('description', 'Aucune description')}\n\n"
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