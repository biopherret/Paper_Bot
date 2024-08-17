import discord
from discord.ext import commands, tasks
import os, copy

import json #for managing tokens and user data

import serpapi #for searching google scholar

import urllib.request #for reading pdfs from the web
from pypdf import PdfReader

from bs4 import BeautifulSoup #for reading text from web pages

from gradio_client import Client #to access a huggingface language model

from datetime import datetime, time, timedelta #for managing scheduler
import asyncio

import typing, functools #to prevent hf from blocking the main thread

from math import ceil #for dividing long messages into multiple messages

#import tiktoken

async def write_json(data, file_name):
    with open (file_name, 'w') as file:
        json.dump(data, file, indent = 4)

async def open_json(file_name):
    with open (file_name) as file:
        return json.load(file)

bot = commands.Bot(command_prefix = '.', intents=discord.Intents.default())
hf_tts_client = Client("https://neongeckocom-neon-tts-plugin-coqui.hf.space/")

discord_token = open("discord_token.txt", "r").read()
profile_pic_url = 'https://cdn.discordapp.com/attachments/1252697568396443679/1253814342177128500/Paper_Bot.png?ex=66773919&is=6675e799&hm=d18a0208886b173ee5d7088f03ac5621dea066a32494834d11e0fb3dd19ec0e3&'
serpapi_tokens = open("serpapi_tokens.txt", "r").readlines()

dev_user_id = 337933564911943682

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

async def get_day_of_week():
    day_int = datetime.today().weekday()
    week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    return week[day_int]
    
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
    if link == None:
        if len(title) >= 200 - 6 - 22:
            return f"{title[:200]}..."
        else:
            return title
    else:
        max_title_length = 200 - len(link) - 6 - 22 #:white_square_button: [title](link)\n
        if max_title_length < 30:
            discord_user = await bot.fetch_user(user)
            await discord_user.send(f"The hyperlink for [{title}]({link}) was too long to include in the main message.")
            return f"{title[:200]}..."
        if len(title) >= max_title_length:
            return f'[{title[:max_title_length] + "..."}]({link})'
        else:
            return f'[{title}]({link})'

async def send_command_response(ctx, user, message, is_embed=False):
    try:
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
    except:
        await ctx.response.send_message("I'm sorry, sometimes discord doesn't respond to me properly. Please try again later.")

async def user_exists(ctx, user):
    topics_json = await open_json("topics.json")
    user_data = topics_json["users"]
    if str(user) in user_data.keys():
        return True
    else:
        await send_command_response(ctx, user, "You don't have any topics saved! Use the /add_topic command to add a topic.")
        return False
    
async def getArticles(topics_list, num_papers, user):
    topics_json = await open_json("topics.json")
    serpapi_token_num = topics_json['current_serpapi_token_num']
    user_data = topics_json["users"]
    serpapi_token = serpapi_tokens[serpapi_token_num]

    found_articles = user_data[str(user)]["found_articles"]
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
            try:
                search=serpapi.search(params)
            except:
                print("Ran out of serpapi tokens")
                if int(serpapi_token_num) == len(serpapi_tokens) - 1: #if we are at the last token
                    print("switch to the first token")
                    serpapi_token_num = 0 #go back to the first token
                else: #if we are not at the last token
                    print('switch to the next token')
                    serpapi_token_num += 1 #try the next one

                topics_json['current_serpapi_token_num'] = serpapi_token_num
                await write_json(topics_json, "topics.json")
                print('switch recorded')
                discord_dev_user = await bot.fetch_user(dev_user_id)
                await discord_dev_user.send(f"Ran out of serpapi tokens. Switching to token number {serpapi_token_num} out of {len(serpapi_tokens)}.")
                #change current token to +1 and continue in the loop
                continue
            i += 1
            if 'organic_results' not in search.keys(): #if there are no search results
                discord_user = await bot.fetch_user(user)
                await discord_user.send(f"Sorry, I couldn't find {num_papers} papers for {topic_dict['topic']}, try setting your topic to something else.")
                break

            for r in range(len(search['organic_results'])): #for each article found in the search
                title = search['organic_results'][r]['title']
                if await not_a_repeat_article(title, found_articles):
                    if 'link' in search['organic_results'][r].keys(): #if the search has an attached link
                        online_link = search['organic_results'][r]['link']
                    else:
                        online_link = None
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
    
