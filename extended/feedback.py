import os
import json
import uuid
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from discord.ui import View ,Button
from discord.ui import Button
from discord.ext import commands
import discord

class StarRatingView(View):
    """
    A Discord view for star-based feedback ratings.
    """
    def __init__(self, ctx, category, description):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.category = category
        self.description = description
        self.rating = None

    async def on_timeout(self):
        await self.ctx.send("⏰ Feedback submission timed out. Please try again.")

    @discord.ui.button(label="⭐", style=discord.ButtonStyle.secondary)
    async def one_star(self, interaction: discord.Interaction, button: Button):
        await self.handle_rating(interaction, 1)

    @discord.ui.button(label="⭐⭐", style=discord.ButtonStyle.secondary)
    async def two_stars(self, interaction: discord.Interaction, button: Button):
        await self.handle_rating(interaction, 2)

    @discord.ui.button(label="⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def three_stars(self, interaction: discord.Interaction, button: Button):
        await self.handle_rating(interaction, 3)

    @discord.ui.button(label="⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def four_stars(self, interaction: discord.Interaction, button: Button):
        await self.handle_rating(interaction, 4)

    @discord.ui.button(label="⭐⭐⭐⭐⭐", style=discord.ButtonStyle.secondary)
    async def five_stars(self, interaction: discord.Interaction, button: Button):
        await self.handle_rating(interaction, 5)

    async def handle_rating(self, interaction: discord.Interaction, rating: int):
        self.rating = rating
        self.stop()

        # Save feedback
        feedback_data = {
            "id": str(uuid.uuid4()),
            "user_id": self.ctx.author.id,
            "username": self.ctx.author.name,
            "category": self.category,
            "description": self.description,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Ensure the feedback.json file exists
            if not os.path.exists("feedback.json"):
                with open("feedback.json", "w") as f:
                    json.dump([], f)  # Initialize with an empty list

            # Load existing feedback
            with open("feedback.json", "r") as f:
                feedback_list = json.load(f)

            # Append new feedback
            feedback_list.append(feedback_data)

            # Save updated feedback
            with open("feedback.json", "w") as f:
                json.dump(feedback_list, f, indent=4)

            await interaction.response.send_message(
                f"✅ Thank you for your feedback! You rated **{rating} stars** for **{self.category}**."
            )
        except Exception as e:
            await interaction.response.send_message("❌ An error occurred while saving your feedback.")
            print(f"Error saving feedback: {e}")
            print(f"Feedback data: {feedback_data}")

class FeedbackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(
        name="feedback",
        description="Submit feedback about the bot."
    )
    @app_commands.describe(
        category="The category of feedback (e.g., reminder, scheduling, time-management, general)",
        description="Your feedback description"
    )
    async def feedback(self, ctx, category: str, *, description: str):
        """
        Command to submit feedback about the bot.
        """
        VALID_CATEGORIES = ["reminder", "scheduling", "time-management", "general"]

        if category.lower() not in VALID_CATEGORIES:
            await ctx.send(f"❌ Invalid category. Please choose from: {', '.join(VALID_CATEGORIES)}.")
            return

        # Send star rating view
        view = StarRatingView(ctx, category, description)
        await ctx.send(
            f"🌟 Please rate your experience with **{category}** (1-5 stars):",
            view=view
        )

    @commands.hybrid_command(
        name="view_feedback",
        description="View feedback submitted by users. Optionally filter by category."
    )
    @commands.has_permissions(administrator=True)  # Restrict to admins
    @app_commands.describe(
        category="Filter feedback by category (e.g., reminder, scheduling, time-management, general)"
        ,analyze="option to analyze previous feedbacks, defaults to false , to turn it to true type true"
    )
    async def view_feedback(self, ctx, category: str = None, analyze : str  = ""):
        """
        Command to view feedback and optionally analyze it.
        """
        # Check if the user included the 'analyze' flag
        analyze = analyze.lower()

        try:
            # Check if the feedback file exists
            if not os.path.exists("feedback.json"):
                with open("feedback.json", "w") as f:
                    json.dump([], f)  # Initialize with an empty list

            try:
                # Load feedback from the file
                with open("feedback.json", "r") as f:
                    feedback_list = json.load(f)
            except json.JSONDecodeError:
                await ctx.send("❌ The feedback file is corrupted. Resetting it.", ephemeral=True)
                with open("feedback.json", "w") as f:
                    json.dump([], f)
                feedback_list = []

            if not feedback_list:
                await ctx.send("No feedback has been submitted yet.", ephemeral=True)
                return

            # Filter feedback by category
            if category:
                feedback_list = [fb for fb in feedback_list if fb['category'].lower() == category.lower()]
            if not feedback_list:
                await ctx.send(f"No feedback found for category: {category}.", ephemeral=True)
                return

            response = f"**Feedback Submitted{' (' + category + ')' if category else ''}:**\n\n"
            for feedback in feedback_list:
                response += (
                    f"⭐ **Rating:** {feedback['rating']} stars\n"
                    f"📋 **Category:** {feedback['category']}\n"
                    f"📝 **Description:** {feedback['description']}\n"
                    f"👤 **User:** {feedback['username']} (ID: {feedback['user_id']})\n"
                    f"🕒 **Timestamp:** {feedback['timestamp']}\n"
                    f"────────────────────\n"
                )

            # Send the feedback (split into multiple messages if too long)
            if len(response) <= 2000:
                await ctx.send(response, ephemeral=True)
            else:
                # Split the response into chunks of 2000 characters (Discord message limit)
                for i in range(0, len(response), 2000):
                    await ctx.send(response[i:i+2000], ephemeral=True)

            # Perform feedback analysis if analyze=True
            if analyze == "true":
                analysis_response = self.analyze_feedback(feedback_list, category)
                await ctx.send(analysis_response, ephemeral=True)

        except Exception as e:
            await ctx.send("❌ An error occurred while fetching feedback.", ephemeral=True)
            print(f"Error viewing feedback: {e}")

    
    def analyze_feedback(self, feedback_list, category=None):
        """
        Analyze feedback data and return a summary.
        """
        if not feedback_list:
            return "No feedback data to analyze."

        # Calculate average rating
        total_ratings = sum(fb['rating'] for fb in feedback_list)
        average_rating = total_ratings / len(feedback_list)

        # Count feedback by category
        category_counts = {}
        for fb in feedback_list:
            cat = fb['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1

        most_common_category = max(category_counts, key=category_counts.get)

        # Sentiment analysis
        positive_words = ["good", "great", "excellent", "awesome", "love", "happy", "amazing", "helpful"]
        negative_words = ["bad", "poor", "terrible", "hate", "unhappy", "disappointing", "slow", "not working"]

        positive_count = 0
        negative_count = 0
        for fb in feedback_list:
            description = fb['description'].lower()
            positive_count += sum(description.count(word) for word in positive_words)
            negative_count += sum(description.count(word) for word in negative_words)

        analysis_response = (
            f"📊 **Feedback Analysis{' (' + category + ')' if category else ''}:**\n\n"
            f"⭐ **Average Rating:** {average_rating:.2f} stars\n"
            f"📋 **Most Common Category:** {most_common_category} ({category_counts[most_common_category]} entries)\n"
            f"😊 **Positive Sentiment Words:** {positive_count}\n"
            f"😠 **Negative Sentiment Words:** {negative_count}\n"
        )

        return analysis_response

    async def setup(bot):
        """
        Setup function to add the FeedbackCog to the bot.
        """
        await bot.add_cog(FeedbackCog(bot))