import asyncio
import aiohttp
from PIL import Image
from discord import File
import multiprocessing as mp
from io import BytesIO
from .base import Module, Command, Scope
import copyreg
import types
# import dill


# https://stackoverflow.com/questions/8804830/python-multiprocessing-picklingerror-cant-pickle-type-function
# this one guy keeps shilling his multiprocessing substitute plugin but i dont want it
# def decode_and_run(payload):
#     func, args = dill.loads(payload)
#     return func(*args)
#
#
# def dill_encode(func, *args):
#     payload = dill.dumps(func, *args)
#     return payload
#

# if this works then we can avoid the dill call
# https://stackoverflow.com/questions/27318290/why-can-i-pass-an-instance-method-to-multiprocessing-process-but-not-a-multipro
def pickler_redirect(method):
    if method.__self__ is None:  # pickle looks for a tuple of 2: the function call, and a tuple denoting what to pass to it
        return getattr, (method.__class__, method.__name__)
    else:
        return getattr, (method.__self__, method.__name__)
# its weird because the conciseness of this implies that the built in pickler just didn't try


copyreg.pickle(types.MethodType, pickler_redirect)


class ImageQueue:
    '''
    The ImageQueue is intended as a means of managing several image commands and relaying them to
    a source. Since image functions can be time-consuming, the intent is to use the Image Queue
    as an intermediate through which images can be swiftly processed in parallel, freeing up the
    main thread to continue processing commands.

    TODO: Look into spinning all ImageQueue calls into processes. Post can absolutely be spun into a process!
    Just rework the functions to suit that workflow better.
    '''
    def __init__(self):
        mp.set_start_method("spawn")  # might have to change on server :)
        self.queue = asyncio.Queue()
        self.pool = mp.Pool(processes=mp.cpu_count() - 1, initializer=None)
        self.load_event = asyncio.Event()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.process_images(self.loop))
        # this can be asyncio.run_coroutine_threadsafe? look into tradeoffs of all of this mess

    async def add_to_queue(self, item):
        await self.queue.put(item)
        pass

    # workaround with dill (minimizing imports):
    #   - pickle the function and its arguments to a bytestream with dill
    #   - pass that bytestream as a parameter to a process using apply_async and a global decoder function
    #   - run the function inside of the decoder, thus voiding the limitations of multiprocessing
    #
    async def process_images(self, loop):
        '''
Manages the core processing loop that powers the image queue.
        '''
        while True:
            process = await self.queue.get()
            await self.load_image(process)
            # should be fine to call from callback since it runs on main thread
            self.load_event.clear()
            # filter operation runs in separate thread, whatever it is
            func, args = process.bundle_filter_call()
            self.pool.apply_async(func, args=args, callback=lambda ret: self.postsync(ret, process))

    def postsync(self, img, proc):
        asyncio.run_coroutine_threadsafe(self.post(img, proc), self.loop)

    async def empty(self):
        pass

    async def post(self, data, q):
        img = BytesIO()
        data.save(img, "PNG")
        img.seek(0)
        await q.channel.send(file=File(img, filename=q.filename))

    # this should be doable pretty quickly when adding the item to the queue?
    async def load_image(self, q):
        print(q)
        print("get image: " + q.url)
        async with aiohttp.ClientSession() as session:
            async with session.get(q.url) as resp:
                data = await resp.read()
        # major blocking here
        # could use a queue event to put this on lock?
        self.load_event.clear()
        # self.pool.apply_async(ImageQueue.bytes_and_load, (data,), callback=lambda ret: self.pass_image(q, ret))
        # non ideal
        ret = ImageQueue.bytes_and_load(data)  # this function potentially incurs some significant blocking, but throwing it into a process atm causes major slowdown. will have to investigate further
        # self.pool.apply_async(ImageQueue.bytes_and_load, args=(data,), callback=lambda ret: self.pass_image(q, ret))
        self.pass_image(q, ret)
        await self.load_event.wait()

    def bytes_and_load(data):
        byte = BytesIO(data)
        try:
            img = Image.open(byte)
        except IOError:
            return None
        return img

    def pass_image(self, queueable, result):
        if result is None:
            # terminate queue item since it is invalid
            pass
        queueable.set_image(result)
        self.load_event.set()


class ImageQueueable:
    def __init__(self, *, channel, url, filename="upload.png"):  # account for image compression
        self.channel = channel
        self.url = url
        self.filename = filename
        self.size = None
        self.mode = None
        self.image = None

        # use executor to get image.

    def apply_filter(self):
        '''
        "Abstract" class intended for creating the image filter. Spun into a process by ImageQueue.
        Performs some operation on a passed image. Parameters should cover all self values, so that
        it can be picklable
        '''
        pass

    def bundle_filter_call(self):
        '''
        Generates arguments on a per-function basis using self properties. Returns a tuple containing the filter function and its arguments.
        Necessary for pickling and running the function within a process.

        Filter accepts parameters. This is responsible for getting those parameters so they can be passed on later.
        '''
        pass

    def set_image(self, img):
        self.image = img
        self.size = img.size
        self.mode = img.mode

    # def dill_bundle_call(self):
    #     return dill_encode(self.apply_filter)


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

    # as before: we bundle up and hand-deliver the proper variables with this
    def bundle_filter_call(self):
        return Pixelsort.apply_filter, (self.image, self.isHorizontal, self.size, self.compare, self.mode, self.threshold)

    # should return the filtered image object.
    def apply_filter(img, isHorizontal, size, compare, mode, threshold):
        data = img.load()  # pixel access

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
                        if cur < fine_axis:  # iffy as hell
                            coldata = get_func(g, cur)
                            thr = compare(coldata, mode)
                    # loop closed. sort internally.
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
        return img  # i hope this work
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


# whoa mama https://bytes.com/topic/python/answers/552476-why-cant-you-pickle-instancemethods
# copy_reg can be used to assign a pickle function
# pickling code is old and from old python. it might work now, who knows!

# write some function main code to test this out

class ImageModule(Module):
    def __init__(self, host, *args, **kwargs):
        super().__init__(host, *args, **kwargs)
        self.queue = ImageQueue()

    def parse_string(content, message):
        array = Command.split(content)
        url = None
        if (len(message.attachments)):
            attachment = message.attachments[0]
            if attachment.height is not None:  # is an image
                url = attachment.proxy_url
        if url is None and len(array) > 0:
            url = array.pop(0)
        return url, array

    # note: might be good to give command objects implicit access to the host
    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="pixelsort")
    async def pixelsort(host, state):
        '''
Quick pixelsorting function. URL or image upload must be provided.

Usage:
g pixelsort (<url>|uploaded image) [<threshold (0.5)> <comparison function (luma)>]
        '''
        url, args = ImageModule.parse_string(state.content, state.message)
        if len(args) >= 1:
            sort = Pixelsort(channel=state.message.channel, url=url, threshold=float(args[0]), isHorizontal=True)
        else:
            sort = Pixelsort(channel=state.message.channel, url=url, isHorizontal=True)
        await state.command_host.queue.add_to_queue(sort)
        pass