def split_text(text, max_length):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]

@to_thread
def get_summary_from_LM(context_text):
    try:
        hf_chat_client = Client("biopherret/Paper_Summarizer") #wake up the chatbot
    except:
        #discord_dev_user = await bot.fetch_user(dev_user_id)
        #await discord_dev_user.send('The chatbot is not responding, please wake it up.')
        print('The chatbot is not respondnig, please wake it up')
    
    #if len(context_text) > 103600:
    #    print(f'context text length: {len(context_text)}')
    #    context_text = context_text[:103600] #limit the text to 103699 characters

    prompt = f'The following text is extracted from a PDF file of an academic paper. Ignoring the formatting text and the works cited, please summarize this paper:\n\n{context_text}'

    #encoding = tiktoken.encoding_for_model("gpt2")
    #token_num = len(encoding.encode(prompt))
    #print(token_num)

    #result = hf_chat_client.predict(prompt,
    #       "You are a friendly Chatbot here to help PhD students by summarizing it for them.",
    #       512,
    #       0.7,
    #       0.95,
    #      api_name="/chat")
    #return result

    try:
        result = hf_chat_client.predict(prompt,
            "You are a friendly Chatbot here to help PhD students by summarizing it for them.",
            512,
            0.7,
            0.95,
            api_name="/chat")
        return result
    except:
        print(f'prompt length:{len(prompt)}')
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

async def make_paper_message(topic_list, recent_list, hyperlink_lists, status_lists):
    embed = discord.Embed(title="Papers I Found For You", color = 0x99e3ee)
    embed.set_thumbnail(url=profile_pic_url)
    complete = True
    for i in range(len(status_lists)): #for each topic
        if status_lists[i] == []: #if no papers were found
            hyperlink_lists[i] = ["No Papers Found"]
        for j in range(len(status_lists[i])): #for each paper found in that topic
            if status_lists[i][j] == None:
                complete = False
                hyperlink_lists[i][j] = f":white_square_button: {hyperlink_lists[i][j]}"
            elif status_lists[i][j] == True:
                hyperlink_lists[i][j] = f":white_check_mark: {hyperlink_lists[i][j]}"
            elif status_lists[i][j] == False:
                hyperlink_lists[i][j] = f":x: {hyperlink_lists[i][j]}"

    for i in range(len(topic_list)):
        recent = ['No', 'Yes'][recent_list[i]]
        embed.add_field(name=f'{topic_list[i]} (Recent Only: {recent})', value="\n".join(hyperlink_lists[i]), inline=False)
    if not complete:
        embed.add_field(name="Now attempting to summarize papers...", value = '', inline=False)
    else: 
        embed.add_field(name="I've finished summarizing papers!", value = '', inline=False)
    return embed

async def send_summary_to_user(user, summary_txt, message_or_audio, title):
    discord_user = await bot.fetch_user(user)
    if summary_txt != None and message_or_audio == "audio":
        file = await text_to_mp3(summary_txt, title)
        success = True
        if file != None:
            await discord_user.send(file=file, content = "")
        else:
            await discord_user.send(f'The text to speech AI failed for "{title}", so sending you the summary as a message instead.')
            print(summary_txt)
            for i in range(ceil(len(summary_txt) / 4096)):
                embed = discord.Embed(title=title, color = 0x99e3ee)
                embed.set_thumbnail(url=profile_pic_url)
                embed.description = (summary_txt[(4096*i):(4096*(i+1))])
                await discord_user.send(embed=embed)
    elif summary_txt != None and message_or_audio == "message":
        success = True
        for i in range(ceil(len(summary_txt) / 4096)):
            embed = discord.Embed(title=title, color = 0x99e3ee)
            embed.set_thumbnail(url=profile_pic_url)
            embed.description = (summary_txt[(4096*i):(4096*(i+1))])
            await discord_user.send(embed=embed)
    else:
        success = False
    return success

