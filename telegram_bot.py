
from telebot.async_telebot import AsyncTeleBot
#from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import re
import os
import sys

"""import the classes from the other repos, this classes works standalone too,
    they are very importat becouse are the core of this projects and of those to come """
from twitter_video_scraper import TwitterVideoScraper
from twitter_video_scraper_with_login import TwitterVideoScraperLogin
from tiktok_video_scraper_web import TikTokVideoScraperWeb
from tiktok_video_scraper_mobile_v2 import TikTokVideoScraperMobile
from instagram_post_scraper import InstagramPostScraper
from instagram_stories_scraper import InstagramStoryScraper
from reddit_video_scraper import RedditVideoScraper

#######################################################################
#TODO 
#   - improve reddit json parsing
#  
#######################################################################

# set your access token
# (see a Telegram BotFather tutorial)
bot = AsyncTeleBot('your bot token')

#######################################################################

@bot.message_handler(commands=['start'])
async def message_handler(message):
    """ this method is executed each time a user send /start to the bot, 
        its important becouse you can store user id, user name and other
        info that messege object have """
    print(f'welcome {message.from_user.username}')
    print(f'now u can download videos from socials ')

"""-----------------------------------------------------------------"""

@bot.message_handler()
async def get_videos(message):
    """ this method is executed each time a message is received 
        extract the url from the given text, 
        check what social the request is from,
        run the recognized scraper for that social """
    
    # regex to extract urls from the text given
    extract_url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    try:
        video_url = re.findall(extract_url_regex, message.text)[0][0]
    except Exception as e:
        print('error finding url on given text')
        return

    site = check_site(video_url)
    if site:
        # twitter
        if site == 'Twitter':
            video_list, video_thumbnails, video_nsfw = await run_twitter_video_scraper(video_url)
            send_video_result = await send_video_to_telegram(video_list, message.chat.id, message.message_id)
            if send_video_result == True:
                print('videos sent successfully')

        # tiktok
        elif site == 'TikTok':
            video_list, video_thumbnail = await run_tiktok_video_scraper(video_url)
            send_video_result = await send_video_to_telegram(video_list, message.chat.id, message.message_id)
            if send_video_result == True:
                print('videos sent successfully')

        # instagram
        elif site == 'Instagram':
            # stories / this need login
            if '/s/' in video_url or '/stories/' in video_url:
                video_list, video_thumbnails = await run_instagram_stories_scraper(video_url)
                send_video_result = await send_video_to_telegram(video_list, message.chat.id, message.message_id)
                if send_video_result == True:
                    print('videos sent successfully')
            # posts, reels
            else:
                video_list, video_thumbnails = await run_instagram_post_scraper(video_url)
                send_video_result = await send_video_to_telegram(video_list, message.chat.id, message.message_id)
                if send_video_result == True:
                    print('videos sent successfully')
        
        # reddit
        elif site == 'Reddit':
            video_list, video_thumbnail, video_nsfw = await run_reddit_video_scraper(video_url)
            send_video_result = await send_video_to_telegram(video_list, message.chat.id, message.message_id)
            if send_video_result == True:
                print('videos sent successfully')       

"""-----------------------------------------------------------------"""

async def run_twitter_video_scraper(video_url: str) -> tuple:

    # create scraper video object
    tw_video = TwitterVideoScraper()

    # set the proxy (optional, u can run it with ur own ip)
    #tw_video.set_proxies('<your http proxy>', '<your https proxy')

    # get post id from url, this method recive the video url to scrap
    restid = tw_video.get_restid_from_tw_url(video_url)

    # get guest token, set it in cookies
    tw_video.get_guest_token()

    # get video url and thumbnails from video id
    video_url_list, video_thumbnails, video_nsfw = tw_video.get_video_url_by_id_graphql(restid)
    #video_url_list = tw_video.get_video_url_by_id_syndication(restid)

    # if its nsfw content, use TwitterVideoScraperLogin
    if video_nsfw == True:
        tw_video.tw_session.close()
        return await run_twitter_video_scraper_login(video_url)
    else:
        # get item filesize
        items_filesize = tw_video.get_video_filesize(video_url_list)
        #[print('filesize: ~' + filesize + ' bytes') for filesize in items_filesize]

        # download video by url
        downloaded_video_list = tw_video.download(video_url_list)

        # fix video to make it shareable (optional, but e.g android reject the default format)
        # remember install ffmpeg to use this method
        fixed_video_list = tw_video.ffmpeg_fix(downloaded_video_list)

        tw_video.tw_session.close()

        return fixed_video_list, video_thumbnails, False

