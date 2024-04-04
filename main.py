import discord
from discord_slash import SlashCommand # Importing the newly installed library.

client = discord.Client(intents=discord.Intents.all())
slash = SlashCommand(client, sync_commands=True) # Declares slash commands through the client.

secret_token = 'MTIyNTIzMDE2ODU5NjE1NjYxOQ.GJ28VQ.vX9X1aJs8UlPhMRgODAWl45TnhLiTBipuvYO7w'

@client.event
async def on_ready():
    print("Ready!")

client.run(secret_token)