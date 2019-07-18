from .base import Module, Command
import asyncio
import async_timeout


class Convo:
    def __init__(self, message1, message2, cmdhost):
        self.host = cmdhost
        self.end_a = {
            'channel': message1.channel,
            'guild': message1.guild
        }

        self.end_b = {
            'channel': message2.channel,
            'guild': message2.guild
        }
        self.message_status = asyncio.Event()
        asyncio.create_task(self.timeout_loop())

    async def timeout_loop(self):
        self.message_status.clear()
        try:
            async with async_timeout.timeout(30):
                await self.message_status.wait()
        except asyncio.TimeoutError:
            await self.end_call()

    async def process_message(self, state):
        self.message_status.set()
        if state.message.author.bot:
            return
        if state.message.guild.id == self.end_a['guild'].id:
            destination = self.end_b['channel']
        elif state.message.guild.id == self.end_b['guild'].id:
            destination = self.end_a['channel']
        else:
            print("what")
            return
        msg = f"**{state.message.author.name}#{state.message.author.discriminator}** {state.message.content}"
        await destination.send(msg)
        await self.timeout_loop()
        pass

    async def end_call(self):
        await self.end_a['channel'].send("Conversation closed.")
        await self.end_b['channel'].send("Conversation closed.")

        self.host.calllist.pop(self.end_a['guild'].id)
        self.host.calllist.pop(self.end_b['guild'].id)
        print(self.host.calllist)


class Telephone(Module):
    def __init__(self, host):  # TODO: host instance not necessary
        super().__init__(self, host)
        # potentially managing hundreds of server connections at a time -- how to streamline it?
        self.userqueue = []
        self.calllist = {}
        pass

    async def check(self, state):
        guild = state.message.guild
        call = self.calllist.get(guild.id, None)
        if call:
            print("hello!")
            await call.process_message(state)
        return self == state.command_host

    @Command.register(name="telephone")
    async def telephone(host, state):
        target = state.message.channel
        # TODO: perform some db function to get a user's rep
        # users match with people with roughly their rating or lower
        # if no suitable matches, sit around and wait
        if state.command_host.calllist.get(state.message.guild.id, None):
            await target.send("You're already in a call here!")
            return
        if state.command_host.userqueue:
            pardner = state.command_host.userqueue.pop(0)
            convo = Convo(state.message, pardner, state.command_host)
            state.command_host.calllist[pardner.guild.id] = convo
            state.command_host.calllist[state.message.guild.id] = convo
            await target.send("Connected to a random place in cyberspace...")
            await pardner.channel.send("Connected to a random place in cyberspace...")
        else:
            state.command_host.userqueue.append(state.message)
            await target.send("Added to call queue!")
