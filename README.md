# How to access paper bot
Follow [this link](https://discord.com/oauth2/authorize?client_id=1252693045938491483) to add the bot to either a server you have admin privileges for.

# Getting Started
To make a user profile simply add your first topic of interest
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253850263798808606/image.png?ex=66775a8e&is=6676090e&hm=25633bd244a5b30853bad9740bb837c97403f82da7797146ad8d11aa0a93a43e&=&format=webp&quality=lossless&width=447&height=89">

Then you can find papers either at will using the /find_papers_now command
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253850357013155902/image.png?ex=66775aa4&is=66760924&hm=5081e1befe202a57bc3fc043c9b878b4bc6d0c08356843a2b812aa2fb041380c&=&format=webp&quality=lossless&width=523&height=80">

or using /schedule to schedule paper bot to send you papers every x days at 9AM PST.
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253853300999192657/image.png?ex=66775d62&is=66760be2&hm=a371ff9b8255d176a876a76fb931aba7e2db856f24d6237e8e883bddb59fcae7&=&format=webp&quality=lossless&width=508&height=76">

In both cases Paper Bot will find related papers and send you links to them. And then work on summarizing them.
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253851856351002645/image.png?ex=66775c09&is=66760a89&hm=bd4d7a9b4f321e5765d0fa1b3f15894a37aad3ccd17a1a3f0187e2d84d85e7f4&=&format=webp&quality=lossless&width=224&height=314">

You'll notice that Paper Bot was not able to summarize every paper, this is often because the journal website blocks web scraping, so Paper Bot isn't able to get the paper content. 

When this happens, you can use the links provided in the first message to find a pdf of the paper and directly ask for a summary using /summarize_pdf
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253852634016645161/image.png?ex=66775cc3&is=66760b43&hm=a6d0293c2067d52f4564a2462c412517d3bf6dabd592b989af051e9bdf5b4245&=&format=webp&quality=lossless&width=533&height=288">
<img src="https://media.discordapp.net/attachments/1099433298914189393/1253852824111026226/image.png?ex=66775cf0&is=66760b70&hm=2b8515bd666d0ee1017c35306c75c5dbce2546d888aeb09f775c8f34e980f9d2&=&format=webp&quality=lossless&width=447&height=187">

# Commands
/add_topic lets you add new topics to your user profile

/view_topics will show you your current topic settings

/remove_topic will let you remove up too all of your current topics

/find_papers_now will find papers from each of your topics, and summarize them for you

/schedule allows you to set a schedule for how often you want Paper Bot to automatically send you papers

/summarize_pdf lets you send Paper Bot a pdf of a particular paper for it to summarize

/clear_history will completely remove your user profile (topics, found articles, and schedule)