import discord
from discord.ext import commands, tasks
import os

import json #for managing tokens and user data

import serpapi #for searching google scholar

import urllib.request #for reading pdfs from the web
from pypdf import PdfReader

from bs4 import BeautifulSoup #for reading text from web pages

from StringProgressBar import progressBar #to report progress of long tasks

from gradio_client import Client #to access a huggingface language model

from datetime import datetime, time, timedelta #for managing scheduler
import asyncio

import typing, functools #to prevent hf from blocking the main thread

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.default())
hf_chat_client = Client("biopherret/Paper_Summarizer")
hf_tts_client = Client("https://neongeckocom-neon-tts-plugin-coqui.hf.space/")

discord_token = open("discord_token.txt", "r").read()
serpapi_token = open("serpapi_token.txt", "r").read()

#TODO: add command to remove only one topic
#TODO: move how to get started to abvove commands
#TODO: make it more clear that its a progross bar
#TODO: message when you can't get a summary
#TODO: schedule change author to user
#TODO: schedlue max 5 papers
#TODO: remove clear history from users
#TODO: actually force them to use y or n
#TODO: add catch not found to send command message
#TODO: edit message to say done instae of new message saying done
#TODO: rename about help
#TODO: pic a proficle picture and staus
#TODO: remove optino to do user from the read me

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)

#calling hugging face blocks the thread (even if in a async function) this decorator will run the function in a separate thread
def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        wrapper = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, wrapper)
    return wrapper

async def not_a_repeat_article(title, found_articles):
    for article_dict in found_articles:
        if title == article_dict['title']:
            return False
    return True

async def get_next_run_time(target_time):
    now = datetime.now()
    next_run = datetime.combine(now.date(), target_time)
    if next_run < now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()

async def uptime_days_rounded_down():
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

async def read_web(link):
    page = urllib.request.urlopen(link)
    html = page.read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()
    
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
        await ctx.response.send_message("Sending you a DM to keep things organized. To avoid spamming the server, please use Paper Bot in DMs.") #sending a message in response to the slash command to only use DMs in the future
        discord_user = await bot.fetch_user(user)
        if is_embed:
            await discord_user.send(embed=message)
        else:
            await discord_user.send(message) #send the message as a DM
    else: #if the slash command was used in a DM
        if is_embed:
            await ctx.response.send_message(embed=message)
        else:
            await ctx.response.send_message(message) #send the message as a DM, in response to the slash command

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

async def get_text_for_LM(paper_title, doc_type, doc_link, online_link):
    if doc_type == 'PDF':  
        try:
            context_text = await read_pdf(doc_link, paper_title)
            return context_text
        except:
            pass

    if doc_type == 'HTML':
        try:
            context_text = await read_web(doc_link)
            return context_text
        except:
            pass
    
    try:
        context_text = await read_web(online_link)
        return context_text
    except:
        return None

@to_thread
def get_summary_from_LM(context_text):
    prompt = f'The following text is extracted from a PDF file of an academic paper. Ignoring the formatting text and the works cited, please summarize this paper. Thank you! Here is the paper text: "{context_text}"'
    try:
        result = hf_chat_client.predict(prompt,
            "You are a friendly Chatbot here to help PhD students by summarizing it for them.",
            512,
            0.7,
            0.95,
            api_name="/chat")
        return result
    except:
        return None

@to_thread
def text_to_mp3(text, title):
    try:
        filepath = hf_tts_client.predict(
            text,
            "en",
            fn_index=0)
    except:
        return None
    dir_path = os.path.dirname(filepath)
    new_path = os.path.join(dir_path, f"{title}.wav")
    os.rename(filepath, new_path) #rename the file to the title

    file_to_send = discord.File(new_path)
    os.remove(new_path)
    return file_to_send

