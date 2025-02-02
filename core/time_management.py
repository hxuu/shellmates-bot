import uuid
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from utils.reminders import load_reminders, save_reminders
from utils.time_manager import *
from utils.google_calendar import GoogleCalendarManager


async def setup(bot):
    """
    Configurer le Cog de gestion du temps pour le bot.
    """
    await bot.add_cog(TimeManagementCog(bot))

class TimeManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_notifications = set()
        self.calendar_manager = GoogleCalendarManager()
        self.calendar_manager.authenticate()


    async def cog_load(self):
        """
        Méthode appelée lorsque le Cog est chargé. Démarre la vérification des rappels.
        """
        self.bot.loop.create_task(self.check_reminders())

    async def check_reminders(self):
        """
        Enhanced background task for checking reminders.
        """
        print("Reminder checker started!")
        await self.bot.wait_until_ready()
        
        # Initialize notifications cache with TTL
        from collections import OrderedDict
        self.sent_notifications = OrderedDict()
        NOTIFICATION_TTL = 3600  # 1 hour TTL for sent notifications
        
        # Add metrics tracking
        metrics = {
            'processed_reminders': 0,
            'sent_notifications': 0,
            'errors': 0,
            'cleanup_operations': 0
        }

        while True:
            try:
                current_time = datetime.now()
                reminders = load_reminders()
                reminders_to_remove = []
                modified_reminders = []

                # Batch process reminders
                for reminder in reminders:
                    try:
                        # Add reminder status tracking
                        reminder_status = {
                            'id': reminder['id'],
                            'processing_started': datetime.now(),
                            'notifications_sent': 0,
                            'errors': []
                        }

                        reminder_datetime = datetime.fromisoformat(reminder["main_time"])
                        time_until_reminder = reminder_datetime - current_time

                        # Optimize old reminder cleanup
                        if time_until_reminder.total_seconds() < -300:  # 5 minutes past
                            reminders_to_remove.append(reminder)
                            continue

                        # Process reminder times more efficiently
                        all_times = [(reminder_datetime, 'main')] + [
                            (datetime.fromisoformat(rt), 'early') 
                            for rt in reminder.get("reminder_times", [])
                        ]

                        for check_time, reminder_type in all_times:
                            time_until = check_time - current_time
                            seconds_until = time_until.total_seconds()

                            # Skip if too far in future or too old
                            if seconds_until > 3600:  # More than 1 hour away
                                continue
                            if seconds_until < -30:  # More than 30 seconds old
                                continue

                            notification_key = f"{reminder['id']}_{check_time.isoformat()}"
                            
                            # More precise timing window
                            if -1 <= seconds_until <= 3 and notification_key not in self.sent_notifications:
                                try:
                                    await self.send_reminder(reminder, reminder_type == 'main')
                                    self.sent_notifications[notification_key] = current_time
                                    reminder_status['notifications_sent'] += 1
                                    metrics['sent_notifications'] += 1
                                    
                                    # Cleanup old notification keys
                                    while len(self.sent_notifications) > 1000:  # Prevent unlimited growth
                                        self.sent_notifications.popitem(last=False)
                                        
                                except Exception as e:
                                    reminder_status['errors'].append(str(e))
                                    metrics['errors'] += 1
                                    continue

                        # Update reminder if modified
                        if reminder.get('modified'):
                            modified_reminders.append(reminder)
                            
                        metrics['processed_reminders'] += 1

                    except Exception as e:
                        print(f"Error processing reminder {reminder.get('id', 'unknown')}: {e}")
                        metrics['errors'] += 1
                        continue

                # Batch update reminders
                if reminders_to_remove or modified_reminders:
                    new_reminders = [
                        r for r in reminders 
                        if r not in reminders_to_remove
                    ]
                    
                    # Update modified reminders
                    for mod_reminder in modified_reminders:
                        reminder_index = next(
                            (i for i, r in enumerate(new_reminders) 
                            if r['id'] == mod_reminder['id']), 
                            None
                        )
                        if reminder_index is not None:
                            new_reminders[reminder_index] = mod_reminder

                    save_reminders(new_reminders)
                    metrics['cleanup_operations'] += 1

                # Cleanup expired notification keys
                current_time = datetime.now()
                self.sent_notifications = OrderedDict(
                    (k, v) for k, v in self.sent_notifications.items()
                    if (current_time - v).total_seconds() < NOTIFICATION_TTL
                )

                # Log metrics periodically
                if metrics['processed_reminders'] % 100 == 0:
                    print(f"Reminder Checker Metrics: {metrics}")

            except Exception as e:
                print(f"Critical error in reminder checker: {e}")
                metrics['errors'] += 1

            # Adaptive sleep time based on number of active reminders
            sleep_time = min(30, max(5, len(reminders) // 10))
            await asyncio.sleep(sleep_time)

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
    
    def get_emails_for_mention(self, ctx, mention_str: str):
        user_data = get_user_emails()
        emails = []
        missing = []

        # Si mention est @everyone
        if mention_str.lower() == "everyone":
            for uid, data in user_data.items():
                emails.append(data['email'])
            return emails, missing

        # Si mention est un rôle
        if mention_str.startswith('<@&'):
            role_id = ''.join(filter(str.isdigit, mention_str))
            role = ctx.guild.get_role(int(role_id))
            if role:
                for member in role.members:
                    data = user_data.get(str(member.id))
                    if data:
                        emails.append(data['email'])
                    else:
                        missing.append(member.name)
        return emails, missing

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
        ),
        add_to_calendar: bool = commands.param(
            default=False,
            description="Ajouter l'événement à Google Calendar"
        ),
        duration: str = commands.param(
            default="1h",
            description="Durée de l'événement (pour Google Calendar)"
        )
):
        try:  # <- Début du try
            from utils.user_data import get_user_emails
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
                    f"Rappels programmés :\n\n{reminder_times_text}\n\n"
                    f"{notification_text}\n\n"
                    f"📢 Les rappels seront envoyés dans ce canal"
                )
                if description:
                    response += f"\n\n📝 Description : {description}"
                await ctx.send(response)
                
            # Added Google Calendar integration
            if add_to_calendar:
                # Calculate end time based on duration
                end_delta = TimeManagement.parse_relative_time(duration)
                end_time = reminder_datetime + end_delta

                # Convert mentions to email addresses if needed
                # Remplacer la partie actuelle avec :
                attendee_emails = []
                all_missing = []

                # Récupérer l'email de l'auteur
                author_data = get_user_emails().get(str(ctx.author.id))
                if author_data:
                    attendee_emails.append(author_data['email'])

                if mentioned_users or ctx.message.mention_everyone:
                    # Gérer @everyone
                    if ctx.message.mention_everyone:
                        emails, missing = self.get_emails_for_mention(ctx, "everyone")
                        attendee_emails.extend(emails)
                        all_missing.extend(missing)
                    
                    # Gérer les rôles mentionnés
                    for mention in mention_parts:
                        if mention.startswith('<@&'):
                            emails, missing = self.get_emails_for_mention(ctx, mention)
                            attendee_emails.extend(emails)
                            all_missing.extend(missing)

                # Gérer les utilisateurs directs
                for user_id in mentioned_users:
                    user_data = get_user_emails().get(str(user_id))
                    if user_data:
                        attendee_emails.append(user_data['email'])
                    else:
                        user = self.bot.get_user(user_id)
                        all_missing.append(user.name if user else str(user_id))

                # Supprimer les doublons
                attendee_emails = list(set(attendee_emails))

                # Create calendar event
                event_id = await self.calendar_manager.create_event(
                    title=title,
                    start_time=reminder_datetime,
                    end_time=end_time,
                    description=description,
                    attendees=attendee_emails
                )

                # Modifier la réponse finale :
                if event_id:
                    response += "\n\n📅 Événement ajouté aux calendriers de :"
                    response += f"\n- {len(attendee_emails)} participants"
                    
                if all_missing:
                    await ctx.send(
                        f"⚠️ Ces utilisateurs/roles n'ont pas d'email enregistré : {', '.join(all_missing)}",
                        ephemeral=True
                    )

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
                    await channel.send(f"{reminder_message}\n{mentions}")
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
            
    @commands.hybrid_command(
        name="register_email",
        description="🔒 Enregistre ton email Google et tes rôles actuels"
    )
    async def register_email(self, ctx, email: str):
        if '@' not in email or '.' not in email.split('@')[-1]:
            await ctx.send("❌ Format d'email invalide", ephemeral=True)
            return
        
        # Récupérer les rôles de l'utilisateur (sans @everyone)
        member = ctx.guild.get_member(ctx.author.id)
        roles = [role.id for role in member.roles if role.name != "@everyone"]
        
        from utils.user_data import save_user_email
        save_user_email(ctx.author.id, email, roles)
        await ctx.send("✅ Email et rôles enregistrés avec succès !", ephemeral=True)