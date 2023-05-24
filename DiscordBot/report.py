from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    CATEGORY_CHOSEN = auto()
    CHOOSE_TYPE1 = auto()
    CHOOSE_TYPE2 = auto()
    CHOOSE_TYPE3 = auto()
    CHOOSE_TYPE4 = auto()
    # PROVIDE_CONTEXT = auto()
    # USER_INPUT = auto()
    BLOCK_STATE = auto()
    REPORT_COMPLETE = auto()
    ADDITIONAL_INFORMATION = auto()



class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    NUM_REPORTS = 0
    REPORTS = []

    ABUSE_TYPES = ['1', '2', '3', '4']
    YES_NO = ['1', '2']

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

            embed.set_footer(text="Ex: To select 'False/misleading information', type `1`.")
            self.state = State.CATEGORY_CHOSEN

            return [{"content":reply, "embed":embed}]
        
        if self.state == State.CATEGORY_CHOSEN:
            if message.content not in self.ABUSE_TYPES:
                return ["Unrecognized option. Please choose from the above options."]
            elif message.content == "1":
                self.state = State.CHOOSE_TYPE1
                reply = ""
                embed = Report.type1_embed()
            elif message.content == "2":
                self.state = State.CHOOSE_TYPE2
                reply = ""
                embed = Report.type2_embed()
            elif message.content == "3":
                self.state = State.CHOOSE_TYPE3
                reply = ""
                embed = Report.type3_embed()
            elif message.content == "4":
                self.state = State.CHOOSE_TYPE4
                reply = ""
                embed = Report.type4_embed()
            return [{"content":reply, "embed":embed}]
        
        if self.state == State.CHOOSE_TYPE1:
            self.state = State.ADDITIONAL_INFORMATION
            embed = discord.Embed(
                color = discord.Colour.dark_blue(),
                title="Would you be able to provide additional information about this disinformation?"
            )

            embed.add_field(
                name = "1",
                value = "Yes. I have additional information to provide",
                inline = False
            )

            embed.add_field(
                name = "2",
                value = "No. I do not have additional information to provide",
                inline = False
            )

            embed.set_footer(text="Ex: To provide additional information, type `1`.")
            return [{"content":reply, "embed":embed}]
        
        if self.state != State.CHOOSE_TYPE1:
            self.state = State.BLOCK_STATE
        
        if self.state == State.ADDITIONAL_INFORMATION:
            if message.content not in self.YES_NO:
                return ["Unrecognized option. Please choose from the above options."]
            elif message.content == "1":
                msg = await self.client.wait_for("message")
                if msg:
                    self.REPORTS.append(msg)
                    self.NUM_REPORTS += 1
                self.state = State.BLOCK_STATE
                return ["Thank you for your report!"]
            elif message.content == "2":
                self.state = State.BLOCK_STATE

    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
    
    @classmethod
    def type1_embed(cls):
        embed = discord.Embed(
            color=discord.Colour.dark_blue(),
            title="What type of false/misleading information does the message fall under?"
        )

        embed.add_field(name="(1)",
                        value="Quoting out of context",
                        inline=False)
        embed.add_field(name="(2)",
                        value="Exaggerated claims",
                        inline=False)
        embed.add_field(name="(3)",
                        value="Selective Reporting",
                        inline=False)

        embed.set_footer(text="Ex: To select 'Quoting out of context', type `1`.")

        return embed
    
    @classmethod
    def type2_embed(cls):
        embed = discord.Embed(
            color=discord.Colour.dark_blue(),
            title="What type of harassment/bullying does the message fall under?"
        )

        embed.add_field(name="(1)",
                        value="Sexual Harassment",
                        inline=False)
        embed.add_field(name="(2)",
                        value="Doxxing",
                        inline=False)
        embed.add_field(name="(3)",
                        value="Stalking",
                        inline=False)
        embed.add_field(name="(4)",
                        value="Threat or Personal Attack",
                        inline=False)

        embed.set_footer(text="Ex: To select 'Sexual Harassment', type `1`.")

        return embed
    
    @classmethod
    def type3_embed(cls):
        embed = discord.Embed(
            color=discord.Colour.dark_blue(),
            title="What type of fraud/scam does the message fall under?"
        )

        embed.add_field(name="(1)",
                        value="Phishing",
                        inline=False)
        embed.add_field(name="(2)",
                        value="Identity Fraud",
                        inline=False)
        embed.add_field(name="(3)",
                        value="Product Scam",
                        inline=False)
        embed.add_field(name="(4)",
                        value="Fake/Bot Account",
                        inline=False)

        embed.set_footer(text="Ex: To select 'Phishing', type `1`.")

        return embed
    
    @classmethod
    def type4_embed(cls):
        embed = discord.Embed(
            color=discord.Colour.dark_blue(),
            title="Please report how the content was violent or harmful."
        )

        embed.add_field(name="(1) Graphic Violence",
                    inline=False)
        embed.add_field(name="(2) Child Exploitation",
                        inline=False)
        embed.add_field(name="(3) Terrorist Content",
                        inline=False)
        embed.add_field(name="(4) Non-Consensual Explicit Content",
                        inline=False)

        embed.set_footer(text="Ex: To select 'Graphic Violence', type `1`.")

        return embed


    

# git add .
# git commit -m ""
# git push origin branchname