import tweepy
from airtable import Airtable
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
import schedule
import time
import os
import asyncio
import re
import json



from twikit import Client

# Helpful when testing locally
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USERNAME = os.getenv("USERNAME")
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# TwitterBot class to help us organize our code and manage shared state
class TwitterBot:
    def __init__(self):
        
        self.llm = ChatOpenAI(temperature=.5, openai_api_key=OPENAI_API_KEY, model_name='gpt-4o')

        # For statics tracking for each run. This is not persisted anywhere, just logging
        self.mentions_found = 0
        self.mentions_replied = 0
        self.mentions_replied_errors = 0
        self.client = None
        
    async def ensure_logged_in(self):
        if self.client is None:
            self.client = Client('en-US')
        try:
            self.client.load_cookies('cookies.json')
        except:
            await self.client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD
            )
            self.client.save_cookies('cookies.json')
    async def send_tweet(self, text):
        if self.client is None:
            self.client = Client('en-US')
            await self.client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD
        )
        await self.client.create_tweet(text)
        

    async def generate_Tweet_text(self):
        system_template = """
            You are karl marx , you give startup ideas that combine absurdity with a dash of Marxist philosophy, poking fun at capitalist structures while imagining comically extreme socialist alternatives.
            Your goal is to provide a concise startup business plan that is absurdly funny and comical.
            
            % RESPONSE TONE:
            
            - Your tone should be serious w/ a hint of wit and sarcasm
            
            % RESPONSE FORMAT:

            - Respond in under 200 characters
            - Respond in two or less short sentences
            - Do not respond with emojis
            
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

        human_template="give me the startup idea"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        final_prompt = chat_prompt.format_prompt().to_messages()
        response = self.llm(final_prompt).content
        return response
    async def reply(self,que,orig):
        system_template = """
            You are karl marx , you give startup ideas that combine absurdity with a dash of Marxist philosophy, poking fun at capitalist structures while imagining comically extreme socialist alternatives.
            Your goal is to reply to ques that has been asked by the user about your previously generated response that is {original}.
            
            % RESPONSE TONE:
            
            - Your tone should be serious w/ a hint of wit and sarcasm
            
            % RESPONSE FORMAT:

            - Respond in under 200 characters
            - Respond in two or less short sentences
            - Do not respond with emojis
            
            % RESPONSE CONTENT:
            - Your response should be a reply to the user's question
            - your reply should be funny and comical
            
        """
        system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

        human_template="{text}"
        human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

        chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

        final_prompt = chat_prompt.format_prompt(text=que,original=orig).to_messages()
        response = self.llm(final_prompt).content
        return response
    
    async def search_for_tweets(self):
        await self.ensure_logged_in()
        user = await self.client.get_user_by_screen_name('BotChief87172')
        tweets = await user.get_tweets('Tweets', count=50)
        return tweets
    async def get_replies(self,tweets):
        replies = []
        for tweet in tweets:
            # print(tweet.reply_count)
            if tweet.reply_count > 0:
                print(tweet.text)
                # print(tweet.id)
                tw = await self.client.get_tweet_by_id(tweet.id)
                for repli in tw.replies:
                    replies.append({
                        'text': repli.text,
                        'id': repli.id,
                        "replied": False,
                        "user": repli.user.id,
                        "original": tweet.text
                        })
            
        return replies
    def merge_dict_lists(self,list1, list2):
        merged_dict = {}
        for d in list1 + list2:
            key = d['id']  # Use the id as the unique key
            if key in merged_dict:
                # Prefer the dictionary with replied: true
                if d['replied']:
                    merged_dict[key] = d
            else:
                merged_dict[key] = d
        return list(merged_dict.values())
    def save_replies(self,replies):
        
        with open('replies.json', 'r') as f:
            json_data = json.load(f)
        new_replies = self.merge_dict_lists(json_data,replies)
        with open('replies.json', 'w') as f:
            json.dump(new_replies, f)
        
    async def create_tweet(self,text,id):
        await self.client.create_tweet(text,reply_to=id)
    async def reply_to_tweet(self):
        with open('replies.json', 'r') as f:
            replies = json.load(f)
            print(replies)
        for reply in replies:
            if reply['replied'] == False:
                ai_message = await self.reply(reply['text'],reply['original'])
                print(ai_message)
                await self.create_tweet("hello buddy",reply['id'])
                reply['replied'] = True
                with open('replies.json', 'w') as f:
                    json.dump(replies, f)
        
async def job():
    bot = TwitterBot()
    
    tweets = await bot.search_for_tweets()
    replies = await bot.get_replies(tweets)
    print(replies)
    bot.save_replies(replies)
    await bot.reply_to_tweet()
    
if __name__ == "__main__":
    # Schedule the job to run every 5 minutes. Edit to your liking, but watch out for rate limits
    schedule.every(30).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)