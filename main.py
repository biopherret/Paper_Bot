import discord
import discord_slash
from discord.ext import commands

import json
import time

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
    found_articles = []
    for topic_dict in topics_list:
        params = {
            "engine": "google_scholar",
            "q": topic_dict['topic'],
            "api_key": serpapi_token,
            "scisbd": topic_dict['recent'],
            "hl": "en"
            }
        search1=serpapi.search(params)
        n = 0
        for article in range(len(search1)):
            n += 1
            article_dict = {'title': search1['organic_results'][article]['title'], 'online_link': search1['organic_results'][article]['link'], 'topic': topic_dict['topic']}
            found_articles.append(article_dict)
            if n == num_papers:
                break
    return found_articles

#TODO: add recent or not in find papers imbend titles
#TODO: find different way to get PDF or HTML (link is not it, maybe its resources?)
#TODO: add doc_type and doc_link to article_dict
#TODO: save list of article_dicts to json file
#TODO: check for repeat articles

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

    embed = discord.Embed(title="Your Topics", description="Here are your current topic settings:")
    for topic_dict in topics_list:
        embed.add_field(name=topic_dict['topic'], value=f"Recent papers only?: {['No', 'Yes'][topic_dict['recent']]}", inline=False)
    await ctx.send(embed = embed)
    
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
    topics_list = topics_json[str(author)]["topic_settings"]

    found_articles = await getArticles(topics_list, num_papers)

    embed = discord.Embed(title="Papers I Found For You", description="For now, these can repeat, in a future update I will keep track of what I send you and avoid repeats.")
    for topic_dict in topics_list:
        paper_list = [f"[{article_dict['title']}]({article_dict['online_link']})" for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']]
        embed.add_field(name=f'{topic_dict["topic"]} (Recent Only: {["No", "Yes"][topic_dict["recent"]]})', value="\n".join(paper_list), inline=False)
    try:
        await ctx.send(embed = embed)
    except:
        time.sleep(2) #sometimes discord appears to time out and throw an error, if this happens try again after a few seconds
        await ctx.send(embed = embed)

bot.run(discord_token)