async def find_papers(user, num_papers, message_or_audio):
    topics_json = await open_json("topics.json")
    user_data = topics_json["users"]
    topics_list = user_data[str(user)]["topic_settings"]

    found_articles = await getArticles(topics_list, num_papers, user)
    num_found = int(len(found_articles))

    original_hyperlink_papers_lists = []
    for topic_dict in topics_list:
        original_hyperlink_papers_lists.append([await truncate_hyperlinked_title(user, article_dict['title'], article_dict['online_link']) for article_dict in found_articles if article_dict['topic'] == topic_dict['topic']])

    discord_user = await bot.fetch_user(user)
    status_lists =  [[None for j in range(len(original_hyperlink_papers_lists[i]))] for i in range(len(topics_list))]
    message = await discord_user.send(embed = await make_paper_message([topic_dict['topic'] for topic_dict in topics_list], [topic_dict['recent'] for topic_dict in topics_list], copy.deepcopy(original_hyperlink_papers_lists), status_lists))

    for count_t, topic_dict in enumerate(topics_list): #for each topic
        for count_a, article_dict in enumerate([article for article in found_articles if article['topic'] == topic_dict['topic']]): #for each article in that topic
            success = False
            context_txt = await get_text_for_LM(article_dict['title'], article_dict['doc_type'], article_dict['doc_link'], article_dict['online_link'])
            if context_txt != None:
                summary_txt = await get_summary_from_LM(context_txt)
                success = await send_summary_to_user(user, summary_txt, message_or_audio, article_dict['title'])
            if success:
                status_lists[count_t][count_a] = True
            else:
                status_lists[count_t][count_a] = False

            await message.edit(embed = await make_paper_message([topic_dict['topic'] for topic_dict in topics_list], [topic_dict['recent'] for topic_dict in topics_list], copy.deepcopy(original_hyperlink_papers_lists), status_lists))

@bot.event
async def on_ready():
    await bot.tree.sync()
    global start_time
    start_time = datetime.now()
    await bot.wait_until_ready()

    topics_json = await open_json("topics.json")
    topics_json['schedule_loop_last_ran'] = "unknown date"
    await write_json(topics_json, "topics.json")
    print('status set to unknown date')
    schedule_find_papers.start()
    
    print("Ready!")
    

@bot.tree.command(name="clear_history", description="Clear all Paper Bot topic settings and articles (remove all previously found papers from history).")
async def _clear_history(ctx):  
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_json["users"].pop(str(user)) #remove the user from the json
        await write_json(topics_json, "topics.json")

        await send_command_response(ctx, user, "Your history has been cleared! All topic settings and found articles have been removed.") 

@bot.tree.command(name="view_topics", description="View your saved topic settings.")
async def _view_topics(ctx):
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        user_data = topics_json["users"]
        topics_list = user_data[str(user)]['topic_settings']

        embed = discord.Embed(title="Your Topics", description="Here are your current topic settings:", color = 0x99e3ee)
        embed.set_thumbnail(url=profile_pic_url)
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
    if str(user) not in topics_json["users"].keys(): #if this user dosn't exist yet
        topics_json["users"][str(user)] = {'topic_settings': [], 'found_articles': [], 'search_schedule' : [], 'auto_num' : 0, 'auto_message_or_audio' : None} #create a dictionary object for the new user
        discord_user = await bot.fetch_user(user)
        await discord_user.send("Welcome to Paper Bot! I've created a new user profile for you.")

    if recent == 'y':
        recent = 1
    elif recent == 'n':
        recent = 0
    else:
        await send_command_response(ctx, user, "Please use 'y' or 'n' to indicate if you want to restrict the search to recent papers.")
        return

    topics_json["users"][str(user)]['topic_settings'].append({"topic": topic, "recent": recent}) #add the new topic
    await write_json(topics_json, "topics.json")
    
    await send_command_response(ctx, user, "Your new topic has been added!")


