# bot.py
from collections import defaultdict
from datetime import datetime
import discord
from discord.ext import commands
from enum import Enum, auto
import os
import json
import logging
import re
import requests
from report import Report
import pdb
import pprint
import queue
import random

import gpt4_classifier


# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']

MODERATOR_LIST_PATH = 'moderators.json'
if not os.path.isfile(MODERATOR_LIST_PATH):
    raise Exception(f"{MODERATOR_LIST_PATH} not found!")
with open(MODERATOR_LIST_PATH) as f:
    moderators = json.load(f)

API_KEY_PATH = 'key.json'
FALSE_REPORTING_LIMIT = 5
LOW_MID_TH = 0.2
MID_HIGH_TH = 0.8
DISTRIBUTION_TH = 6
VULNERABILITY_TH = 6
MODEL_AUTHOR_ID = 'AUTO_FLAGGING_MODEL'
MAX_QUEUE_SIZE = 1000000
OVERRIDE_HIGH_PRIORITY = 'Special attention needed'


class Mode(Enum):
    RAPID_RESPONSE_TO_HARM = auto()
    BEST_ACCURACY = auto()


class Classifier(Enum):
    GPT4 = auto()
    ROBERTA_FAKENEWS = auto()


# Simple priority queue implementation to rank reports by urgency 1-10
class PriorityQueue:
    def __init__(self):
        self.queue = []

    def is_empty(self):
        return len(self.queue) == 0

    def enqueue(self, item, priority):
        self.queue.append((item, priority))
        self.queue.sort(key=lambda x: x[1], reverse=True)

    def dequeue(self):
        if self.is_empty():
            raise Exception("Priority queue is empty.")
        return self.queue.pop(0)[0]

    def peek(self):
        if self.is_empty():
            raise Exception("Priority queue is empty.")
        return self.queue[0][0]