"""-----------------------------------------------------------------"""
async def run_twitter_video_scraper_login(video_url: str) -> tuple:
    
    # set your username and password
    username = 'your twitter username'
    password = 'your twitter password'

    cookies_path = 'tw_cookies'

    # create scraper video object
    tw_video = TwitterVideoScraperLogin()

    # set the proxy (optional, u can run it with ur own ip),
    #tw_video.set_proxies('<your http proxy>', '<your https proxy')

    # get post id from url
    restid = tw_video.get_restid_from_tw_url(video_url)

    # get guest token, set it in cookies
    tw_video.get_guest_token()

    # perform login
    tw_video.tw_login(username, password, cookies_path)

    # get video url and thumbnails from video id
    video_url_list, video_thumbnails, video_nsfw = tw_video.get_video_url_by_id_graphql(restid)

    # perform logout, if u use this method u should delete tw_cookies
    #tw_video.tw_logout()

    # get the videos filesize
    items_filesize = tw_video.get_video_filesize(video_url_list)
    #[print('filesize: ~' + filesize + ' bytes') for filesize in items_filesize]
        
    # download video by url
    downloaded_video_list = tw_video.download(video_url_list)

    # fix video to make it shareable (optional, but e.g android reject the default format)
    # remember install ffmpeg if u dont have it
    fixed_video_list = tw_video.ffmpeg_fix(downloaded_video_list)

    tw_video.tw_session.close()

    return fixed_video_list, video_thumbnails, video_nsfw

"""-----------------------------------------------------------------"""
async def run_tiktok_video_scraper(video_url: str) -> tuple:
    
    # create scraper video object
    tiktok_video = TikTokVideoScraperWeb()

    # set the proxy (optional, u can run it with ur own ip)
    #tiktok_video.set_proxies('<your http proxy>', '<your https proxy')

    # get video id from url
    video_id = tiktok_video.get_video_id_by_url(video_url)
    
    # get video url from video id
    try:
        tiktok_video_url, video_thumbnail = tiktok_video.get_video_data_by_video_url(video_url)
    except SystemExit as e:    
    # if web scraper fails, try with the mobile scraper
        tiktok_video_mobile = TikTokVideoScraperMobile()
        tiktok_video_url, video_thumbnail = tiktok_video_mobile.get_video_data_by_video_id(video_id)
    # get the video filesize
    video_size = tiktok_video.get_video_filesize(tiktok_video_url)
    print(f'filesize: ~{video_size} bytes')

    # download video by url
    downloaded_video_list = tiktok_video.download(tiktok_video_url, video_id)

    tiktok_video.tiktok_session.close()

    return downloaded_video_list, video_thumbnail

"""-----------------------------------------------------------------"""

async def run_instagram_stories_scraper(video_url: str) -> tuple:

    # set your ig username and password
    your_username = 'your instagram username'
    your_password = 'your instagram password'
    cookies_path = 'ig_cookies'

    # create scraper post object    
    ig_story = InstagramStoryScraper()

    # set the proxy (optional, u can run it with ur own ip),
    # It is recommended that you use trusted proxies because 
    # you are giving your credentials
    #ig_story.set_proxies('<your http proxy>', '<your https proxy')

    # get the username and story id by url
    username, story_id = ig_story.get_username_storyid(video_url)

    # get the user id or highlights id
    user_id = ig_story.get_userid_by_username(username, story_id)

    # perform login or load cookies
    ig_story.ig_login(your_username, your_password, cookies_path)

    # get the stories urls (sequential with get_story_filesize)
    stories_urls, thumbnail_urls = ig_story.get_ig_stories_urls(user_id)

    # get the video filesize (sequential with get_ig_stories_urls)
    storysize = ig_story.get_story_filesize(stories_urls)
    #[print('filesize: ~' + filesize + ' bytes') for filesize in storysize]

    # download the stories
    downloaded_stories_list = ig_story.download(stories_urls)

    ig_story.ig_session.close()

    return downloaded_stories_list, thumbnail_urls

