import discord
import discord_slash
from discord.ext import commands, tasks
from pypdf import PdfReader

import json, asyncio, math, urllib.request, os
from datetime import datetime, time, timedelta

import serpapi
import itertools
import os
import pandas as pd

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.all())
slash = discord_slash.SlashCommand(bot, sync_commands=True) # Declares slash commands through the bot.

#TODO: make about page
#TODO: scrap the paper text from pdf
#TODO: scrap paper text from html link
#TODO: scrap paper text from normal link with disclaimer
#TODO: call the huggingface lm to summarize the text
#TODO: convert text to mp4
#TODO: add mp4 files to the find papers message
#TODO: summarizing progress bar

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

def get_next_run_time(target_time):
    now = datetime.now()
    next_run = datetime.combine(now.date(), target_time)
    if next_run < now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()

def uptime_days_rounded_down():
    delta = datetime.now().date() - start_time.date()
    if str(delta) == "0:00:00":
        return 0
    else:
        return str(delta).split()[0]
    
async def read_pdf(doc_link, title):
    response = urllib.request.urlopen(doc_link)
    file = open(title, 'wb')
    file.write(response.read())
    file.close()

    reader = PdfReader(title)
    context_txt = ""
    for page in reader.pages:
        context_txt += page.extract_text()
    os.remove(title) 
    return context_txt
    
async def truncate_hyperlinked_title(user, title, link):
    max_title_length = 200 - len(link) - 6 #[title](link)\n
    if max_title_length < 30:
        discord_user = await bot.fetch_user(user)
        await discord_user.send(f"The hyperlink for [{title}]({link}) was too long to include in the main message.")
        return f"{title[:200]}..."
    if len(title) >= max_title_length:
        return f'[{title[:max_title_length] + "..."}]({link})'
    else:
        return f'[{title}]({link})'

async def send_command_response(ctx, user, message, is_embed=False):
    if not isinstance(ctx.channel, discord.channel.DMChannel): #if the slash command was used in a server
        await ctx.send("Sending you a DM to keep things organized. To avoid spamming the server, please use Paper Bot in DMs.") #sending a message in response to the slash command to only use DMs in the future
        discord_user = await bot.fetch_user(user)
        if is_embed:
            await discord_user.send(embed=message)
        else:
            await discord_user.send(message) #send the message as a DM
    else: #if the slash command was used in a DM
        if is_embed:
            await ctx.send(embed=message)
        else:
            await ctx.send(message) #send the message as a DM, in response to the slash command

async def user_exists(ctx, user):
    topics_json = await open_json("topics.json")
    if str(user) in topics_json.keys():
        return True
    else:
        await send_command_response(ctx, user, "You don't have any topics saved! Use the /add_topic command to add a topic.")
        return False
    
async def send_warning_to_schedule_users():
    topics_json = await open_json("topics.json")
    users = [user for user in topics_json.keys() if topics_json[user]['search_schedule'] != None] #get all users with a search schedule
    for user in users:
        discord_user = await bot.fetch_user(user)
        await discord_user.send("Warning: I just woke up from a nap, this means I have lost track of how many days its been since I last sent you papers. I will send you papers at 9AM, and after your paper frequency will return to normal.")

async def getArticles(topics_list, num_papers, user):
    topics_json = await open_json("topics.json")
    found_articles = topics_json[str(user)]["found_articles"]
    new_articles = []

    for topic_dict in topics_list:
        n = 0 #keep track of the number of papers found
        i = 0 #keep track of th number of searches done
        
        while n < num_papers: #while we haven't found the desired number of papers yet
            params = {
                "engine": "google_scholar",
                "q": topic_dict['topic'],
                "api_key": serpapi_token,
                "scisbd": topic_dict['recent'],
                "hl": "en",
                'num': 20,
                'start': i*20
                }
            search=serpapi.search(params)
            i += 1
            for r in range(len(search['organic_results'])): #for each article found in the search
                print(n,i)
                title = search['organic_results'][r]['title']
                if await not_a_repeat_article(title, found_articles): 
                    online_link = search['organic_results'][r]['link']
                    n += 1
                    if 'resources' in search['organic_results'][r].keys(): #if the search has attached docs
                        doc_type = search['organic_results'][r]['resources'][0]['file_format'] #get the doc type for the first resource
                        doc_link = search['organic_results'][r]['resources'][0]['link'] #get the link for the first resource
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

async def get_text_for_LM(paper_title, doc_type, doc_link, online_link, user):
    if doc_type == 'PDF':  
        try:
            context_text = await read_pdf(doc_link, paper_title)
            return context_text
        except:
            return None  
        
    else:
        discord_user = await bot.fetch_user(user)
        await discord_user.send(f"Sorry, I can only summarize PDFs at the moment and wasn't able to find one for {paper_title}.")
        return None


