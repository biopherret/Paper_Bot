#import discord
#import interactions
#from interactions import slash_command, SlashContext
#import discord_slash
#from discord.ext import commands, tasks
#from pypdf import PdfReader
#from bs4 import BeautifulSoup
#from gtts import gTTS
#from StringProgressBar import progressBar
#from gradio_client import Client

import json
#import asyncio, math, urllib.request, os
#from datetime import datetime, time, timedelta

#import serpapi
#import itertools
#import os
#import pandas as pd



#bot = commands.Bot(command_prefix = '.', intents=discord.Intents.default())
#slash = discord_slash.SlashCommand(bot, sync_commands=True) # Declares slash commands through the bot.

#TODO: make about page
#TODO: call the huggingface lm to summarize the text
#TODO: make a command to give a pdf to summarrize

discord_token = open("discord_token.txt", "r").read()
#serpapi_token = open("serpapi_token.txt", "r").read()

from interactions import Client, Intents, listen

bot = Client(intents=Intents.DEFAULT)
# intents are what events we want to receive from discord, `DEFAULT` is usually fine

@listen()  # this decorator tells snek that it needs to listen for the corresponding event, and run this coroutine
async def on_ready():
    # This event is called when the bot is ready to respond to commands
    print("Ready")
    print(f"This bot is owned by {bot.owner}")


@listen()
async def on_message_create(event):
    # This event is called when a message is sent in a channel the bot can see
    print(f"message received: {event.message.content}")

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)
    
# async def not_a_repeat_article(title, found_articles):
#     for article_dict in found_articles:
#         if title == article_dict['title']:
#             return False
#     return True

# async def get_next_run_time(target_time):
#     now = datetime.now()
#     next_run = datetime.combine(now.date(), target_time)
#     if next_run < now:
#         next_run += timedelta(days=1)
#     return (next_run - now).total_seconds()

# async def uptime_days_rounded_down():
#     delta = datetime.now().date() - start_time.date()
#     if str(delta) == "0:00:00":
#         return 0
#     else:
#         return str(delta).split()[0]
    
# async def read_pdf(doc_link, title):
#     response = urllib.request.urlopen(doc_link)
#     file = open(title, 'wb')
#     file.write(response.read())
#     file.close()

#     reader = PdfReader(title)
#     context_txt = ""
#     for page in reader.pages:
#         context_txt += page.extract_text()
#     os.remove(title) 
#     return context_txt

# async def read_web(link):
#     page = urllib.request.urlopen(link)
#     html = page.read().decode("utf-8")
#     soup = BeautifulSoup(html, "html.parser")
#     return soup.get_text()
    
# async def truncate_hyperlinked_title(user, title, link):
#     max_title_length = 200 - len(link) - 6 #[title](link)\n
#     if max_title_length < 30:
#         discord_user = await bot.fetch_user(user)
#         await discord_user.send(f"The hyperlink for [{title}]({link}) was too long to include in the main message.")
#         return f"{title[:200]}..."
#     if len(title) >= max_title_length:
#         return f'[{title[:max_title_length] + "..."}]({link})'
#     else:
#         return f'[{title}]({link})'

# async def send_command_response(ctx, user, message, is_embed=False):
#     if not isinstance(ctx.channel, discord.channel.DMChannel): #if the slash command was used in a server
#         await ctx.send("Sending you a DM to keep things organized. To avoid spamming the server, please use Paper Bot in DMs.") #sending a message in response to the slash command to only use DMs in the future
#         discord_user = await bot.fetch_user(user)
#         if is_embed:
#             await discord_user.send(embed=message)
#         else:
#             await discord_user.send(message) #send the message as a DM
#     else: #if the slash command was used in a DM
#         if is_embed:
#             await ctx.send(embed=message)
#         else:
#             await ctx.send(message) #send the message as a DM, in response to the slash command

# async def user_exists(ctx, user):
#     topics_json = await open_json("topics.json")
#     if str(user) in topics_json.keys():
#         return True
#     else:
#         await send_command_response(ctx, user, "You don't have any topics saved! Use the /add_topic command to add a topic.")
#         return False
    
# async def send_warning_to_schedule_users():
#     topics_json = await open_json("topics.json")
#     users = [user for user in topics_json.keys() if topics_json[user]['search_schedule'] != None] #get all users with a search schedule
#     for user in users:
#         discord_user = await bot.fetch_user(user)
#         await discord_user.send("Warning: I just woke up from a nap, this means I have lost track of how many days its been since I last sent you papers. I will send you papers at 9AM, and after your paper frequency will return to normal.")

# async def getArticles(topics_list, num_papers, user):
#     topics_json = await open_json("topics.json")
#     found_articles = topics_json[str(user)]["found_articles"]
#     new_articles = []

#     for topic_dict in topics_list:
#         n = 0 #keep track of the number of papers found
#         i = 0 #keep track of th number of searches done
        
