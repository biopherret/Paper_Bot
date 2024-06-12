import discord
import discord_slash
from discord.ext import commands, tasks

import json
import datetime

import serpapi
import itertools
import os
import pandas as pd
from datetime import date

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.all())
slash = discord_slash.SlashCommand(bot, sync_commands=True) # Declares slash commands through the bot.

#TODO: Made a loop at an interval of 24 hours (5 min to start to troubleshoot)
#TODO: add a user setting of frequency (in days) of paper finding
#TODO: make slash command to edit the setting
#TODO: loop looks at user setting to decide which user it is finding papers for on that day
#TODO: call get_papers as needed
#TODO: send papers to user DM

#TODO: scrap the paper text from the doc link
#TODO: put an LM on the pi
#TODO: have the LM generate summaries with context
#TODO: convert text to mp4
#TODO: add mp4 files to the find papers message

discord_token = open("discord_token.txt", "r").read()
serpapi_token = open("serpapi_token.txt", "r").read()

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)
    
async def not_a_repeat_article(title, found_articles):
    for article_dict in found_articles:
        if title == article_dict['title']:
            return False
    return True

async def getArticles(topics_list, num_papers, author):
    topics_json = await open_json("topics.json")
    found_articles = topics_json[str(author)]["found_articles"]
    new_articles = []

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
        for i in range(len(search1)): #for each article found in the search
            title = search1['organic_results'][i]['title']
            if await not_a_repeat_article(title, found_articles): 
                online_link = search1['organic_results'][i]['link']
                n += 1
                if 'resources' in search1['organic_results'][i].keys(): #if the search has attached docs
                    doc_type = search1['organic_results'][i]['resources'][0]['file_format'] #get the doc type for the first resource
                    doc_link = search1['organic_results'][i]['resources'][0]['link'] #get the link for the first resource
                else: #if there are no attached docs
                    doc_type = None
                    doc_link = None

                article_dict = {'title': title, 'online_link': online_link, 'topic': topic_dict['topic'], 'doc_type': doc_type, 'doc_link': doc_link}
                found_articles.append(article_dict)
                new_articles.append(article_dict)
    
            if n == num_papers:
                break
    await write_json(topics_json, "topics.json") #save new articles to json
    return new_articles

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
        topics_json[str(author)] = {'topic_settings': [], 'found_articles': [], 'search_schedule' : None} #create a dictionary object for the new user
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
    await ctx.send("Finding papers for you...") #sending an initial message b/c if the initial response from the bot takes too long, discord will send a no-response error message
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(author)]["topic_settings"]

    found_articles = await getArticles(topics_list, num_papers, author)

    embed = discord.Embed(title="Papers I Found For You")
    for topic_dict in topics_list:
        paper_list = [f"[{article_dict['title']}]({article_dict['online_link']})" for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']]
        embed.add_field(name=f'{topic_dict["topic"]} (Recent Only: {["No", "Yes"][topic_dict["recent"]]})', value="\n".join(paper_list), inline=False)
    await ctx.send(embed = embed)

@slash.slash(name="schedule", description="Set the frequency Paper Bot will automatically find papers and send them to your DM.",
             options=[
                 discord_slash.manage_commands.create_option(name = 'days', option_type = 4, required = True, description = "Find papers every x days.")
             ])
async def _schedule(ctx, days):
    author = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_json[str(author)]['search_schedule'] = days
    await write_json(topics_json, "topics.json")
    await ctx.send(f"Your paper finding schedule has been set to every {days} days.")

#TODO: error im getting: TypeError: loop() got an unexpected keyword argument 'time' despite internet saying it is a keyword argument https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html
#time = datetime.time(hour = 5, minute = 0)
#@tasks.loop(time=time) 
#async def schedule_find_papers():
#    topics_json = await open_json("topics.json")
#    authors = [author for author in topics_json.keys() if author['search_schedule'] != None] #get all users with a search schedule
#    for author in authors:
#        user = author['id']
#        await user.send('Hello')
        


bot.run(discord_token)
