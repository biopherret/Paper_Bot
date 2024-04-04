import discord
from discord_slash import SlashCommand # Importing the newly installed library.

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True) # Declares slash commands through the client.

discord_token = open("discord_token.txt", "r").read()

@client.event
async def on_ready():
    print("Ready!")

@slash.slash(name="ping")
async def _ping(ctx): # Defines a new "context" (ctx) command called "ping."
    await ctx.send(f"Pong! ({client.latency*1000}ms)")

client.run(discord_token)
