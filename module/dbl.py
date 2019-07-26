from aiohttp import web
import asyncio
from .base import Module


#todo: give access via commands
class WebHandler:
    '''delegates a local web server for handling deliberate requests'''
    def __init__(self, host, dom, port, **kwargs):
        print(kwargs)
        self.host = host
        self.dom = dom
        self.port = port
        self.app = None
        self.server = None
        self.dbl_key = kwargs.get("dbl_key")
        asyncio.create_task(self.create_webhooks())

    async def create_webhooks(self):
        self.app = web.Application()

        # initialize all endpoints
        if self.dbl_key is not None:
            self.app.router.add_post("/dbl", self.dbl_request)

        self.app.router.add_get("/stats", self.stat_request)

        runner = web.AppRunner(self.app)
        await runner.setup()

        self.server = web.TCPSite(runner, self.dom, self.port)
        await self.server.start()
        print("running on port {self.port}!")

        print("all fired up!")

    def auth(self, req):
        key = req.headers.get('Authorization')
        return key and key == self.dbl_key

    async def dbl_request(self, req):
        if self.auth(req):
            fresp = await req.json()
            print(f"User {fresp['user']} just upvoted the bot!")
            return web.Response()
        # referenced from the DBL client github
        return web.Response(status=401)
        pass

    async def stat_request(self, req):
        return web.json_response(self.host.stats)
