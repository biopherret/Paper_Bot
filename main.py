import discord
import discord_slash
from discord.ext import commands

import json

import serpapi
import itertools
import os
import pandas as pd
from datetime import date

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.all())
slash = discord_slash.SlashCommand(bot, sync_commands=True) # Declares slash commands through the bot.

discord_token = open("discord_token.txt", "r").read()
serpapi_token = open("serpapi_token.txt", "r").read()

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)

async def getArticles(topics_list, num_papers):
    allArticles = list()
    for topic_dict in topics_list:
        params = {
            "engine": "google_scholar",
            "q": topic_dict['topic'],
            "api_key": serpapi_token,
            "scisbd": topic_dict['recent'],
            "hl": "en"
            }
        search1=serpapi.search(params)
        topicArticles = list()
        n = 0
        for article in range(len(search1)):
            n += 1
            print(search1['organic_results'][article]['title'], search1['organic_results'][article]['link'])
            topicArticles.append(search1['organic_results'][article]['title'])
            if n == num_papers:
                break
        allArticles.append(topicArticles)
    return(allArticles)

@bot.event
async def on_ready():
    print("Ready!")

@slash.slash(name="clear_history", description="Clear all Paper Bot topic settings and articles (remove all previously found papers from history).")
async def _clear_history(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_json.pop(str(author)) #remove the user from the json
    await write_json(topics_json, "topics.json")
    await ctx.send("Your history has been cleared! All topic settings and found articles have been removed.")

@slash.slash(name="clear_topics", description="Clear your saved topic settings.")
async def _clear_topics(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_json[str(author)]['topic_settings'] = [] #empty the topic settings list
    await write_json(topics_json, "topics.json")
    await ctx.send("Topics have been cleared!")

@slash.slash(name="view_topics", description="View your saved topic settings.")
async def _view_topics(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(author)]['topic_settings']
    mes = 'Here are your current topics:'
    for topic_dict in topics_list:
        mes += f"\n{topic_dict['topic']}"
        if topic_dict['recent'] == 1:
            mes += " (recent papers only)"
    await ctx.send(mes)
    
@slash.slash(name="add_topic", description='Add a topic of papers you want Paper Bot to find for you. Use "author: name" to search for authors.', 
             options=[
                 discord_slash.manage_commands.create_option(name = 'topic', option_type = 3, required = True, description = "The topic you are interested in"),
                 discord_slash.manage_commands.create_option(name = 'recent', option_type = 3, required = True, description = "Do you want to restrict the search to papers published in the last year? (y/n)"),
             ])
async def _add_topic(ctx, topic, recent):
    author = ctx.author.id #save topic preferences in json
    topics_json = await open_json("topics.json")
    if str(author) not in topics_json.keys(): #if this user dosn't exist yet
        topics_json[str(author)] = {'topic_settings': [], 'found_articles': []} #create a dictionary object for the new user
        await ctx.send("Welcome to Paper Bot! I've created a new user profile for you.")

    if recent == 'y':
        recent = 1
    else:
        recent = 0

    topics_json[str(author)]['topic_settings'].append({"topic": topic, "recent": recent}) #add the new topic
    await write_json(topics_json, "topics.json")

    await ctx.send("Your new topic has been added!")

@slash.slash(name="find_papers", description="Find papers based on your topic interests",
             options=[
                 discord_slash.manage_commands.create_option(name = 'num_papers', option_type = 4, required = True, description = "The number of papers you want to find for each topic"),
             ])
async def _find_papers(ctx, num_papers):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(author)]

    allArticles = await getArticles(topics_list, num_papers)
    print(allArticles)
    await ctx.send("found some articles, check terminal")

bot.run(discord_token)