@bot.tree.command(name="find_papers_now", description="Find papers based on your topic interests")
async def _find_papers_now(ctx, num_papers : int, message_or_audio : str):
    '''Find papers based on your topic instrests

    Args:
        ctx (Interaction): The context of the command
        num_papers (int): The number of papers you want to find for each topic (Max 5)
        message_or_audio (str): Do you want the AI summary as a message or an audio file (message/audio)?
    '''
    user = ctx.user.id
    if num_papers < 6:
        if message_or_audio == "message" or message_or_audio == "audio":
            if await user_exists(ctx, user):
                await send_command_response(ctx, user, "Finding papers for you...") #sending an initial message b/c if the initial response from the bot takes too long, discord will send a no-response error message
                await find_papers(user, num_papers, message_or_audio)
        else:
            await send_command_response(ctx, user, 'Please specify if you want the summary as "message" or "audio".')
    else: #if they are trying to find more than 5 papers per topic
        await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")

class schedule_button(discord.ui.Button['DayOptions']):
    def __init__(self, day, current_days):
        if day in current_days:
            super().__init__(style=discord.ButtonStyle.green, label = day)
        else:
            super().__init__(style=discord.ButtonStyle.grey, label = day) 
    async def callback(self, ctx: discord.Interaction):
        user = ctx.user.id
        day_selected = self.label

        topics_json = await open_json("topics.json")
        if day_selected in topics_json["users"][str(user)]['search_schedule']: #if the day is already in the schedule
            self.style = discord.ButtonStyle.grey 
            await ctx.response.edit_message(view=self.view) #update the button color
            topics_json["users"][str(user)]['search_schedule'].remove(day_selected) #remove the day from the schedule
        else:
            self.style = discord.ButtonStyle.green
            await ctx.response.edit_message(view=self.view) #update the button color
            topics_json["users"][str(user)]['search_schedule'].append(day_selected)
        print(topics_json["users"][str(user)]['search_schedule'])
        await write_json(topics_json, "topics.json")

class DayOptions(discord.ui.View):
    def __init__(self, current_days):
        super().__init__()
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            self.add_item(schedule_button(day, current_days)) 

@bot.tree.command(name="schedule", description="Set the frequency Paper Bot will automatically find papers and send them to your DM.")
async def _schedule(ctx, number_of_papers : int, message_or_audio : str):
    '''Set on what days Paper Bot will automatically find papers and send them to your DM.

    Args:
        ctx (Interaction): The context of the command
        number_of_papers (int): Number of papers to find per search per topic (Max 5).
        message_or_audio (str): Do you want the AI summary as a message or an audio file (text/audio)?
    '''
    user = ctx.user.id
    if number_of_papers < 6:
        if message_or_audio == "message" or message_or_audio == "audio":
            if await user_exists(ctx, user):
                topics_json = await open_json("topics.json")
                topics_json["users"][str(user)]['auto_num'] = number_of_papers
                topics_json["users"][str(user)]['auto_message_or_audio'] = message_or_audio
                await write_json(topics_json, "topics.json")

                current_days = topics_json["users"][str(user)]['search_schedule']

                await send_command_response(ctx, user, f"Paper Bot will now find {number_of_papers} papers on each day you schedule it")

                discord_user = await bot.fetch_user(user)
                await discord_user.send("Please select (or deselect) what days of the week you want more papers", view=DayOptions(current_days))
        else:
            await send_command_response(ctx, user, 'Please specify if you want the summary as "message" or "audio".')
    else: #if they are trying to find more than 5 papers per topic
        await send_command_response(ctx, user, "You can only find up to 5 papers per topic at a time. Please try again with a smaller number.")


@bot.tree.command(name="summarize_pdf", description="Summarize a PDF file")
async def _summarize_pdf(ctx, pdf : discord.Attachment, message_or_audio : str):
    '''_summary_

    Args:
        ctx (Interaction): Discrod Interaction
        pdf (discord.Attachment): A pdf file of the paper you want to summarize
        message_or_audio (str): Do you want the AI summary as a message or an audio file (text/audio)?
    '''
    user = ctx.user.id
    await send_command_response(ctx, user, "I'm working on summarizing your PDF. This may take a while...")

    await pdf.save(pdf.filename)
    reader = PdfReader(pdf.filename)
    context_txt = ""
    for page in reader.pages:
        context_txt += page.extract_text()
    os.remove(pdf.filename)

    summary_txt = await get_summary_from_LM(context_txt)
    success = await send_summary_to_user(user, summary_txt, message_or_audio, pdf.filename)
    if not success:
        discord_user = await bot.fetch_user(user)
        await discord_user.send("I'm sorry, I couldn't summarize the PDF. Please try again later.")