async def find_papers(user, num_papers):
    topics_json = await open_json("topics.json")
    topics_list = topics_json[str(user)]["topic_settings"]

    found_articles = await getArticles(topics_list, num_papers, user)
    num_found = int(len(found_articles))

    embed = discord.Embed(title="Papers I Found For You")
    for topic_dict in topics_list:
        hyperlinked_papers_list = [await truncate_hyperlinked_title(user, article_dict['title'], article_dict['online_link']) for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']]
        embed.add_field(name=f'{topic_dict["topic"]} (Recent Only: {["No", "Yes"][topic_dict["recent"]]})', value="\n".join(hyperlinked_papers_list), inline=False)
    discord_user = await bot.fetch_user(user)
    await discord_user.send(embed = embed)

    i = 0
    progress_mes = await discord_user.send("I will now attempt to summarize the papers for you. This may take a while, and I am not always able to summarize every paper\n {}".format(progressBar.filledBar(num_found, i, size = num_found)[0]))
    for article_dict in found_articles:
        i += 1
        context_txt = await get_text_for_LM(article_dict['title'], article_dict['doc_type'], article_dict['doc_link'], article_dict['online_link'])
        if context_txt != None:
            summary_txt = await get_summary_from_LM(context_txt)
            if summary_txt != None:
                file = await text_to_mp3(summary_txt, article_dict['title'])
                if file != None:
                    await discord_user.send(file=file, content = "")
        await progress_mes.edit(content = "I will now attempt to summarize the papers for you. This may take a while, and I am not always able to summarize every paper.\n {}".format(progressBar.filledBar(num_found, i, size = num_found)[0]))   
    await discord_user.send("Done!")

@bot.event
async def on_ready():
    await bot.tree.sync()
    global start_time
    start_time = datetime.now()
    await send_warning_to_schedule_users()
    schedule_find_papers.start()
    print("Ready!")

@bot.tree.command(name="clear_history", description="Clear all Paper Bot topic settings and articles (remove all previously found papers from history).")
async def _clear_history(ctx):  
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_json.pop(str(user)) #remove the user from the json
        await write_json(topics_json, "topics.json")

        await send_command_response(ctx, user, "Your history has been cleared! All topic settings and found articles have been removed.")

@bot.tree.command(name="clear_topics", description="Clear your saved topic settings")
async def _clear_topics(ctx):
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_json[str(user)]['topic_settings'] = [] #empty the topic settings list
        await write_json(topics_json, "topics.json")

        await send_command_response(ctx, user, "Your topic settings have been cleared!")    

@bot.tree.command(name="view_topics", description="View your saved topic settings.")
async def _view_topics(ctx):
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_list = topics_json[str(user)]['topic_settings']

        embed = discord.Embed(title="Your Topics", description="Here are your current topic settings:")
        for topic_dict in topics_list:
            embed.add_field(name=topic_dict['topic'], value=f"Recent papers only?: {['No', 'Yes'][topic_dict['recent']]}", inline=False)

        await send_command_response(ctx, user, embed, is_embed=True)

@bot.tree.command(name="add_topic", description='Add a topic of papers you want Paper Bot to find for you.')
async def _add_topic(ctx, topic : str, recent : str):
    '''Add a topic of papers you are interested in

    Args:
        ctx (Interaction): The context of the command
        topic (str): Use "author: name" to search for authors.
        recent (str): Do you want to restrict the search to papers published in the last year? (y/n)
    '''
    user = ctx.user.id #save topic preferences in json
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


@bot.tree.command(name="find_papers_now", description="Find papers based on your topic interests")
async def _find_papers_now(ctx, num_papers : int):
    '''Find papers based on your topic instrests

    Args:
        ctx (Interaction): The context of the command
        num_papers (int): The number of papers you want to find for each topic (Max 5)
    '''
    user = ctx.user.id
    if num_papers < 6:
        if await user_exists(ctx, user):
            await send_command_response(ctx, user, "Finding papers for you...") #sending an initial message b/c if the initial response from the bot takes too long, discord will send a no-response error message
            await find_papers(user, num_papers)
    else: #if they are trying to find more than 5 papers per topic
        await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")
    

@bot.tree.command(name="schedule", description="Set the frequency Paper Bot will automatically find papers and send them to your DM.")
async def _schedule(ctx, days : int, number_of_papers : int):
    '''Set the frequency Paper Bot will automatically find papers and send them to your DM.

    Args:
        ctx (Interaction): The context of the command
        days (int): Find papers every x days.
        number_of_papers (int): Number of papers to find per search per topic.
    '''
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


@bot.tree.command(name="summarize_pdf", description="Summarize a PDF file")
async def _summarize_pdf(ctx, pdf : discord.Attachment):
    user = ctx.user.id
    await send_command_response(ctx, user, "I'm working on summarizing your PDF. This may take a while...")

    await pdf.save(pdf.filename)
    reader = PdfReader(pdf.filename)
    context_txt = ""
    for page in reader.pages:
        context_txt += page.extract_text()
    os.remove(pdf.filename)

    prompt = f'The following text is extracted from a PDF file of an academic paper. Ignoring the formatting text and the works cited, please summarize this paper. Thank you! Here is the paper text: "{context_txt}"'
    summary_txt = await get_summary_from_LM(prompt)
    discord_user = await bot.fetch_user(user)
    if summary_txt != None:
        file = await text_to_mp3(summary_txt, pdf.filename)
        if file != None:
            await discord_user.send(file=file, content = "")
        else:
            await discord_user.send("I'm sorry, I was unable to summarize this paper. Please try again later.")
    else:
        await discord_user.send("I'm sorry, I was unable to summarize this paper. Please try again later.")

@bot.tree.command(name="about", description="Learn more about Paper Bot")
async def _about(ctx):
    embed = discord.Embed(title="About Paper Bot", description="Paper Bot is a Discord bot that helps you find and summarize academic papers. You can add topics of interest, schedule automatic paper searches, and more!")
    embed.add_field(name="Commands", value="/add_topic lets you add new topics to your user profile\n/view_topics will show you your current topic settings\n/clear_topics resets your topic settings\n/clear_history will completely remove your user profile (topics, found articles, and schedule)\n/find_papers_now will find papers from each of your topics, and summarize them for you\n/schedule allows you to set a schedule for how often you want Paper Bot to automatically send you papers\n/summarize_pdf lets you send Paper Bot a pdf of a particular paper for it to summarize", inline=False)
    embed.add_field(name="How do I get Started?", value="To get started, use the /add_topic command to add a topic of interest. You can then use /find_papers_now to find papers for that topic, or use /schedule to have Paper Bot automatically send you papers every x days.", inline=False)
    embed.add_field(name="Why does Paper Bot not send me a summary for every paper?", value="Paper Bot requires access to the paper to be able to summarize it. Paper Bot uses both Goggle Scholar and web scraping to try to access the paper content, but some journal websites block these methods. For papers that paper bot wasn't able to summarize, you can retrieve the pdf from the provided links and use /summarize_pdf to retrieve the summary.", inline=False)
    await ctx.response.send_message(embed=embed)

# button = discord.ui.Button(label = "Click me!", style=discord.ButtonStyle.grey)
# async def button_callback(interaction:discord.Interaction):
#     await interaction.response.send_message("workie!",ephemeral=True)
# view = discord.ui.View(timeout = None)
# view.add_item(button)

# @bot.tree.command(name="tester", description="tester")
# async def _hello(ctx: discord.Interaction):
#     await ctx.response.send_message("tester", view=view)

@tasks.loop(hours = 24)
async def schedule_find_papers():
    day_count = await uptime_days_rounded_down()
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
    next_run_in_seconds = await get_next_run_time(target_time)
    await asyncio.sleep(next_run_in_seconds)

bot.run(discord_token)