#         while n < num_papers: #while we haven't found the desired number of papers yet
#             params = {
#                 "engine": "google_scholar",
#                 "q": topic_dict['topic'],
#                 "api_key": serpapi_token,
#                 "scisbd": topic_dict['recent'],
#                 "hl": "en",
#                 'num': 20,
#                 'start': i*20
#                 }
#             search=serpapi.search(params)
#             i += 1
#             for r in range(len(search['organic_results'])): #for each article found in the search
#                 title = search['organic_results'][r]['title']
#                 if await not_a_repeat_article(title, found_articles): 
#                     online_link = search['organic_results'][r]['link']
#                     n += 1
#                     if 'resources' in search['organic_results'][r].keys(): #if the search has attached docs
#                         doc_type = search['organic_results'][r]['resources'][0]['file_format'] #get the doc type for the first resource
#                         doc_link = search['organic_results'][r]['resources'][0]['link'] #get the link for the first resource
#                     else: #if there are no attached docs
#                         doc_type = None
#                         doc_link = None

#                     article_dict = {'title': title, 'online_link': online_link, 'topic': topic_dict['topic'], 'doc_type': doc_type, 'doc_link': doc_link}
#                     found_articles.append(article_dict)
#                     new_articles.append(article_dict)
        
#                 if n == num_papers:
#                     break

#     await write_json(topics_json, "topics.json") #save new articles to json
#     return new_articles

# async def get_text_for_LM(paper_title, doc_type, doc_link, online_link, user):
#     if doc_type == 'PDF':  
#         try:
#             context_text = await read_pdf(doc_link, paper_title)
#             return context_text
#         except:
#             pass

#     if doc_type == 'HTML':
#         try:
#             context_text = await read_web(doc_link)
#             return context_text
#         except:
#             pass
    
#     try:
#         context_text = await read_web(online_link)
#         return context_text
#     except:
#         discord_user = await bot.fetch_user(user)
#         return None

# async def get_summary_from_LM(context_text):
#     client = Client("biopherret/Paper_Summarizer")
#     prompt = f'The following text is extracted from a PDF file of an academic paper. Ignoring the formatting text and the works cited, can you summarize the paper for a PhD student so I can decided if I want to read the paper? Thank you! Here is the paper text: "{context_text}"'
#     result = client.predict("Hello!!",
# 		"You are a friendly Chatbot.",
# 		512,
# 		0.7,
# 		0.95,
# 		api_name="/chat"
# )
#     print(result)
#     return result
    
# async def text_to_mp3(text, title):
#     tts = gTTS(text, lang='en', slow = False)
#     tts.save(f"{title}.mp3")
#     file_to_send = discord.File(f"{title}.mp3")
#     os.remove(f"{title}.mp3")
#     return file_to_send

# async def find_papers(user, num_papers):
#     topics_json = await open_json("topics.json")
#     topics_list = topics_json[str(user)]["topic_settings"]

#     found_articles = await getArticles(topics_list, num_papers, user)
#     num_found = int(len(found_articles))

#     embed = discord.Embed(title="Papers I Found For You")
#     for topic_dict in topics_list:
#         hyperlinked_papers_list = [await truncate_hyperlinked_title(user, article_dict['title'], article_dict['online_link']) for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']]
#         embed.add_field(name=f'{topic_dict["topic"]} (Recent Only: {["No", "Yes"][topic_dict["recent"]]})', value="\n".join(hyperlinked_papers_list), inline=False)
#     discord_user = await bot.fetch_user(user)
#     await discord_user.send(embed = embed)

#     i = 0
#     progress_mes = await discord_user.send("I will now attempt to summarize the papers for you. This may take a while, and I am not always able to summarize every paper\n {}".format(progressBar.filledBar(num_found, i, size = num_found)[0]))
#     for article_dict in found_articles:
#         i += 1
#         context_txt = await get_text_for_LM(article_dict['title'], article_dict['doc_type'], article_dict['doc_link'], article_dict['online_link'], user)
#         if context_txt != None:
#             summary_txt = await get_summary_from_LM(context_txt)
#             file = await text_to_mp3(summary_txt, article_dict['title'])
#             await discord_user.send(file=file, content = "")
#         await progress_mes.edit(content = "I will now attempt to summarize the papers for you. This may take a while, and I am not always able to summarize every paper.\n {}".format(progressBar.filledBar(num_found, i, size = num_found)[0]))   
#     await discord_user.send("Done!")

# @slash.slash(name="clear_history", description="Clear all Paper Bot topic settings and articles (remove all previously found papers from history).")
# async def _clear_history(ctx):  
#     user = ctx.author.id
#     topics_json = await open_json("topics.json")
#     topics_json.pop(str(user)) #remove the user from the json
#     await write_json(topics_json, "topics.json")

#     await send_command_response(ctx, user, "Your history has been cleared! All topic settings and found articles have been removed.")

# @slash.slash(name="clear_topics", description="Clear your saved topic settings.")
# async def _clear_topics(ctx):
#     user = ctx.author.id
#     if await user_exists(ctx, user):
#         topics_json = await open_json("topics.json")
#         topics_json[str(user)]['topic_settings'] = [] #empty the topic settings list
#         await write_json(topics_json, "topics.json")

