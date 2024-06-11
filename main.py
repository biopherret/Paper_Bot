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

wd=os.getcwd()

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)
    
async def format_paper_message(topic_list, all_articles):
    message = ""
    for topic in topic_list:
        message += f"**{topic}**\n"
        t = 0
        for article in all_articles[t]:
            message += f"{article}\n"
            t += 1
        message += "\n"
    return message

async def getArticles(listofTopics, num_papers, recents):
    allArticles = list()
    for topic, recent in zip(listofTopics, recents):
        params = {
            "engine": "google_scholar",
            "q": topic,
            "api_key": serpapi_token,
            "scisbd": recent,
            "hl": "en"
            }
        search1=serpapi.search(params)
        topicArticles = list()
        n = 0
        for article in range(len(search1)):
            n += 1
            print(search1['organic_results'][article]['link'])
            topicArticles.append(search1['organic_results'][article]['title'])
            if n == num_papers:
                break
        allArticles.append(topicArticles)
    return(allArticles)

@bot.event
async def on_ready():
    print("Ready!")

@slash.slash(name="clear_topics", description="Clear your saved topic settings.")
async def _clear_topics(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_json.pop(str(author))
    await write_json(topics_json, "topics.json")
    await ctx.send("Topics have been cleared!")

@slash.slash(name="view_topics", description="View your saved topic settings.")
async def _view_topics(ctx):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(author)]
    mes = 'Here are your current topics:'
    for topic_dict in topics_list:
        mes += f"\n{topic_dict['topic']}"
        if topic_dict['recent'] == 'y':
            mes += " (recent papers only)"
    await ctx.send(mes)
    
@slash.slash(name="add_topic", description="Add a topics of papers you want Paper Bot to find for you", 
             options=[
                 discord_slash.manage_commands.create_option(name = 'topic', option_type = 3, required = True, description = "The topic you are interested in"),
                 discord_slash.manage_commands.create_option(name = 'recent', option_type = 3, required = True, description = "Do you want to restrict the search to papers published in the last year? (y/n)"),
             ])
async def _add_topic(ctx, topic, recent):
    author = ctx.author.id #save topic preferences in json
    topics_json = await open_json("topics.json")
    if str(author) not in topics_json.keys(): #if this user dosn't have set topics already
        topics_json[str(author)] = [] #create a topic list for them

    topics_json[str(author)].append({"topic": topic, "recent": recent}) #add the new topic
    await write_json(topics_json, "topics.json")

    await ctx.send("Your new topic has been added!")

@slash.slash(name="find_papers", description="Find papers based on your topic interests",
             options=[
                 discord_slash.manage_commands.create_option(name = 'num_papers', option_type = 4, required = True, description = "The number of papers you want to find for each topic"),
             ])
async def _find_papers(ctx, num_papers):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics = topics_json[str(author)]

    allArticles = await getArticles(topics, num_papers)
    mes = await format_paper_message(topics, allArticles)
    await ctx.send(mes)

bot.run(discord_token)
