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
    BLOCK_STATE = auto()
    IN_REVIEW_STATE = auto()
    REPORT_COMPLETE = auto()
    MOD_START = auto()
    MOD_1 = auto()
    MOD_2 = auto()
    MOD_3 = auto()
    MOD_4 = auto()
    EMERGENCY = auto()
    HIGHER_LEVEL_MOD = auto()
    ADDITIONAL_INFORMATION = auto()


class Report:
    # User reporting
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    USER_OVERRIDE = "as user:"

    # Moderation
    MOD_START_KEYWORD = 'moderate'
    DISINFO_CATEGORIES = [
        '1. Conspiracy theory',
        '2. Fabricated information',
        '3. Misleading information',
        '4. Imposter',
        '5. Uncertain',
        '6. Other',
    ]
    DISINFO_ACTORS = [
        '1. State actor',
        '2. Terrorist organization',
        '3. Domestic ideologue',
        '4. Mercenary',
        '5. Spammer',
        '6. Trolling factory',
        '7. Uncertain',
        '8. Other',
    ]
    DISINFO_ACTIONS = [
        '1. Remove content',
        '2. Remove content and temporarily forbid users from making posts',
        '3. Remove content and temporarily suspend user account',
        '4. Remove content and remove user account',
    ]
    NUM_REPORTS = 0
    REPORTS = []

    ABUSE_TYPES = ['1', '2', '3', '4']
    YES_NO = ['1', '2']

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.message_obj = None
        self.reporting_user_id = None
        self.false_reporting = False


    def run_block_state(self):
        reply = ""

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

        return [{"content": reply, "embed": embed}]


    async def handle_message(self, message):
        '''
        This function makes up the meat of the user-side reporting flow. It defines how we transition between states and what 
        prompts to offer at each of those states. You're welcome to change anything you want; this skeleton is just here to
        get you started and give you a model for working with Discord. 
        '''

        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]
        
        elif self.state == State.REPORT_START:
            reply =  "Thank you for starting the reporting process. "
            reply += "Say `help` at any time for more information.\n\n"
            reply += "Please copy paste the link to the message you want to report.\n"
            reply += "You can obtain this link by right-clicking the message and clicking `Copy Message Link`."
            self.state = State.AWAITING_MESSAGE
            self.reporting_user_id = message.author.id
            return [reply]
        
        elif self.state == State.AWAITING_MESSAGE:
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
            self.message = '-' * 50 + '\n'
            self.message += f'REPORT [from: {message.author.name}]\nContent:\n```{message.content}```'
            self.message_obj = message
            self.state = State.MESSAGE_IDENTIFIED
            return [
                "I found this message:",
                "```" + message.author.name + ": " + message.content + "```",
                "Is this correct? Please answer `Yes` or `No`"]

        elif self.state == State.MESSAGE_IDENTIFIED:
            reply = "Here is the reported message:\n" + "```" + message.author.name + ": " + message.content + "```"

            if message.content.lower() in ['no', 'n']:
                return ["Please double check the message link and say `cancel` to cancel."]

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

            return [{"content": reply, "embed": embed}]

        elif self.state == State.CATEGORY_CHOSEN:
            if message.content not in self.ABUSE_TYPES:
                return ["Unrecognized option. Please choose from the above options."]
            if message.content == "1":
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

            self.message += f"[C1={message.content}]"
            
            return [{"content": reply, "embed": embed}]

        elif self.state in [State.CHOOSE_TYPE2, State.CHOOSE_TYPE3, State.CHOOSE_TYPE4]:
            self.message += f'[C2={message.content}]'
            self.state = State.BLOCK_STATE
            return self.run_block_state()

        elif self.state == State.CHOOSE_TYPE1:
            self.message += f'[C2={message.content}]'
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

            embed.set_footer(
                text=("Ex: To provide additional information, type `1` and hit ENTER."
                      "Then provide the additional information in text in the next message."))
            reply = ""
            return [{"content": reply, "embed": embed}]
        
        elif self.state == State.ADDITIONAL_INFORMATION:
            if message.content not in self.YES_NO:
                return ["Unrecognized option. Please choose from the above options."]
            elif message.content.startswith("1"):
                msg = await self.client.wait_for("message")
                if msg:
                    self.message += f'\nAdditional information: {msg.content}'
                    self.REPORTS.append(msg)
                    self.NUM_REPORTS += 1
            self.state = State.BLOCK_STATE
            return self.run_block_state()

        elif self.state == State.BLOCK_STATE:
            reply = None
            if message.content in self.ABUSE_TYPES:
                self.state = State.IN_REVIEW_STATE
                if message.content == '1':
                    reply = "The user was successfully blocked."
                elif message.content == '2':
                    reply = "The content was successfully blocked."
                elif message.content == '3':
                    reply = "The user and content were successfully blocked"
                else:
                    reply = "Neither the user nor content was blocked."
                self.message += f'\nReporting user action: {reply}\n'
                self.message += '-' * 50 + '\n'
                reply += "\nWe've received your report! " \
                    "Thank you for taking the time to help keep our community safe and truthful." \
                    " Our content moderation team will promptly review the report."
            else:  # In case the input is not within the ABUSE_TYPES
                reply = "Please choose a valid option by typing the corresponding number (1, 2, 3, or 4)."

            return [reply]

        elif message.content != self.MOD_START_KEYWORD and self.state == State.IN_REVIEW_STATE:
            return ["Your report is currently under review. We will update you on the status of the report promptly."]

        elif message.content == self.MOD_START_KEYWORD and self.state == State.IN_REVIEW_STATE:
            reply = (
                'Thank you for starting the moderation process\n'
                f'Here is a summary of the report:\n\n{self.message}\n'
                'Q: Does any content pose imminent threat?\n'
                'Please answer `Yes` or `No`\n'
            )
            self.state = State.MOD_START
            return [reply]

        elif self.state == State.MOD_START:
            if message.content.lower() in ['yes', 'y']:
                reply = 'Report `<escalated to emergency status>`. Thank you.'
                self.state = State.EMERGENCY
            else:
                reply = (
                    'Q: Does any content constitute disinformation?\n'
                    'Please answer `Yes` or `No` or `Uncertain`'
                )
                self.state = State.MOD_1
            return [reply]

        elif self.state == State.MOD_1:
            if message.content.lower() in ['uncertain', 'u']:
                reply = 'Report `<escalated to higher level moderators>`. Thank you'
                self.state = State.HIGHER_LEVEL_MOD
            elif message.content.lower() in ['no', 'n']:
                reply = 'Report resolved. Thank you.'
                self.false_reporting = True
                self.state = State.REPORT_COMPLETE
            else:
                reply = (
                    'Q: What category does this disinformation belong to?\n'
                    'Please choose one of the following options by entering the option number:\n'
                )
                reply += '\n'.join(self.DISINFO_CATEGORIES)
                self.state = State.MOD_2
            return [reply]

        elif self.state == State.MOD_2:
            # TODO: Parse response and store in database
            reply = (
                'Q: Who is the most likely actor of this disinformation\n'
                'Please choose one of the following options by entering the option number:\n'
            )
            reply += '\n'.join(self.DISINFO_ACTORS)
            self.state = State.MOD_3
            return [reply]

        elif self.state == State.MOD_3:
            # TODO: Parse response and store in database
            reply = (
                'Q: What is the severity of this disinformation and what action'
                ' should be taken?\n'
                'Please choose one of the following options by entering the option number:\n'
            )
            reply += '\n'.join(self.DISINFO_ACTIONS)
            self.state = State.MOD_4
            return [reply]

        elif self.state == State.MOD_4:
            # TODO: Parse response and store in database
            if '1' in message.content:
                await self.message_obj.delete()
                reply = ''
            elif '2' in message.content:
                await self.message_obj.delete()
                reply = '`<User temporarily forbidden from making posts>`\n'
            elif '3' in message.content:
                await self.message_obj.delete()
                reply = '`<User account temporarily suspended>`\n'
            else:
                await self.message_obj.delete()
                reply = '`<User account removed>`\n'
            reply += (
                'Thank you for handling this report.\n'
                'The report is resolved and the neccesary measures taken.'
            )
            self.state = State.REPORT_COMPLETE
            return [reply]

    
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
        embed.add_field(name="(4)",
                        value="Conspiracy theory",
                        inline=False)
        embed.add_field(name="(5)",
                        value="Fabricated information",
                        inline=False)
        embed.add_field(name="(6)",
                        value="Misleading information",
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

        embed.add_field(
            name="(1)",
            value="Graphic Violence",
            inline=False)
        embed.add_field(
            name="(2)",
            value="Child Exploitation",
            inline=False)
        embed.add_field(
            name="(3)",
            value="Terrorist Content",
            inline=False)
        embed.add_field(
            name="(4)",
            value="Non-Consensual Explicit Content",
            inline=False)

        embed.set_footer(text="Ex: To select 'Graphic Violence', type `1`.")

        return embed


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    def report_escalated(self):
        return self.state in [State.EMERGENCY, State.HIGHER_LEVEL_MOD]


    def report_summary(self):
        return f'- Status [{self.state}]\n{self.message}'


    def report_stats(self):
        return {
            'reported_user': self.message_obj.author.id,
            'reporting_user': self.reporting_user_id,
            'false_reporting': self.false_reporting,
        }
