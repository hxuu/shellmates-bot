import uuid
import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from utils.reminders import load_reminders, save_reminders
from utils.time_manager import *
from utils.google_calendar import GoogleCalendarManager
from discord import app_commands
from prophet import Prophet
import pandas as pd
import numpy as np
from collections import defaultdict
from discord.ext import tasks
import json
class ActivityTracker:
    def __init__(self):
        self.activity_data = defaultdict(list)
        self.message_counts = defaultdict(lambda: defaultdict(int))
        self.presence_data = defaultdict(lambda: defaultdict(int))
        self.synthetic_weight = 1.0
        self.load_activity_data()
    
    def save_activity_data(self):
        """Save message_counts and presence_data to a JSON file."""
        data = {
            'message_counts': {
            str(user_id): {hour_key.isoformat(): count for hour_key, count in hour_counts.items()}
            for user_id, hour_counts in self.message_counts.items()
            },
            'presence_data': {
            str(user_id): {hour_key.isoformat(): count for hour_key, count in hour_counts.items()}
            for user_id, hour_counts in self.presence_data.items()
            },
            'synthetic_weight': self.synthetic_weight
        }
        with open('data/activity_data.json', 'w') as f:
            json.dump(data, f)

    def load_activity_data(self):
        """Load message_counts and presence_data from a JSON file."""
        try:
            with open('data/activity_data.json', 'r') as f:
                data = json.load(f)
                self.message_counts = defaultdict(lambda: defaultdict(int))
                self.presence_data = defaultdict(lambda: defaultdict(int))
            
                # Load message_counts
                for user_id, hour_counts in data.get('message_counts', {}).items():
                    self.message_counts[int(user_id)] = defaultdict(int, {
                        datetime.fromisoformat(hour): count for hour, count in hour_counts.items()
                })
            
                # Load presence_data
                for user_id, hour_counts in data.get('presence_data', {}).items():
                    self.presence_data[int(user_id)] = defaultdict(int, {
                        datetime.fromisoformat(hour): count for hour, count in hour_counts.items()
                    })
            
                # Load synthetic_weight
                self.synthetic_weight = data.get('synthetic_weight', 1.0)
        except FileNotFoundError:
            print("File not found, starting with fresh activity data.")
        except json.JSONDecodeError:
            print("Error decoding JSON, starting with fresh activity data.")
        except Exception as e:
            print(f"Error loading activity data: {e}, starting with fresh activity data.")
    
    def generate_synthetic_data(self, days=30):
        """Generate synthetic activity data based on common Discord usage patterns"""
        now = datetime.now()
        start_date = now - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=now, freq='H')
        
        synthetic_data = []
        for date in dates:
            score = 0.5  # Base activity score
            
            # Time of day patterns
            hour = date.hour
            if 9 <= hour <= 23:  # Active hours
                score += 0.3
                if 17 <= hour <= 22:  # Peak evening hours
                    score += 0.2
                elif 9 <= hour <= 16:  # Working hours
                    score += 0.1
            else:  # Late night/early morning
                score -= 0.2
                
            # Day of week patterns
            if date.weekday() < 5:  # Weekdays
                score += 0.1
                if date.weekday() in [1, 2, 3]:  # Mid-week boost
                    score += 0.1
            else:  # Weekends
                score += 0.2
                if 13 <= hour <= 22:  # Weekend activity hours
                    score += 0.1
                    
            synthetic_data.append({
                'ds': date,
                'y': max(0.1, min(1.0, score))  # Clamp between 0.1 and 1.0
            })
            
        return pd.DataFrame(synthetic_data)
    
    def add_message(self, user_id, timestamp):
        """Record a message being sent"""
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        self.message_counts[user_id][hour_key] += 1
        # Reduce synthetic data weight as we get real data
        self.synthetic_weight = max(0.2, self.synthetic_weight * 0.995)
        self.save_activity_data()
    
    def add_presence(self, user_id, timestamp, status):
        """Record user presence status"""
        hour_key = timestamp.replace(minute=0, second=0, microsecond=0)
        if status in [discord.Status.online, discord.Status.idle]:
            self.presence_data[user_id][hour_key] += 1
        self.save_activity_data()
    
    def get_hybrid_activity_data(self, days_back=30):
        """Combine synthetic and real activity data"""
        # Get real activity data
        now = datetime.now()
        start_date = now - timedelta(days=days_back)
        
        real_data = []
        for hour_key in pd.date_range(start=start_date, end=now, freq='H'):
            total_messages = sum(self.message_counts[user_id][hour_key] 
                               for user_id in self.message_counts)
            total_presence = sum(self.presence_data[user_id][hour_key] 
                               for user_id in self.presence_data)
            
            # Normalize and combine scores
            message_score = min(1.0, total_messages / max(1, len(self.message_counts)))
            presence_score = min(1.0, total_presence / max(1, len(self.presence_data)))
            activity_score = (0.7 * message_score + 0.3 * presence_score)
            
            real_data.append({
                'ds': hour_key,
                'y': activity_score
            })
        
        real_df = pd.DataFrame(real_data)
        
        # Get synthetic data
        synthetic_df = self.generate_synthetic_data(days=days_back)
        
        # Combine data with weights
        real_weight = 1.0 - self.synthetic_weight
        combined_df = pd.DataFrame({
            'ds': synthetic_df['ds'],
            'y': (synthetic_df['y'] * self.synthetic_weight + 
                 real_df['y'] * real_weight)
        })
        
        return combined_df

