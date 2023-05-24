from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    CHOOSE_CATEGORY = auto()
    BLOCK_STATE = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

    ABUSE_TYPES = ['1', '2', '3', '4']

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
    
    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        if self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            return [reply]
        
        if self.state == State.AWAITING_MESSAGE:
            # Parse out the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Here we've found the message - it's up to you to decide what to do next!
            self.state = State.MESSAGE_IDENTIFIED
            
        if self.state == State.MESSAGE_IDENTIFIED:
            reply = "I found this message:", "```" + message.author.name + ": " + message.content + "```"
            
            embed = discord.Embed(
                color = discord.Colour.dark_blue(),
                title="Please choose the category of disinformation that best describes your reason for reporting"
            )

            embed.add_field(
                name="(1)",
                value="False/misleading information",
                inline=False
            )

            embed.add_field(
                name="(2)",
                value="Harassment and Bullying",
                inline=False
            )

            embed.add_field(
                name="(3)",
                value="Fraud and Scams",
                inline=False
            )

            embed.add_field(
                name="(4)",
                value="Violent and Harmful content",
                inline=False
            )

            embed.set_footer(text="Please type the number corresponding to the category.")
            self.state = State.CHOOSE_CATEGORY

            return [{"content": reply, "embed": embed}]

        if self.state == State.BLOCK_STATE:

            embed = discord.Embed(
                color=discord.Colour.dark_blue(),
                title="Would you like to block the content or user?"
            )

            embed.add_field(
                name="(1)",
                value="Block user",
                inline=False
            )

            embed.add_field(
                name="(2)",
                value="Block content",
                inline=False
            )

            embed.add_field(
                name="(3)",
                value="Block user and content",
                inline=False
            )

            embed.add_field(
                name="(4)",
                value="Do not block",
                inline=False
            )

            embed.set_footer(text="Please type the number corresponding to your choice.")

            reply = None
            if message.content in self.ABUSE_TYPES:
                self.state = State.REPORT_COMPLETE
                if message.content == '1':
                    reply = "The user was successfully blocked."
                elif message.content == '2':
                    reply = "The content was successfully blocked."
                elif message.content == '3':
                    reply = "The user and content were successfully blocked"
                else:
                    reply = "Neither the user nor content was blocked."
            else:  # In case the input is not within the ABUSE_TYPES
                reply = "Please choose a valid option by typing the corresponding number (1, 2, 3, or 4)."

            return [{"content": reply, "embed": embed}]

        def report_complete(self):
            if self.state == State.REPORT_COMPLETE:
                return "We've received your report! " \
                       "Thank you for taking the time to help keep our community safe and truthful." \
                       " Our content moderation team will promptly review the report"
            else:
                return "Your report is still in progress. Please continue to provide the necessary information."



    

