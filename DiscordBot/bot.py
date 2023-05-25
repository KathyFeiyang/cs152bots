# bot.py
from collections import defaultdict
from datetime import datetime
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb

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


FALSE_REPORTING_LIMIT = 1


class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.messages = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        # TODO: order reports by priority
        self.reports = {} # Map from user IDs to the state of their report
        # TODO: manage moderator - report assignments
        self.moderators = moderators
        self.moderator_assignments = {}
        self.false_report_history = defaultdict(list)


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
                if len(self.reports) == 0:
                    await message.channel.send(
                        'There are no active reports to moderate. Thank you for checking.')
                    return
                else:
                    self.moderator_assignments[author_id] = next(iter(self.reports.keys()))
            await self.process_message(
                message=message,
                author_id=self.moderator_assignments[author_id])
            # If the report is complete or cancelled, remove it from our map
            if (self.reports[self.moderator_assignments[author_id]].report_complete()
                or self.reports[self.moderator_assignments[author_id]].report_escalated()):
                reporting_user = await self.fetch_user(int(self.moderator_assignments[author_id]))
                await reporting_user.send((
                    f'Your earlier report has been resolved: {self.reports[self.moderator_assignments[author_id]].state}'))
                mod_channel = discord.utils.get(
                    self.get_all_channels(),
                    name=f'group-{self.group_num}-mod') 
                await mod_channel.send(self.mod_summary(
                    self.moderator_assignments[author_id],
                    self.reports[self.moderator_assignments[author_id]]))
                stats = self.reports[self.moderator_assignments[author_id]].report_stats()
                if stats['false_reporting']:
                    self.false_report_history[str(stats['reporting_user'])].append(datetime.now())
                    print(stats)
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
                else:
                    await message.channel.send(
                        'You are temporarily suspended from making reports because you have made too many false reports recently.'
                        ' We apologize for the inconveninence. If you believe this is a mistake, please contact us at XXX-XXX-XXXX.')
                    return
            await self.process_message(
                message=message,
                author_id=author_id)
            # TODO: support reporting of users, in addition to content


    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        scores = self.eval_text(message.content)
        await mod_channel.send(self.code_format(scores))

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        # TODO: swap with model in milestone 3
        if 'disinformation' in message.lower():
            return 1
        else:
            return 0

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


    def mod_summary(self, user_id, report):
        summary = '**MODERATION UPDATE**\n'
        summary += f'- Reporting user [{user_id}]\n'
        summary += f'{report.report_summary()}\n'
        return summary


client = ModBot()
client.run(discord_token)