class EventTimeSuggester:
    def __init__(self, activity_tracker):
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            interval_width=0.95,
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0
        )
        self.activity_tracker = activity_tracker
        self.last_training = None
    
    def train_model(self):
        """Train the model using hybrid activity data"""
        df = self.activity_tracker.get_hybrid_activity_data()
        if len(df) > 0:
            self.model = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=True,
                daily_seasonality=True
            )
            self.model.fit(df)
            self.last_training = datetime.now()
        
    def get_time_suggestions(self, start_date=None, num_suggestions=3):
        """Get suggested meeting times based on hybrid activity patterns"""
        if (self.last_training is None or 
            datetime.now() - self.last_training > timedelta(hours=6)):
            self.train_model()
            
        if start_date is None:
            start_date = datetime.now()
            
        future_dates = pd.date_range(
            start=start_date,
            end=start_date + timedelta(days=7),
            freq='30min'
        )
        future_df = pd.DataFrame({'ds': future_dates})
        
        forecast = self.model.predict(future_df)
        best_times = forecast.sort_values('yhat', ascending=False)
        
        # Filter for reasonable hours (8 AM - 10 PM)
        best_times = best_times[
            (best_times.ds.dt.hour >= 8) & 
            (best_times.ds.dt.hour <= 22)
        ]
        
        suggestions = []
        for _, row in best_times.head(num_suggestions).iterrows():
            time = row['ds'].to_pydatetime()
            score = row['yhat']
            
            # Get active users count and their activity scores
            active_users, user_scores = self._get_active_users_count(time)
            synthetic_weight = self.activity_tracker.synthetic_weight
            
            suggestions.append((
                time, 
                score, 
                active_users, 
                synthetic_weight,
                user_scores
            ))
            
        return suggestions
    
    def _get_active_users_count(self, time):
        """
        Get a sophisticated count of typically active users at a specific time.
        
        Uses multiple activity signals:
        1. Message frequency
        2. Presence status
        3. Time of day patterns
        4. Weighted scoring
        """
        hour_key = time.replace(minute=0, second=0, microsecond=0)
        day_of_week = time.weekday()
        hour = time.hour

        # Combine multiple activity signals
        active_users = 0
        user_activity_scores = {}

        for user_id in self.activity_tracker.message_counts:
            # Message frequency weight
            message_count = self.activity_tracker.message_counts[user_id].get(hour_key, 0)
            
            # Presence status weight
            presence_count = self.activity_tracker.presence_data[user_id].get(hour_key, 0)
            
            # Time of day pattern weight
            time_of_day_score = self._calculate_time_of_day_score(hour, day_of_week)
            
            # Combine weights
            total_score = (
                message_count * 0.4 +  # Message frequency
                presence_count * 0.3 +  # Online presence
                time_of_day_score * 0.3  # Time of day pattern
            )
            
            # Only count users with meaningful activity
            if total_score > 0.5:
                active_users += 1
                user_activity_scores[user_id] = total_score
        
        return active_users, user_activity_scores

    def _calculate_time_of_day_score(self, hour, day_of_week):
        """
        Calculate an activity score based on time of day and day of week.
        Provides a base activity prediction even without direct data.
        """
        # Base scores for different hours and days
        hour_scores = {
            # Peak working hours on weekdays
            (9, 17): 0.8 if 0 <= day_of_week <= 4 else 0.2,
            # Evening hours
            (17, 22): 0.9 if 0 <= day_of_week <= 6 else 0.5,
            # Late night/early morning
            (22, 9): 0.1
        }
        
        # Find the appropriate score range
        for (start, end), score in hour_scores.items():
            if start <= hour < end:
                return score
        
        return 0.2  # Default low score

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
        self.activity_tracker = ActivityTracker()
        self.time_suggester = EventTimeSuggester(self.activity_tracker)
        self.track_activity.start()

    def cog_unload(self):
        self.activity_tracker.cancel()
    
    @tasks.loop(minutes=5)
    async def track_activity(self):
        """Track user activity periodically"""
        for guild in self.bot.guilds:
            for member in guild.members:
                self.activity_tracker.add_presence(
                    member.id,
                    datetime.now(),
                    member.status
                )

    @commands.Cog.listener()
    async def on_message(self, message):
        """Track message activity"""
        if message.author.bot:
            return
        self.activity_tracker.add_message(
            message.author.id,
            message.created_at
        )

    @commands.hybrid_command(
    name="suggest_times",
    description="🕒 Get smart suggestions for the best meeting times"
)
    async def suggest_times(self, ctx, start_date: str = None):
        """Get suggestions for optimal meeting times."""
        try:
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError:
                    await ctx.send("❌ Invalid date format. Please use YYYY-MM-DD", ephemeral=True)
                    return
            else:
                start_dt = datetime.now()

            suggestions = self.time_suggester.get_time_suggestions(start_dt)
        
            response = "📊 **Smart meeting time suggestions:**\n\n"
            for time, score, active_users, synthetic_weight, user_scores in suggestions:
                confidence = int(score * 100)
                data_source = (f"({int(synthetic_weight * 100)}% pre-defined patterns, "
                         f"{int((1-synthetic_weight) * 100)}% server activity)")
            
                # Top 3 most active users (if available)
                top_users = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:3]
                top_users_str = ", ".join([f"<@{uid}>" for uid, _ in top_users]) if top_users else "No specific users"
            
                response += (
                f"📅 {time.strftime('%Y-%m-%d %H:%M')}\n"
                f"👥 Typically active users: {active_users}\n"
                f"💫 Top active members: {top_users_str}\n"
                f"📊 Activity score: {confidence}%\n"
                f"📈 Based on: {data_source}\n\n"
                )
        
            await ctx.send(response)
        
        except Exception as e:
            await ctx.send("❌ An error occurred while getting time suggestions.", ephemeral=True)
            print(f"Error in suggest_times: {e}")
            
        

    @commands.hybrid_command(
        name="view_activity",
        description="📊 View server activity patterns"
        )
    async def view_activity(self, ctx):
        """View current server activity patterns and data weights."""
        try:
            # Get current weights and activity data
            synthetic_weight = self.activity_tracker.synthetic_weight
            real_weight = 1 - synthetic_weight
            
            # Get basic statistics
            total_messages = sum(len(msgs) for msgs in self.activity_tracker.message_counts.values())
            total_users = len(self.activity_tracker.message_counts)
            
            # Get most active hours
            hour_activity = defaultdict(int)
            for user_msgs in self.activity_tracker.message_counts.values():
                for timestamp in user_msgs:
                    hour_activity[timestamp.hour] += user_msgs[timestamp]
                    
            most_active_hours = sorted(
                hour_activity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            
            response = (
                "📊 **Server Activity Analysis**\n\n"
                f"**Data Sources**\n"
                f"Pre-defined patterns: {int(synthetic_weight * 100)}%\n"
                f"Server activity data: {int(real_weight * 100)}%\n\n"
                f"**Statistics**\n"
                f"Total messages tracked: {total_messages}\n"
                f"Active users tracked: {total_users}\n\n"
                f"**Most Active Hours**\n"
            )
            
            for hour, count in most_active_hours:
                response += f"• {hour:02d}:00 - {hour:02d}:59: {count} messages\n"
                
            await ctx.send(response)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while analyzing activity patterns.", ephemeral=True)
            print(f"Error in view_activity: {e}")

    @commands.hybrid_command(
        name="clear_activity",
        description="🗑️ Clear stored activity data"
    )
    @commands.has_permissions(administrator=True)
    async def clear_activity(self, ctx):
        """Clear all stored activity data and reset weights."""
        try:
            # Reset all activity data
            self.activity_tracker.message_counts.clear()
            self.activity_tracker.presence_data.clear()
            self.activity_tracker.synthetic_weight = 1.0
            
            await ctx.send("✅ Activity data has been cleared and weights reset to default.")
            
        except Exception as e:
            await ctx.send("❌ An error occurred while clearing activity data.", ephemeral=True)
            print(f"Error in clear_activity: {e}")

    @commands.hybrid_command(
        name="set_weights",
        description="⚖️ Adjust activity prediction weights"
    )
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        synthetic_weight="Weight for pre-defined patterns (0-100)"
    )
    async def set_weights(self, ctx, synthetic_weight: int):
        """Manually adjust the weights between synthetic and real data."""
        try:
            if not 0 <= synthetic_weight <= 100:
                await ctx.send("❌ Weight must be between 0 and 100.", ephemeral=True)
                return
                
            self.activity_tracker.synthetic_weight = synthetic_weight / 100.0
            
            response = (
                "⚖️ **Weights Updated**\n\n"
                f"Pre-defined patterns: {synthetic_weight}%\n"
                f"Server activity data: {100 - synthetic_weight}%"
            )
            
            await ctx.send(response)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while updating weights.", ephemeral=True)
            print(f"Error in set_weights: {e}")

    @commands.hybrid_command(
        name="schedule_recurring",
        description="🔄 Schedule a recurring meeting"
    )
    @app_commands.describe(
        title="Meeting title",
        frequency="daily, weekly, or monthly",
        initial_time="YYYY-MM-DD HH:MM format"
    )
    async def schedule_recurring(self, ctx, title: str, frequency: str, initial_time: str):
        """Schedule a recurring meeting with smart time suggestions."""
        try:
            # Validate frequency
            valid_frequencies = ['daily', 'weekly', 'monthly']
            if frequency.lower() not in valid_frequencies:
                await ctx.send("❌ Invalid frequency. Use: daily, weekly, or monthly", ephemeral=True)
                return
                
            # Parse initial time
            try:
                start_time = datetime.strptime(initial_time, "%Y-%m-%d %H:%M")
            except ValueError:
                await ctx.send("❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True)
                return
                
            # Get suggestions near the specified time
            suggestions = self.time_suggester.get_time_suggestions(start_time)
            
            response = (
                f"🔄 **Recurring Meeting: {title}**\n\n"
                f"Frequency: {frequency}\n"
                f"Initial time: {initial_time}\n\n"
                "Suggested optimized times:\n\n"
            )
            
            for time, score, active_users, synthetic_weight in suggestions:
                confidence = int(score * 100)
                response += (
                    f"📅 {time.strftime('%Y-%m-%d %H:%M')}\n"
                    f"👥 Typically active users: {active_users}\n"
                    f"💫 Activity score: {confidence}%\n\n"
                )
                
            response += (
                "To confirm, use:\n"
                f"`/schedule {title} YYYY-MM-DD HH:MM`\n"
                "with your chosen time from the suggestions."
            )
            
            await ctx.send(response)
            
        except Exception as e:
            await ctx.send("❌ An error occurred while scheduling recurring meeting.", ephemeral=True)
            print(f"Error in schedule_recurring: {e}")

    # Error handlers
    @suggest_times.error
    @view_activity.error
    @clear_activity.error
    @set_weights.error
    @schedule_recurring.error
    async def command_error(self, ctx, error):
        """Generic error handler for all commands."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.", ephemeral=True)
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Invalid argument provided.", ephemeral=True)
        else:
            await ctx.send("❌ An error occurred while processing the command.", ephemeral=True)
            print(f"Command error: {error}")

    

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
    description="📅 Schedule a custom reminder with optional early reminders"
)
    @app_commands.describe(
    title="Title of the meeting", 
    time_spec="YYYY-MM-DD HH:MM or relative time like 15m 13h",
    remind_before="e.g., 10m, default: 5 minutes",
    mentions="Users or roles to mention",
    add_to_calendar="Add event to Google Calendar",
    duration="Event duration",
    channel_id="Specific channel ID to send reminder (optional)"
    )
    @commands.has_permissions(mention_everyone=True)
    async def schedule(
    self,
    ctx,
    title: str,
    time_spec: str,
    remind_before: str = "5m",
    description: str = None,
    mentions: str = None,
    add_to_calendar: bool = False,
    duration: str = "1h",
    channel_id: str = None
    ):
        try:
            from utils.user_data import get_user_emails

            # Validate and set channel
            target_channel = (
            self.bot.get_channel(int(channel_id)) 
            if channel_id 
            else ctx.channel
        )
        
            if not target_channel:
                await ctx.send("❌ Invalid channel ID provided.", ephemeral=True)
                return

            # Check permissions for mentions
            if mentions:
                mentioned_users = []
                mention_parts = mentions.split()
                for mention in mention_parts:
                    user_id = ''.join(filter(str.isdigit, mention))
                    if user_id:
                        mentioned_users.append(int(user_id))
            else:
                mentioned_users = []
        
            is_dm_reminder = len(mentioned_users) == 1

            if mentioned_users:
                if(len(mentioned_users) == 1) and mentioned_users[0] != ctx.author.id:
                    await ctx.send("❌ You can only schedule a private reminder for yourself.", ephemeral=True)
                    return

                if not ctx.author.guild_permissions.mention_everyone:
                    await ctx.send("❌ You do not have permission to mention other users", ephemeral=True)
                    return
            else:
                if not ctx.author.guild_permissions.mention_everyone:
                    await ctx.send("❌ You do not have permission to mention @everyone", ephemeral=True)
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
                    await ctx.send("❌ Invalid date/time format. Use YYYY-MM-DD HH:MM or relative time", ephemeral=True)
                    return

            if reminder_datetime < datetime.now():
                await ctx.send("❌ Date and time must be in the future.", ephemeral=True)
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
                    await ctx.send(f"❌ Invalid reminder format: {time_str}", ephemeral=True)
                    return

            # Sort reminder times chronologically
            reminder_times.sort()

            # Set up reminder data
            reminder_id = str(uuid.uuid4())
        
            reminder = {
                "id": reminder_id,
                "user_id": ctx.author.id,
                "username": ctx.author.name,
                "channel_id": target_channel.id,
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
                f"⏰ Reminder in {self.format_time_until(rt - datetime.now())}"
                for rt in reminder_times
            ])

            if is_dm_reminder:
                target_user = ctx.guild.get_member(mentioned_users[0])
                response = (
                f"✅ Private reminder scheduled: {title}\n\n"
                f"📅 Date: {date} at {time}\n\n"
                f"⏳ In approximately {formatted_time}\n\n"
                f"Scheduled reminders:\n\n{reminder_times_text}\n\n"
                f"👤 Private message to {target_user.mention}\n\n"
                f"📢 Reminders will be sent via DM"
            )
                if description:
                    response += f"\n\n📝 Description: {description}"
        
                await ctx.send(response, ephemeral=True)
            else:
                notification_text = f"👥 Notification: {', '.join(f'<@{uid}>' for uid in mentioned_users) if mentioned_users else '@everyone'}"
                response = (
                f"✅ Event scheduled: {title}\n\n"
                f"📅 Date: {date} at {time}\n\n"
                f"⏳ In approximately {formatted_time}\n\n"
                f"Reminders scheduled:\n\n{reminder_times_text}\n\n"
                f"{notification_text}\n\n"
                f"📢 Reminders will be sent in {target_channel.mention}"
            )
                if description:
                    response += f"\n\n📝 Description: {description}"
                await ctx.send(response)
            
            # Google Calendar integration
            if add_to_calendar:
                end_delta = TimeManagement.parse_relative_time(duration)
                end_time = reminder_datetime + end_delta

                # Get attendee emails
                attendee_emails = []
                all_missing = []

                # Add author's email
                author_data = get_user_emails().get(str(ctx.author.id))
                if author_data:
                    attendee_emails.append(author_data['email'])

                if mentioned_users or ctx.message.mention_everyone:
                    # Handle @everyone
                    if ctx.message.mention_everyone:
                        emails, missing = self.get_emails_for_mention(ctx, "everyone")
                        attendee_emails.extend(emails)
                        all_missing.extend(missing)
                
                    # Handle mentioned roles
                    for mention in mention_parts:
                        if mention.startswith('<@&'):
                            emails, missing = self.get_emails_for_mention(ctx, mention)
                            attendee_emails.extend(emails)
                            all_missing.extend(missing)

                # Handle direct user mentions
                for user_id in mentioned_users:
                    user_data = get_user_emails().get(str(user_id))
                    if user_data:
                        attendee_emails.append(user_data['email'])
                    else:
                        user = self.bot.get_user(user_id)
                        all_missing.append(user.name if user else str(user_id))

                # Remove duplicates
                attendee_emails = list(set(attendee_emails))

                # Create calendar event
                event_id = await self.calendar_manager.create_event(
                title=title,
                start_time=reminder_datetime,
                end_time=end_time,
                description=description,
                attendees=attendee_emails
                )

                # Update response with calendar details
                if event_id:
                    await ctx.send(
                        f"📅 Event added to calendars of: {len(attendee_emails)} participants",
                        ephemeral=True
                    )
                
                if all_missing:
                    await ctx.send(
                        f"⚠️ These users/roles have no registered email: {', '.join(all_missing)}",
                        ephemeral=True
                    )

        except discord.Forbidden:
            await ctx.send("❌ I do not have the necessary permissions to perform this action.", ephemeral=True)
        except ValueError as ve:
            await ctx.send(f"❌ {str(ve)}", ephemeral=True)
        except Exception as e:
            await ctx.send("❌ An error happend.", ephemeral=True)
            print(f"Error: {e}")

    @schedule.error
    async def schedule_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have the required permissions to execute this command.")
        else:
            await ctx.send("❌  An error happened when executing the command.")

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
                f"⏰ Reminder: {reminder['title']}\n\n"
                )
            else:
                reminder_message = (
                    f"⏰ The event: {reminder['title']} starts now\n\n"
                )
            if(reminder.get('description')):
                reminder_message += f"📝 Description: {reminder.get('description')}\n\n"
            if(not isMain):
                reminder_message+= f"⏳ Remaining time: {time_left_str}\n\n"
            

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
                    await channel.send(f"{reminder_message}{mentions}")
        except Exception as e:
            print(f"An error happened when sending the reminder: {e}")

    @commands.hybrid_command(
        name="reminders",
        description="List the current reminders."
    )
    async def reminders(self, ctx):
        try:
            reminders = load_reminders()
            user_reminders = [r for r in reminders if r["user_id"] == ctx.author.id]

            if not user_reminders:
                await ctx.send("You don't have any reminders")
                return

            user_reminders.sort(key=lambda r: f"{r['date']} {r['time']}")
            response = "**Your current reminders :**\n\n"
            for i, reminder in enumerate(user_reminders, start=1):
                reminder_datetime = datetime.fromisoformat(reminder["main_time"])
                time_until = reminder_datetime - datetime.now()
                response += (
                    f"{i}. **{reminder['title']}**\n\n"
                    f"📅 {reminder['date']} at {reminder['time']}\n\n"
                    f"⏰ In {self.format_time_until(time_until)}\n\n"
                    f"📝 Description: {reminder.get('description', 'No description')}\n\n"
                    f"🆔 ID : {reminder['id']}\n\n"
                )
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ An error happened.")
            print(f"Erreur : {e}")

    @commands.hybrid_command(
        name="delete",
        description="Delete a specific reminder using its ID"
    )
    @app_commands.describe(
        reminder_id ="The reminder's ID , You can find it using the command reminders"
    )
    async def delete(self, ctx, reminder_id: str):
        try:
            reminders = load_reminders()
            reminder_to_delete = next((r for r in reminders if r["id"] == reminder_id and r["user_id"] == ctx.author.id), None)

            if not reminder_to_delete:
                await ctx.send("❌ No reminder using this ID is found.")
                return

            reminders.remove(reminder_to_delete)
            save_reminders(reminders)
            await ctx.send(f"✅ Deleted reminder : **{reminder_to_delete['title']}** (ID : {reminder_id})")

        except Exception as e:
            await ctx.send("❌ An error happened.")
            print(f"Erreur : {e}")

    @commands.hybrid_command(
        name="check_permissions",
        description="Verify bot permissions."
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
            response = "**Bot permissions in this channel :**\n" + "\n".join(
                f"{'✅' if value else '❌'} {perm}" for perm, value in perms_list
            )
            await ctx.send(response)
        except Exception as e:
            await ctx.send("❌ An error happened.")
            print(f"Erreur : {e}")
            
    @commands.hybrid_command(
        name="register_email",
        description="🔒 Save your google email and roles"
    )
    @app_commands.describe(
        email = "example@gmail.com"
    )
    async def register_email(self, ctx, email: str):
        if '@' not in email or '.' not in email.split('@')[-1]:
            await ctx.send("❌ Invalid email format", ephemeral=True)
            return
        
        # Récupérer les rôles de l'utilisateur (sans @everyone)
        member = ctx.guild.get_member(ctx.author.id)
        roles = [role.id for role in member.roles if role.name != "@everyone"]
        
        from utils.user_data import save_user_email
        save_user_email(ctx.author.id, email, roles)
        await ctx.send("✅ Email and roles saved successfully !", ephemeral=True)