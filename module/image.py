import asyncio
import aiohttp
from PIL import Image
from discord import File
import multiprocessing as mp
from io import BytesIO
from .base import Module, Command, Scope
import copyreg
import types


# if this works then we can avoid the dill call
# https://stackoverflow.com/questions/27318290/why-can-i-pass-an-instance-method-to-multiprocessing-process-but-not-a-multipro
def pickler_redirect(method):
    if method.__self__ is None:  # pickle looks for a tuple of 2: the function call, and a tuple denoting what to pass to it
        return getattr, (method.__class__, method.__name__)
    else:
        return getattr, (method.__self__, method.__name__)


copyreg.pickle(types.MethodType, pickler_redirect)


class ImageQueue:
    '''
The ImageQueue is intended as a means of managing several image commands and relaying them to
a source. Since image functions can be time-consuming, the intent is to use the Image Queue
as an intermediate through which images can be swiftly processed in parallel, freeing up the
main thread to continue processing commands.

TODO: Rework the image queue into a general case queue object, allowing it to return the results of
different complex operations, for instance shader renders and the like.
    '''
    def __init__(self):
        mp.set_start_method("spawn")
        self.queue = asyncio.Queue()
        self.pool = mp.Pool(processes=mp.cpu_count() - 1, initializer=None)
        self.load_event = asyncio.Event()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.process_images(self.loop))
        # this can be asyncio.run_coroutine_threadsafe? look into tradeoffs of all of this mess

    async def add_to_queue(self, item):
        await self.queue.put(item)

    async def process_images(self, loop):
        '''
Manages the core processing loop that powers the image queue.
        '''
        while True:
            process = await self.queue.get()
            # parameterize this further. Move the image queue to the client, and submit draw requests to it.
            # then we can submit multiple types of images easily.
            try:
                image_successful = await self.load_image(process)
                if not image_successful:
                    await process.channel.send("Something went wrong while parsing that link. Make sure it contains an image.")
                    continue
            except aiohttp.InvalidURL:
                await process.channel.send("Invalid URL provided.")
                continue

            print("image fetched")
            self.load_event.clear()
            func, args = process.bundle_filter_call()
            self.pool.apply_async(func, args=args, callback=lambda ret: self.prepare_upload(ret, process))

    # this is lame for now
    def prepare_upload(self, img, proc):
        asyncio.run_coroutine_threadsafe(self.post(img, proc), self.loop)

    async def post(self, data, q):
        print("sending")
        await q.channel.send(file=File(data, filename=q.filename))

    async def load_image(self, q):
        print(q)
        print("get image: " + q.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(q.url) as resp:
                data = await resp.read()
        self.load_event.clear()
        ret = ImageQueue.bytes_and_load(data)  # this function potentially incurs some significant blocking, but throwing it into a process atm causes major slowdown. will have to investigate further
        # self.pool.apply_async(ImageQueue.bytes_and_load, args=(data,), callback=lambda ret: self.pass_image(q, ret))
        if ret is None:
            return False
        self.pass_image(q, ret)
        await self.load_event.wait()
        return True

    def bytes_and_load(data):
        byte = BytesIO(data)
        try:
            img = Image.open(byte)
        except IOError:
            return None
        return img

    def pass_image(self, queueable, result):
        if result is None:
            # wipe item
            pass
        queueable.set_image(result)
        self.load_event.set()


class ImageQueueable:
    def __init__(self, *, channel, url, filename="upload.png"):
        self.channel = channel
        self.url = url
        self.filename = filename
        self.size = None
        self.mode = None
        self.image = None

    def apply_filter(img):
        size = img.size
        resize = False
        size_zero_larger = True if size[0] > size[1] else False
        larger_dimension = size[0] if size_zero_larger else size[1]
        if larger_dimension > 1024:  # replace with const
            scale_factor = larger_dimension / 1024
            size = (int(size[0] / scale_factor), int(size[1] / scale_factor))
            resize = True
        if resize:
            img = img.resize(size, resample=Image.BICUBIC)
        return img, size

    def bundle_filter_call(self):
        '''
Bundles up necessary internal parameters for the class's sorting function and returns them
as a tuple containing a static reference to the sorting functions and all necessary arguments.
        '''
        pass

    def set_image(self, img):
        self.image = img
        self.size = img.size
        self.mode = img.mode


class Pixelsort(ImageQueueable):
    '''Pixelsort implementation extending ImageQueueable.

If not provided, compare is set to the luminance function.

Pixelsort(channel, url, [filename='upload.png', isHorizontal=True, threshold=0.5, compare=luma])'''
    def __init__(self, *, channel, url, filename="upload.png", isHorizontal=True, threshold=0.5, compare=None):
        super().__init__(channel=channel, url=url, filename=filename)
        self.compare = compare
        if not compare:
            self.compare = compare_funcs.luma
        self.threshold = threshold
        self.isHorizontal = isHorizontal

        # add rotation value

    def set_image(self, img):
        super().set_image(img)

    def bundle_filter_call(self):
        return Pixelsort.apply_filter, (self.image, self.isHorizontal, self.compare, self.mode, self.threshold)

    def apply_filter(img, isHorizontal, compare, mode, threshold):
        img, size = ImageQueueable.apply_filter(img)
        print("started")

        data = img.load()

        if isHorizontal:
            gross_axis = size[1]
            fine_axis = size[0]

            def get_func(g, f):
                return data[f, g]

            def set_func(g, f, col):
                data[f, g] = col
        else:
            gross_axis = size[0]
            fine_axis = size[1]

            def get_func(g, f):
                return data[g, f]

            def set_func(g, f, col):
                data[g, f] = col

        try:
            for g in range(gross_axis):
                cur = 0
                store = []
                while cur < fine_axis:
                    start = cur
                    coldata = get_func(g, cur)
                    thr = compare(coldata, mode)
                    while cur < fine_axis and thr > threshold:
                        store.append((thr, coldata))
                        cur += 1
                        if cur < fine_axis:
                            coldata = get_func(g, cur)
                            thr = compare(coldata, mode)
                    sorted_store = sorted(store, key=lambda val: val[0])  # avoid recalculation
                    store = []
                    for f in range(start, cur):  # truncated at one before cur -- should be good
                        set_func(g, f, sorted_store[start - f][1])
                    cur += 1
        except Exception as e:
            import traceback
            print("An error occurred!")
            print(e)
            traceback.print_exc()
        print("sort complete")
        result = BytesIO()
        img.save(result, "PNG")
        result.seek(0)
        return result  # i hope this work
        pass


# ~~ THRESHOLD FUNCTIONS ~~ #
class compare_funcs:
    def luma(col, mode="RGB"):
        if mode == "RGB":
            return (0.2126 * col[0] + 0.7152 * col[1] + 0.0722 * col[2]) / 256
        elif mode == "RGBA":
            return (0.2126 * col[0] + 0.7152 * col[1] + 0.0722 * col[2]) * (col[3] / 65536)
        elif mode == "L":
            return col / 256
        elif mode == "YCbCr":
            return col[0] / 256
        else:
            return 0  # handle other color spaces


class ImageModule(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.queue = ImageQueue()

    def parse_string(content, message):
        array = Command.split(content)
        print(array)
        url = None
        if (len(message.attachments)):
            attachment = message.attachments[0]
            if attachment.height is not None:
                url = attachment.proxy_url
        if url is None and len(array) > 0:
            url = array.pop(0)
        return url, array

    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="pixelsort")
    async def pixelsort(host, state):
        '''
Quick pixelsorting function. URL or image upload must be provided.

Usage:
g pixelsort (<url>|uploaded image) [<threshold (0.5)> <comparison function (luma)>]
        '''
        url, args = ImageModule.parse_string(state.content, state.message)
        print(args)
        if len(args) >= 1:
            sort = Pixelsort(channel=state.message.channel, url=url, threshold=float(args[0]), isHorizontal=True)
        else:
            sort = Pixelsort(channel=state.message.channel, url=url, isHorizontal=True)
        await state.command_host.queue.add_to_queue(sort)
        pass
