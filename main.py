import discord
from discord_slash import SlashCommand # Importing the newly installed library.
from discord_slash.utils.manage_commands import create_option

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True) # Declares slash commands through the client.

discord_token = open("discord_token.txt", "r").read()

@client.event
async def on_ready():
    print("Ready!")

@slash.slash(name="Set Topic Interests", description="Set the topics of papers you want Paper Bot to find for you", 
             options=[
                 create_option(name = 'Topic 1', option_type = 3, required = True),
                    create_option(name = 'Topic 2', option_type = 3, required = False),
                    create_option(name = 'Topic 3', option_type = 3, required = False),
                    create_option(name = 'Topic 4', option_type = 3, required = False),
                    create_option(name = 'Topic 5', option_type = 3, required = False),
             ])
async def _set_topic_interests(ctx): # Defines a new "context" (ctx) command called "ping."
    await ctx.send(f"Pong! ({client.latency*1000}ms)")

client.run(discord_token)