@bot.tree.command(name="help", description="Learn more about Paper Bot")
async def _help(ctx):
    embed = discord.Embed(title="About Paper Bot", description="Paper Bot is a Discord bot that helps you find and summarize academic papers. You can add topics of interest, schedule automatic paper searches, and more!", color = 0x99e3ee)
    embed.set_thumbnail(url=profile_pic_url)
    embed.add_field(name="How do I get Started?", value="To get started, use the /add_topic command to add a topic of interest. You can then use /find_papers_now to find papers for that topic, or use /schedule to have Paper Bot automatically send you papers every x days.", inline=False)
    embed.add_field(name="Why does Paper Bot not send me a summary for every paper?", value="Paper Bot requires access to the paper to be able to summarize it. Paper Bot uses both Goggle Scholar and web scraping to try to access the paper content, but some journal websites block these methods. For papers that paper bot wasn't able to summarize, you can retrieve the pdf from the provided links and use /summarize_pdf to retrieve the summary.", inline=False)
    embed.add_field(name="Source Code", value="For more information you can check out the public [github repo](https://github.com/biopherret/Paper_Bot)", inline=False)
    await ctx.response.send_message(embed=embed)

class topic_button(discord.ui.Button['TopicOptions']):
    def __init__(self, topic):
        super().__init__(style=discord.ButtonStyle.secondary, label = topic['topic'])
    async def callback(self, ctx: discord.Interaction):
        user = ctx.user.id
        topic_to_remove = self.label

        topics_json = await open_json("topics.json")
        topics_json["users"][str(user)]['topic_settings'] = [topic_dict for topic_dict in topics_json["users"][str(user)]['topic_settings'] if topic_dict['topic'] != topic_to_remove]
        await write_json(topics_json, "topics.json")
    
        await ctx.response.send_message(f'{topic_to_remove} has been removed from your topic list', ephemeral=True)

class TopicOptions(discord.ui.View):
    def __init__(self, topics):
        super().__init__()
        for topic in topics:
            self.add_item(topic_button(topic))

@bot.tree.command(name="remove_topic", description="Allows you to remove any number of your topics.")
async def _remove_topic(ctx: discord.Interaction):
    user = ctx.user.id
    if await user_exists(ctx, user):
        topics_json = await open_json("topics.json")
        topics_list = topics_json["users"][str(user)]['topic_settings']
    
        await ctx.response.send_message("Which topic do you want to remove?", view=TopicOptions(topics_list))

@tasks.loop(hours = 24)
async def schedule_find_papers():
    now = datetime.now()
    current_date = str(now.date())
    topics_json = await open_json("topics.json")
    if topics_json['schedule_loop_last_ran'] == current_date: #if the loop has allready started running today
        print('loop has allready started running today')
        return
    
    print('schedule loop started')
    topics_json['schedule_loop_last_ran'] = currentS_date
    await write_json(topics_json, "topics.json")
    print('status set to schedlue loop started today')

    dev_user = await bot.fetch_user(dev_user_id)

    today = await get_day_of_week()
    topics_json = await open_json("topics.json")
    user_data = topics_json["users"]
    users = [user for user in user_data.keys() if user_data[user]['search_schedule'] != []] #get all users with a search schedule

    await dev_user.send(f"Good morning! It's a {today} and there are {len(users)} users who have schedules set up.")
    for user in users:
        schedule_days = user_data[user]['search_schedule']
        num = user_data[user]['auto_num']
        message_or_audio = user_data[user]['auto_message_or_audio']

        if today in schedule_days:
            await dev_user.send(f"Attempting to send papers to <@{user}>")
            await find_papers(user, num, message_or_audio)
            await dev_user.send(f"Sent papers to <@{user}>")

@schedule_find_papers.before_loop #this executes before the above loop starts
async def before_schedule_find_papers():
    print('schedule loop waiting...')
    target_time = time(hour=9, minute=00)
    next_run_in_seconds = await get_next_run_time(target_time)
    await asyncio.sleep(next_run_in_seconds)

bot.run(discord_token)