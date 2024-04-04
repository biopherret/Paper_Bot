import discord
from discord_slash import SlashCommand # Importing the newly installed library.
from discord_slash.utils.manage_commands import create_option

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True) # Declares slash commands through the client.

discord_token = open("discord_token.txt", "r").read()

@client.event
async def on_ready():
    print("Ready!")

@slash.slash(name="set_topic_interests", description="Set the topics of papers you want Paper Bot to find for you", 
             options=[
                 create_option(name = 'topic1', option_type = 3, required = True, description = "The first topic you are interested in"),
                    create_option(name = 'topic2', option_type = 3, required = False, description = "The second topic you are interested in"),
                    create_option(name = 'topic3', option_type = 3, required = False, description = "The third topic you are interested in"),
                    create_option(name = 'topic4', option_type = 3, required = False, description = "The fourth topic you are interested in"),
                    create_option(name = 'topic5', option_type = 3, required = False, description = "The fifth topic you are interested in"),
             ])
async def _set_topic_interests(ctx): # Defines a new "context" (ctx) command called "ping."
    await ctx.send(Topic1)

client.run(discord_token)
