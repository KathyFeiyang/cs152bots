from enum import Enum, auto
import discord
import re

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    REPORT_COMPLETE = auto()
    MOD_START = auto()
    MOD_1 = auto()
    MOD_2 = auto()
    MOD_3 = auto()
    MOD_4 = auto()
    EMERGENCY = auto()
    HIGHER_LEVEL_MOD = auto()

class Report:
    # User reporting
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"

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
        '1. Attach disinformation warning to content and alert user',
        '2. Remove content and alert user',
        '3. Remove content and temporarily forbid users from making posts',
        '4. Remove content and temporarily suspend user account',
        '5. Remove content and remove user account',
    ]

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
            self.message = '-' * 50 + '\n'
            self.message += f'REPORT [from: {message.author.name}]\nContent:\n```{message.content}```'
            self.message += '-' * 50 + '\n'
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", "```" + message.author.name + ": " + message.content + "```", \
                    "This is all I know how to do right now - it's up to you to build out the rest of my reporting flow!"]
        
        if message.content != self.MOD_START_KEYWORD and self.state == State.MESSAGE_IDENTIFIED:
            # TODO: implement reporting flow
            return ["<insert rest of reporting flow here>"]

        if message.content == self.MOD_START_KEYWORD and self.state == State.MESSAGE_IDENTIFIED:
            reply = (
                'Thank you for starting the moderation process\n'
                f'Here is a summary of the report:\n\n{self.message}\n'
                'Q: Does any content pose imminent threat?\n'
                'Please answer `Yes` or `No`\n'
            )
            self.state = State.MOD_START
            return [reply]

        if self.state == State.MOD_START:
            if message.content.lower() in ['yes', 'y']:
                reply = '`<Escalated to emergency status>`'
                self.state = State.EMERGENCY
            else:
                reply = (
                    'Q: Does any content constitute disinformation?\n'
                    'Please answer `Yes` or `No` or `Uncertain`'
                )
                self.state = State.MOD_1
            return [reply]

        if self.state == State.MOD_1:
            if message.content.lower() in ['uncertain', 'u']:
                reply = '`<Escalated to higher level moderators>`'
                self.state = State.HIGHER_LEVEL_MOD
            elif message.content.lower() in ['no', 'n']:
                reply = 'Report resolved. Thank you.'
                self.state = State.REPORT_COMPLETE
            else:
                reply = (
                    'Q: What category does this disinformation belong to?\n'
                    'Please choose one of the following options by entering the option number:\n'
                )
                reply += '\n'.join(self.DISINFO_CATEGORIES)
                self.state = State.MOD_2
            return [reply]

        if self.state == State.MOD_2:
            # TODO: Parse response and store in database
            reply = (
                'Q: Who is the most likely actor of this disinformation\n'
                'Please choose one of the following options by entering the option number:\n'
            )
            reply += '\n'.join(self.DISINFO_ACTORS)
            self.state = State.MOD_3
            return [reply]

        if self.state == State.MOD_3:
            # TODO: Parse response and store in database
            reply = (
                'Q: What is the severity of this disinformation and what action'
                ' should be taken?\n'
                'Please choose one of the following options by entering the option number:\n'
            )
            reply += '\n'.join(self.DISINFO_ACTIONS)
            self.state = State.MOD_4
            return [reply]

        if self.state == State.MOD_4:
            # TODO: Parse response and store in database
            # TODO: Flag or remove content / ban user account
            if '1' in message.content:
                pass
            elif '2' in message.content:
                pass
            elif '3' in message.content:
                pass
            elif '4' in message.content:
                pass
            else:
                pass
            reply = (
                'Thank you for handling this report.\n'
                'The report is resolved and the neccesary measures taken.'
            )
            self.state = State.REPORT_COMPLETE
            return [reply]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE


    def report_escalated(self):
        return self.state in [State.EMERGENCY, State.HIGHER_LEVEL_MOD]


    def report_summary(self):
        return f'- Status [{self.state}]\n{self.message}'