async def find_papers(user, num_papers):
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(user)]["topic_settings"]

    found_articles = await getArticles(topics_list, num_papers, user)

    embed = discord.Embed(title="Papers I Found For You")
    for topic_dict in topics_list:
        hyperlinked_papers_list = [await truncate_hyperlinked_title(user, article_dict['title'], article_dict['online_link']) for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']]
        embed.add_field(name=f'{topic_dict["topic"]} (Recent Only: {["No", "Yes"][topic_dict["recent"]]})', value="\n".join(hyperlinked_papers_list), inline=False)
    discord_user = await bot.fetch_user(user)
    await discord_user.send(embed = embed)

    context_txts = [await get_text_for_LM(article_dict['title'], article_dict['doc_type'], article_dict['doc_link'], article_dict['online_link'], user) for article_dict in found_articles]
    print(context_txts)

@bot.event
async def on_ready():
    global start_time
    start_time = datetime.now()
    await send_warning_to_schedule_users()
    schedule_find_papers.start()
    print("Ready!")

@slash.slash(name="clear_history", description="Clear all Paper Bot topic settings and articles (remove all previously found papers from history).")
async def _clear_history(ctx):  
    user = ctx.author.id
    topics_json = await open_json("topics.json")
    topics_json.pop(str(user)) #remove the user from the json
    await write_json(topics_json, "topics.json")

    await send_command_response(ctx, user, "Your history has been cleared! All topic settings and found articles have been removed.")

@slash.slash(name="clear_topics", description="Clear your saved topic settings.")
async def _clear_topics(ctx):
    user = ctx.author.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_json[str(user)]['topic_settings'] = [] #empty the topic settings list
        await write_json(topics_json, "topics.json")

        await send_command_response(ctx, user, "Your topic settings have been cleared!")    

@slash.slash(name="view_topics", description="View your saved topic settings.")
async def _view_topics(ctx):
    user = ctx.author.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_list = topics_json[str(user)]['topic_settings']

        embed = discord.Embed(title="Your Topics", description="Here are your current topic settings:")
        for topic_dict in topics_list:
            embed.add_field(name=topic_dict['topic'], value=f"Recent papers only?: {['No', 'Yes'][topic_dict['recent']]}", inline=False)

        await send_command_response(ctx, user, embed, is_embed=True)
    
@slash.slash(name="add_topic", description='Add a topic of papers you want Paper Bot to find for you. Use "author: name" to search for authors.', 
             options=[
                 discord_slash.manage_commands.create_option(name = 'topic', option_type = 3, required = True, description = "The topic you are interested in"),
                 discord_slash.manage_commands.create_option(name = 'recent', option_type = 3, required = True, description = "Do you want to restrict the search to papers published in the last year? (y/n)"),
             ])
async def _add_topic(ctx, topic, recent):
    user = ctx.author.id #save topic preferences in json
    topics_json = await open_json("topics.json")
    if str(user) not in topics_json.keys(): #if this user dosn't exist yet
        topics_json[str(user)] = {'topic_settings': [], 'found_articles': [], 'search_schedule' : None, 'auto_num' : 0} #create a dictionary object for the new user
        discord_user = await bot.fetch_user(user)
        await discord_user.send("Welcome to Paper Bot! I've created a new user profile for you.")

    if recent == 'y':
        recent = 1
    else:
        recent = 0

    topics_json[str(user)]['topic_settings'].append({"topic": topic, "recent": recent}) #add the new topic
    await write_json(topics_json, "topics.json")
    
    await send_command_response(ctx, user, "Your new topic has been added!")

@slash.slash(name="find_papers_now", description="Find papers based on your topic interests",
             options=[
                 discord_slash.manage_commands.create_option(name = 'num_papers', option_type = 4, required = True, description = "The number of papers you want to find for each topic (Max 5)"),
             ])
async def _find_papers_now(ctx, num_papers):
    user = ctx.author.id
    if num_papers < 6:
        if await user_exists(ctx, user):
            await send_command_response(ctx, user, "Finding papers for you...") #sending an initial message b/c if the initial response from the bot takes too long, discord will send a no-response error message
            await find_papers(user, num_papers)
    else: #if they are trying to find more than 5 papers per topic
        await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")
    
@slash.slash(name="schedule", description="Set the frequency Paper Bot will automatically find papers and send them to your DM.",
             options=[
                 discord_slash.manage_commands.create_option(name = 'days', option_type = 4, required = True, description = "Find papers every x days."),
                 discord_slash.manage_commands.create_option(name = 'number_of_papers', option_type = 4, required = True, description = "Number of papers to find per search per topic.")
             ])
async def _schedule(ctx, days, number_of_papers):
    user = ctx.author.id
    if number_of_papers < 6:
        if await user_exists(ctx, user):
            topics_json = await open_json("topics.json")
            topics_json[str(user)]['search_schedule'] = days
            topics_json[str(user)]['auto_num'] = number_of_papers
            await write_json(topics_json, "topics.json")

            await send_command_response(ctx, user, f"Paper Bot will now find {number_of_papers} papers per topic every {days} days.")
    else: #if they are trying to find more than 5 papers per topic
        await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")

@tasks.loop(hours = 24)
async def schedule_find_papers():
    day_count = uptime_days_rounded_down()
    topics_json = await open_json("topics.json")
    users = [user for user in topics_json.keys() if topics_json[user]['search_schedule'] != None] #get all users with a search schedule
    for user in users:
        frequency = topics_json[user]['search_schedule']
        num = topics_json[user]['auto_num']
        if int(day_count) % int(frequency) == 0:
            await find_papers(user, num)

@schedule_find_papers.before_loop #this executes before the above loop starts
async def before_schedule_find_papers():
    target_time = time(hour=9, minute=00)
    next_run_in_seconds = get_next_run_time(target_time)
    await asyncio.sleep(next_run_in_seconds)

bot.run(discord_token)