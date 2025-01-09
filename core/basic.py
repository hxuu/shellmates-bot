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
