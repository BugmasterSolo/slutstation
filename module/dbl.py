from aiohttp import web
import asyncio


class WebHandler:
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

        runner = web.AppRunner(self.app)
        await runner.setup()

        self.server = web.TCPSite(runner, self.dom, self.port)
        await self.server.start()

        print("all fired up!")

    async def dbl_request(self, resp):
        key = resp.headers.get('Authorization')
        if key and key == self.dbl_key:
            fresp = await resp.json()
            print(f"User {fresp['user']} just upvoted the bot!")
            return web.Response()
        return web.Response(status=401)
        pass