class ModBot(discord.Client):
    def __init__(self, mode, classifier_type): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.high_priority_queue = queue.PriorityQueue(maxsize=MAX_QUEUE_SIZE)
        self.low_priority_queue = queue.PriorityQueue(maxsize=MAX_QUEUE_SIZE) #Order reports by priority
        self.reports = {} # Map from user IDs to the state of their report
        self.moderators = moderators
        self.moderator_assignments = {}
        self.false_report_history = defaultdict(list)
        self.mode = mode
        if classifier_type == Classifier.GPT4:
            if not os.path.isfile(API_KEY_PATH):
                raise Exception(f"{API_KEY_PATH} not found!")
            with open(API_KEY_PATH) as f:
                api_key = json.load(f)['key']
            self.classifier = gpt4_classifier.GPT4MisinformationClassifier(api_key)
        else:
            self.classifier = None

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)


    async def process_message(self, message, author_id):
        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            if isinstance(r, dict):
                    await message.channel.send(r["content"], embed = r["embed"])
            else:
                await message.channel.send(r)


    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "- Use the `report` command to begin the reporting process.\n"
            reply += "- Use the `cancel` command to cancel the report process.\n"
            reply += "- [Moderators] Use the `moderate` command to begin the moderation process.\n"
            reply += "- [Moderators] Start with `as user:` to act as a regular user.\n"
            await message.channel.send(reply)
            return

        author_id = str(message.author.id)

        # Only respond to messages if they're part of a reporting or moderator flow
        if ((author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD)) and
            (author_id not in self.moderators and not message.content.startswith(Report.MOD_START_KEYWORD))):
            return

        if author_id in self.moderators and not message.content.startswith(Report.USER_OVERRIDE):
            print('running as mod')
            if author_id in self.moderator_assignments:
                await message.channel.send('`...ongoing moderation...`')
            else:
                print('\n[DEBUG] Priority queues')
                print(self.high_priority_queue.qsize())
                print(self.low_priority_queue.qsize())
                # Get next report with highest priority
                if not self.high_priority_queue.empty():
                    _, next_report = self.high_priority_queue.get()
                elif not self.low_priority_queue.empty():
                    _, next_report = self.low_priority_queue.get()
                else:
                    await message.channel.send(
                        'There are no active reports to moderate. Thank you for checking.')
                    return
                self.moderator_assignments[author_id] = next_report
            await self.process_message(
                message=message,
                author_id=self.moderator_assignments[author_id])
            # If the report is complete or cancelled, remove it from our map
            if (self.reports[self.moderator_assignments[author_id]].report_complete()
                or self.reports[self.moderator_assignments[author_id]].report_escalated()):
                if not MODEL_AUTHOR_ID in self.moderator_assignments[author_id]:
                    reporting_user = await self.fetch_user(int(self.moderator_assignments[author_id]))
                    await reporting_user.send((
                        f'Your earlier report has been resolved: {self.reports[self.moderator_assignments[author_id]].final_action}'))
                mod_channel = discord.utils.get(
                    self.get_all_channels(),
                    name=f'group-{self.group_num}-mod') 
                await mod_channel.send(self.mod_summary(
                    self.moderator_assignments[author_id],
                    self.reports[self.moderator_assignments[author_id]]))
                stats = self.reports[self.moderator_assignments[author_id]].report_stats()
                if stats['false_reporting'] and not MODEL_AUTHOR_ID in stats['reporting_user']:
                    self.false_report_history[str(stats['reporting_user'])].append(datetime.now())
                    print('False reporting updated:', stats)
                self.reports.pop(self.moderator_assignments[author_id])
                self.moderator_assignments.pop(author_id)
        else:
            print('running as user')
            if author_id in self.moderators and message.content.startswith(Report.USER_OVERRIDE):
                message.content = message.content.split(Report.USER_OVERRIDE)[-1].strip()
            # print('message content in reporting flow:', message.content)
            # If we don't currently have an active report for this user, add one
            if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
                return
            if author_id not in self.reports and message.content.startswith(Report.START_KEYWORD):
                if len(self.false_report_history[author_id]) < FALSE_REPORTING_LIMIT:
                    self.reports[author_id] = Report(self)
                    # Generate a priority and assign to appropriate queue
                    score, info = self.run_disinfo_model(message)
                    priority = int(score * 10)
                    self.assign_report_priority(author_id, priority)
                else:
                    await message.channel.send(
                        'You are temporarily suspended from making reports because you have made too many false reports recently.'
                        ' We apologize for the inconveninence. If you believe this is a mistake, please contact us at XXX-XXX-XXXX.')
                    return
            await self.process_message(
                message=message,
                author_id=author_id)


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        score, info = self.run_disinfo_model(message)
        priority, further_moderation_needed = self.compute_priority(
            message, score, info)
        info['priority'] = priority
        print('\n[DEBUG] handle_channel_message')
        print(score, info, priority, further_moderation_needed)
        if further_moderation_needed or (OVERRIDE_HIGH_PRIORITY in info and info[OVERRIDE_HIGH_PRIORITY]):
            reporting_user_id = f'{MODEL_AUTHOR_ID}_{datetime.now()}'
            self.reports[reporting_user_id] = Report(
                client=self,
                message=message,
                reporting_user_id=reporting_user_id,
                score=score,
                info=info)
            self.assign_report_priority(
                reporting_user_id,
                priority,
                override_high_priority=OVERRIDE_HIGH_PRIORITY in info and info[OVERRIDE_HIGH_PRIORITY])
            print(f'Auto flagged message filed as report for {reporting_user_id}')

            # Forward the message to the mod channel
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(self.code_format(message, score, info))


    def compute_priority(self, message, score, info):
        if score <= LOW_MID_TH:
            return 0, False
        elif score > MID_HIGH_TH:
            return 0, True
        if self.mode == Mode.RAPID_RESPONSE_TO_HARM:
            distribution_score = self.get_distribution_score(message)
            vulnerability_score = self.get_vulnerability_score(message)
            if (distribution_score > DISTRIBUTION_TH or
                vulnerability_score > VULNERABILITY_TH):
                priority = max(
                    distribution_score,
                    vulnerability_score,
                    6,
                    int(score * 10))
        else:
            priority = int(score * 10)
        return priority, True


    def assign_report_priority(self, author_id, priority, override_high_priority=False):
        if priority <= 5 and not override_high_priority:
            self.low_priority_queue.put((-1. * priority, author_id))
        else:
            self.high_priority_queue.put((-1. * priority, author_id))

    
    def code_format(self, message, score, info):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return (
            f'**AUTO FLAGGING**\n{message.author.name}: "{message.content}"\n'
            f'- Score: {score:.3f}\n'
            f'- Info: {pprint.pformat(info, indent=4)}\n')


    def run_disinfo_model(self, message):
        score, classification = self.classifier.classify_message(message.content)
        info = {
            'score': score,
            'classification': classification,
            OVERRIDE_HIGH_PRIORITY: random.random() > 0.5,
        }
        print(f'\n[DEBUG] disinfo model: {score}, {info}')
        return score, info


    def get_distribution_score(self, message):
        # Dummy function
        return random.randint(1, 11)


    def get_vulnerability_score(self, message):
        # Dummy function
        return random.randint(1, 11)


    def mod_summary(self, user_id, report):
        summary = '**MODERATION UPDATE**\n'
        summary += f'- Reporting user [{user_id}]\n'
        summary += f'{report.report_summary()}\n'
        return summary


if __name__ == '__main__':
    MODE = Mode.BEST_ACCURACY
    CLASSIFIER_TYPE = Classifier.GPT4

    client = ModBot(
        mode=MODE,
        classifier_type=CLASSIFIER_TYPE)
    client.run(discord_token)