"""-----------------------------------------------------------------"""
async def run_instagram_post_scraper(video_url: str) -> tuple:

    # create scraper post object    
    ig_post = InstagramPostScraper()
    
    # set the proxy (optional, u can run it with ur own ip)
    #ig_post.set_proxies('<your http proxy>', '<your https proxy')
    
    # get video id from url    
    post_id = ig_post.get_post_id_by_url(video_url)

    # get csrf token
    csrf_token = ig_post.get_csrf_token(post_id)

    # get post urls from video id
    ig_post_urls, video_thumbnails = ig_post.get_ig_post_urls(csrf_token, post_id)

    # get item filesize
    items_filesize = ig_post.get_video_filesize(ig_post_urls)
    #[print('filesize: ~' + filesize + ' bytes') for filesize in items_filesize]

    # download post items
    downloaded_item_list = ig_post.download(ig_post_urls, post_id)

    ig_post.ig_session.close()

    return downloaded_item_list, video_thumbnails

"""-----------------------------------------------------------------"""

async def run_reddit_video_scraper(video_url: str) -> tuple:

    # create scraper video object
    reddit_video = RedditVideoScraper()

    # set the proxy (optional, u can run it with ur own ip)
    #reddit_video.set_proxies('<your http proxy>', '<your https proxy')

    # get video info from url
    reddit_video_info = reddit_video.get_video_json_by_url(video_url)

    # get the video details
    reddit_video_urls, video_thumbnail, video_nsfw = reddit_video.reddit_video_details(reddit_video_info)
    
    # get the video filesize
    video_size = reddit_video.get_video_filesize(reddit_video_urls['video_url'], reddit_video_urls['audio_url'])
    #print(f'filesize: ~{video_size} bytes')

    # download the video and audio
    download_details = reddit_video.download(reddit_video_urls)

    # join the video and audio
    # remember install ffmpeg if u dont have it
    downloaded_video_list = reddit_video.ffmpeg_mux(download_details)

    reddit_video.reddit_session.close()

    return downloaded_video_list, video_thumbnail, video_nsfw

"""-----------------------------------------------------------------"""

async def send_video_to_telegram(video_list: list, message_chat_id: str, message_id: str) -> bool:
    """ send the video or img to telegram user, differentiates whether it is an image or a video, 
        and then deletes the sent file from disk """

    for video_name in video_list:
        try:
            with open(video_name, 'rb') as video_or_pic:
                # if its mp4, send like video
                if os.path.splitext(video_name)[1] == '.mp4':
                    await bot.send_video(message_chat_id, video_or_pic, reply_to_message_id=message_id)
                else:
                    await bot.send_photo(message_chat_id, video_or_pic, reply_to_message_id=message_id)
            # in this case delete the video from your disk, but you can keep it
            os.system(f'rm {video_name}') 
        except Exception as e:
            print(e, "\nError on line {}".format(sys.exc_info()[-1].tb_lineno))
            return False
    return True

"""-----------------------------------------------------------------"""

def check_site(url: str) -> tuple[str, bool]:
    """ check what type of url was entered and classify it, 
        if the social is not supported it returns false """

    #instagram
    if 'instagram.com' in url:
        return 'Instagram' 
    #twitter
    if 'twitter.com' in url or 'x.com' in url:
        return 'Twitter'
    #tiktok
    if 'tiktok.com' in url:
        return 'TikTok'
    #reddit
    if 'reddit.com' in url or 'redd.it' in url:
        return 'Reddit'
    
    return False

#######################################################################

if __name__ == '__main__':
    asyncio.run(bot.polling(non_stop=True))