import discord
import discord_slash
from discord_slash import SlashCommand # Importing the newly installed library.
from discord.ext import commands

import json

import serpapi
import itertools
import os
import pandas as pd
from datetime import date

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True) # Declares slash commands through the bot.

discord_token = open("discord_token.txt", "r").read()
serpapi_token = open("serpapi_token.txt", "r").read()

wd=os.getcwd()

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)

async def getArticles(listofTopics):
    allArticles = list()
    if(len(listofTopics) > 1):
        for topic in listofTopics:
            params = {
              "engine": "google_scholar",
              "q": topic,
              "api_key": serpapi_token,
                "scisbd": 1
            }
            search1=serpapi.search(params)
            topicArticles = list()
            for article in range(len(search1)):
                topicArticles.append(search1['organic_results'][article]['title'])
            allArticles.append(topicArticles)
        return(allArticles)

@bot.event
async def on_ready():
    print("Ready!")

@slash.slash(name="set_topic_interests", description="Set the topics of papers you want Paper Bot to find for you", 
             options=[
                 discord_slash.manage_commands.create_option(name = 'topic1', option_type = 3, required = True, description = "The first topic you are interested in"),
                    discord_slash.manage_commands.create_option(name = 'topic2', option_type = 3, required = False, description = "The second topic you are interested in"),
                    discord_slash.manage_commands.create_option(name = 'topic3', option_type = 3, required = False, description = "The third topic you are interested in"),
                    discord_slash.manage_commands.create_option(name = 'topic4', option_type = 3, required = False, description = "The fourth topic you are interested in"),
                    discord_slash.manage_commands.create_option(name = 'topic5', option_type = 3, required = False, description = "The fifth topic you are interested in"),
             ])
async def _set_topic_interests(ctx, topic1, topic2 = None, topic3 = None, topic4 = None, topic5 = None): # Defines a new "context" (ctx) command called "ping."
    topic_list = [topic1, topic2, topic3, topic4, topic5]
    while None in topic_list:
        topic_list.remove(None) #remove empty topics from list

    author = ctx.author.id #save topic preferences in json
    topics_json = await open_json("topics.json")
    topics_json[str(author)] = topic_list
    await write_json(topics_json, "topics.json")
    await ctx.send("Topics have been set!")

@slash.slash(name="find_papers", description="Find papers based on your topic interests") 
async def _find_papers(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics = topics_json[str(author)]

    allArticles = await getArticles(topics)
    await ctx.send(allArticles)

bot.run(discord_token)
