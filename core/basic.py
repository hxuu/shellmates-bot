def setup(bot):
    # Un simple exemple de hybrid_command
    @bot.hybrid_command()
    async def hello(ctx):
        await ctx.send('Hello, world!')

    @bot.hybrid_command()
    async def ping(ctx):
        await ctx.send('Pong!')

    @bot.hybrid_command()
    async def say(ctx, *, message):
        await ctx.send(message)
        
from predict import predict_best_reminder_time

@bot.command(name="best_time")
async def best_time(ctx):
    best_hour = predict_best_reminder_time()
    await ctx.send(f"📢 Le meilleur moment pour ton rappel est **{best_hour}:00** !")