#         await send_command_response(ctx, user, "Your topic settings have been cleared!")    

# @slash.slash(name="view_topics", description="View your saved topic settings.")
# async def _view_topics(ctx):
#     user = ctx.author.id
#     if await user_exists(ctx, user):
#         topics_json = await open_json("topics.json")
#         topics_list = topics_json[str(user)]['topic_settings']

#         embed = discord.Embed(title="Your Topics", description="Here are your current topic settings:")
#         for topic_dict in topics_list:
#             embed.add_field(name=topic_dict['topic'], value=f"Recent papers only?: {['No', 'Yes'][topic_dict['recent']]}", inline=False)

#         await send_command_response(ctx, user, embed, is_embed=True)
    
# @slash.slash(name="add_topic", description='Add a topic of papers you want Paper Bot to find for you. Use "author: name" to search for authors.', 
#              options=[
#                  discord_slash.manage_commands.create_option(name = 'topic', option_type = 3, required = True, description = "The topic you are interested in"),
#                  discord_slash.manage_commands.create_option(name = 'recent', option_type = 3, required = True, description = "Do you want to restrict the search to papers published in the last year? (y/n)"),
#              ])
# async def _add_topic(ctx, topic, recent):
#     user = ctx.author.id #save topic preferences in json
#     topics_json = await open_json("topics.json")
#     if str(user) not in topics_json.keys(): #if this user dosn't exist yet
#         topics_json[str(user)] = {'topic_settings': [], 'found_articles': [], 'search_schedule' : None, 'auto_num' : 0} #create a dictionary object for the new user
#         discord_user = await bot.fetch_user(user)
#         await discord_user.send("Welcome to Paper Bot! I've created a new user profile for you.")

#     if recent == 'y':
#         recent = 1
#     else:
#         recent = 0

#     topics_json[str(user)]['topic_settings'].append({"topic": topic, "recent": recent}) #add the new topic
#     await write_json(topics_json, "topics.json")
    
#     await send_command_response(ctx, user, "Your new topic has been added!")

# @slash.slash(name="find_papers_now", description="Find papers based on your topic interests",
#              options=[
#                  discord_slash.manage_commands.create_option(name = 'num_papers', option_type = 4, required = True, description = "The number of papers you want to find for each topic (Max 5)"),
#              ])
# async def _find_papers_now(ctx, num_papers):
#     user = ctx.author.id
#     if num_papers < 6:
#         if await user_exists(ctx, user):
#             await send_command_response(ctx, user, "Finding papers for you...") #sending an initial message b/c if the initial response from the bot takes too long, discord will send a no-response error message
#             await find_papers(user, num_papers)
#     else: #if they are trying to find more than 5 papers per topic
#         await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")
    
# @slash.slash(name="schedule", description="Set the frequency Paper Bot will automatically find papers and send them to your DM.",
#              options=[
#                  discord_slash.manage_commands.create_option(name = 'days', option_type = 4, required = True, description = "Find papers every x days."),
#                  discord_slash.manage_commands.create_option(name = 'number_of_papers', option_type = 4, required = True, description = "Number of papers to find per search per topic.")
#              ])
# async def _schedule(ctx, days, number_of_papers):
#     user = ctx.author.id
#     if number_of_papers < 6:
#         if await user_exists(ctx, user):
#             topics_json = await open_json("topics.json")
#             topics_json[str(user)]['search_schedule'] = days
#             topics_json[str(user)]['auto_num'] = number_of_papers
#             await write_json(topics_json, "topics.json")

#             await send_command_response(ctx, user, f"Paper Bot will now find {number_of_papers} papers per topic every {days} days.")
#     else: #if they are trying to find more than 5 papers per topic
#         await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")


# @bot.tree.command(name="summarize_pdf", description="Summarize a PDF file")
# async def _summarize_pdf(ctx, pdf : discord.Attachment):
#     user = ctx.author.id
#     print(pdf, type(pdf))
#     await ctx.send("I got your pdf")
#     #await send_command_response(ctx, user, "I got your pdf")

# @tasks.loop(hours = 24)
# async def schedule_find_papers():
#     day_count = await uptime_days_rounded_down()
#     topics_json = await open_json("topics.json")
#     users = [user for user in topics_json.keys() if topics_json[user]['search_schedule'] != None] #get all users with a search schedule
#     for user in users:
#         frequency = topics_json[user]['search_schedule']
#         num = topics_json[user]['auto_num']
#         if int(day_count) % int(frequency) == 0:
#             await find_papers(user, num)

# @schedule_find_papers.before_loop #this executes before the above loop starts
# async def before_schedule_find_papers():
#     target_time = time(hour=9, minute=00)
#     next_run_in_seconds = await get_next_run_time(target_time)
#     await asyncio.sleep(next_run_in_seconds)

bot.start()