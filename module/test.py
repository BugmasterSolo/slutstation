from .base import Module, Command

class Test(Module):
    @Command.register(name="tester")
    async def idot():
        print("one two three")

    @Command.register(name="tester")
    async def one():
        print("fuckit")
        
