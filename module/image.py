import asyncio
import aiohttp
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter
from discord import File
import multiprocessing as mp
from io import BytesIO
from .base import Module, Command, Scope
import random
import copyreg
import types

# todo: make these function names consistent. they're a pain :)


class ImageNotFoundException(Exception):
    pass


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
        print("added!")

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
                    print("duy")
                    await process.channel.send("Something went wrong while parsing that link. Make sure it contains an image.")
                    continue
            except aiohttp.InvalidURL:
                print("doy")
                await process.channel.send("Invalid URL provided.")
                continue

            self.load_event.clear()
            func, args = process.bundle_filter_call()
            print("run")
            self.pool.apply_async(func, args=args, callback=lambda ret: self.prepare_upload(ret, process))
            print("done!")

    # this is lame for now
    def prepare_upload(self, img, proc):
        asyncio.run_coroutine_threadsafe(self.post(img, proc), self.loop)

    async def post(self, data, q):
        await q.channel.send(file=File(data, filename=q.filename))

    async def load_image(self, q):
        if q.url:  # hate this just want her back x
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
        else:
            return False
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
    def __init__(self, *, channel, filename="upload.png", url=None):
        self.channel = channel
        self.filename = filename
        self.url = url
        self.size = None
        self.mode = None
        self.image = None

    def apply_filter(img, maxsize=1024):
        '''Rescales images to the passed size.'''
        print("scale down")
        size = img.size
        resize = False
        size_zero_larger = True if size[0] > size[1] else False
        larger_dimension = size[0] if size_zero_larger else size[1]
        if larger_dimension > maxsize:  # replace with const
            scale_factor = larger_dimension / maxsize
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

    def bytes_and_load(self, data):
        byte = BytesIO(data)
        try:
            img = Image.open(byte)
        except IOError:
            return None
        return img

    def set_image(self, img):
        self.image = img
        self.size = img.size
        self.mode = img.mode


# tons of fun but may be best to port it over to wand
class Cruncher(ImageQueueable):
    SOBEL_X = (
        -1, 0, 1,
        -2, 0, 2,
        -1, 0, 1
    )

    SOBEL_Y = (
        1, 2, 1,
        0, 0, 0,
        -1, -2, -1
    )

    SOBEL_X_INV = (
        1, 0, -1,
        2, 0, -2,
        1, 0, -1
    )

    SOBEL_Y_INV = (
        -1, -2, -1,
        0, 0, 0,
        1, 2, 1
    )

    def __init__(self, *, channel, url, scale=0.2):
        super().__init__(channel=channel)
        self.url = url
        self.scale = scale

    def bundle_filter_call(self):
        return Cruncher.apply_filter, (self.image, self.scale)

    def explore(start, step, row, data, size):
        x = start
        if start >= size[0]:
            return -1
        coltemp = data[x, row]
        while coltemp[3] == 128:
            x += step
            if x < 0 or x >= size[0]:
                return -1
            coltemp = data[x, row]
        return x

    def apply_crunch(img, scale, debug=False):
        '''For brevity -- more sophisticated image crunch model'''
        img, size = ImageQueueable.apply_filter(img)  # oop
        size_target = int(size[0] * scale)
        kernelX = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_X, scale=1))
        kernelY = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_Y, scale=1))
        kernelXInv = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_X_INV, scale=1))
        kernelYInv = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_Y_INV, scale=1))
        gradientMag = ImageChops.add(ImageChops.add(kernelX, kernelY, scale=1), ImageChops.add(kernelXInv, kernelYInv, scale=1), scale=2).convert("L").convert("RGBA").crop((1, 1, size[0] - 1, size[1] - 1))  # shitfuck
        # r: color value
        # g: seam id
        # b: color value (duplicate)
        # a: 0 if removed, 128 if recorded, 256 if not
        print("gradients calculated!")
        if debug:
            return gradientMag
        size = gradientMag.size
        data = gradientMag.load()

        seed_array = []
        for x in range(size[0]):
            seed_sum = data[x, 0][0]
            x_big = int(x / 256)
            x_small = x % 256
            data[x, 0] = (seed_sum, x_big, x_small, 128)
            x_min = x  # initial x represents seed ID
            for row in range(1, size[1]):
                c_pos = Cruncher.explore(x_min, 1, row, data, size)
                if c_pos == -1:
                    c_pos = Cruncher.explore(x_min - 1, -1, row, data, size)
                    r_val = 4096
                else:
                    r_pos = Cruncher.explore(c_pos + 1, 1, row, data, size)
                    if r_pos == -1:
                        r_val = 4096
                    else:
                        r_val = data[r_pos, row][0]
                c_val = data[c_pos, row][0]
                l_pos = Cruncher.explore(x_min - 1, -1, row, data, size)
                if l_pos == -1:
                    l_val = 4096
                else:
                    l_val = data[l_pos, row][0]
                # values determined -- decide where to go
                if l_val < c_val and l_val < r_val:
                    x_min = l_pos
                    col_temp = data[l_pos, row]
                elif c_val < r_val:
                    x_min = c_pos
                    col_temp = data[c_pos, row]
                else:
                    x_min = r_pos
                    col_temp = data[r_pos, row]
                seed_sum += col_temp[0]
                data[x_min, row] = (col_temp[0], x_big, x_small, 128)
            seed_array.append((x, seed_sum))
        seed_array = sorted(seed_array, key=lambda i: i[1])
        seed_table = {}
        for i in range(len(seed_array)):  # whatever dude
            seed_table[seed_array[i][0]] = i
            pass
        size_final = (size[0] - size_target, size[1])
        print("seam carving done!")
        finale = Image.new("RGB", size_final)
        f_data = finale.load()
        init_data = img.load()
        for j in range(size[1]):
            cur_x = 0
            for i in range(size[0]):
                coltemp = data[i, j]
                if seed_table[(coltemp[1] * 256) + coltemp[2]] >= size_target and cur_x < size_final[0]:
                    f_data[cur_x, j] = init_data[i, j]
                    cur_x += 1
        print("done!")
        return finale
        # attempt to program in the seam carving method

        pass

    def apply_crunch_lazy(img, scale, debug=False):
        '''Faster seam carve function that runs a ton faster but crunches it up all nasty'''
        print("starting")
        img, size = ImageQueueable.apply_filter(img, maxsize=640)  # oop
        if scale > 0.9:
            scale = 0.9
        size_target = int(size[0] * scale)
        kernelX = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_X, scale=1))
        kernelY = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_Y, scale=1))
        kernelXInv = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_X_INV, scale=1))
        kernelYInv = img.filter(ImageFilter.Kernel((3, 3), Cruncher.SOBEL_Y_INV, scale=1))
        gradientMag = ImageChops.add(ImageChops.add(kernelX, kernelY, scale=1), ImageChops.add(kernelXInv, kernelYInv, scale=1), scale=2).convert("L").convert("RGBA").crop((1, 1, size[0] - 1, size[1] - 1))  # shitfuck
        print("gradients calculated!")
        if debug:
            return gradientMag
        size = gradientMag.size
        data = gradientMag.load()
        # if possible, speed up this loop
        for x in range(size_target):
            x_min = random.randint(0, size[0] - 1)
            while data[x_min, 0][3] == 128:
                x_min = random.randint(0, size[0] - 1)
            col_temp = data[x_min, 0]
            data[x_min, 0] = (col_temp[0], col_temp[1], col_temp[2], 128)
            for row in range(1, size[1]):
                c_pos = Cruncher.explore(x_min, 1, row, data, size)
                if c_pos == -1:
                    c_pos = Cruncher.explore(x_min - 1, -1, row, data, size)
                    r_val = 4096
                else:
                    r_pos = Cruncher.explore(c_pos + 1, 1, row, data, size)
                    if r_pos == -1:
                        r_val = 4096
                    else:
                        r_val = data[r_pos, row][0]
                c_val = data[c_pos, row][0]
                l_pos = Cruncher.explore(c_pos - 1, -1, row, data, size)
                if l_pos == -1:
                    l_val = 4096
                else:
                    l_val = data[l_pos, row][0]
                # values determined -- decide where to go
                if l_val < c_val and l_val < r_val:
                    x_min = l_pos
                    col_temp = data[l_pos, row]
                elif c_val < r_val:
                    x_min = c_pos
                    col_temp = data[c_pos, row]
                else:
                    x_min = r_pos
                    col_temp = data[r_pos, row]
                data[x_min, row] = (col_temp[0], col_temp[1], col_temp[2], 128)
        size_final = (size[0] - size_target, size[1])
        finale = Image.new("RGB", size_final)
        f_data = finale.load()
        init_data = img.load()
        for j in range(size[1]):
            cur_x = 0
            for i in range(size[0]):
                col_temp = data[i, j]
                if col_temp[3] != 128:
                    f_data[cur_x, j] = init_data[i, j]
                    cur_x += 1
        print("done!")
        return finale

    def apply_filter(img, scale, debug=False):
        if debug:
            img_final = Cruncher.apply_crunch(img, scale, debug)
        else:
            img_temp = Cruncher.apply_crunch_lazy(img, scale).rotate(90, expand=True)
            img_final = Cruncher.apply_crunch_lazy(img_temp, scale).rotate(-90, expand=True)

        result = BytesIO()
        img_final.save(result, "JPEG", quality=int(max(100 / (scale * 25), 5)))
        result.seek(0)
        return result


class StatView(ImageQueueable):
    def __init__(self, *, channel, target, url):
        super().__init__(channel=channel)  # christ
        self.target = target
        self.url = url

    def bundle_filter_call(self):
        return StatView.apply_filter, (self.image, self.target)

    def apply_filter(img, target):
        GRAY = 0x36393f
        GREEN = 0xadd8a3
        SIZE = (384, 256)
        canvas = Image.new("RGB", SIZE, (54, 57, 63))
        canvas.paste(img, (257, 129))

        brush = ImageDraw.Draw(canvas)

        brush.rectangle((0, 0, 256, 256), fill=GREEN)
        brush.rectangle((0, 256, 128, 384), fill=GREEN)

        levelbar_x = int(12 + (target[9] / target[8]) * 232)

        brush.rectangle((10, 104, 12, 120), fill=GRAY)
        brush.rectangle((244, 104, 246, 120), fill=GRAY)
        brush.rectangle((12, 110, levelbar_x, 118), fill=GRAY)

        try:
            fontBig = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=64)
            fontSmall = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=32)
            fontTiny = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=16)
        except Exception as e:
            print(e)

        level = str(target[7])
        rank = "#" + str(target[6])
        expnext = str(target[8])
        expcur = str(target[9])

        levelWidth = brush.textsize(level, font=fontBig)
        brush.text((10, 30), level, font=fontBig, fill=GRAY)
        brush.text((10, 140), "GR", font=fontBig, fill=GRAY)
        brush.text((138, 140), "LR", font=fontBig, fill=GRAY)
        brush.text((levelWidth[0] + 15, 60), expcur, font=fontTiny, fill=GRAY)
        brush.text((levelWidth[0] + 15, 80), expnext, font=fontTiny, fill=GRAY)
        grWidth = brush.textsize(rank, font=fontSmall)
        lrWidth = brush.textsize("N/A", font=fontSmall)
        brush.text((118 - grWidth[0], 208), rank, font=fontSmall, fill=GRAY)
        brush.text((246 - lrWidth[0], 208), "N/A", font=fontSmall, fill=GRAY)

        result = BytesIO()
        canvas.save(result, "PNG")
        result.seek(0)
        return result
    pass


class JPEGFilter(ImageQueueable):
    def __init__(self, *, channel, url):
        print("filter created")
        super().__init__(channel=channel, url=url)

    def bundle_filter_call(self):
        return JPEGFilter.apply_filter, (self.image,)

    def apply_filter(img, quality=5):
        print("ok")
        try:
            result = BytesIO()
            img.save(result, "JPEG", quality=quality)
            result.seek(0)
            print("saved")
            return result
        except Exception as e:
            print(e)


class MemeFilter(ImageQueueable):
    def __init__(self, *, channel, url, text):
        super().__init__(channel=channel, url=url)
        self.text = text

    def bundle_filter_call(self):
        return MemeFilter.apply_filter, (self.image, self.text)

    def split_text(text_arr, font, size_limit):
        line_size = 0
        string_temp = ""
        first_line = True
        linecount = 0
        for word in text_arr:
            line_size += ImageDraw.textsize(word, font=font)
            if first_line:
                linecount += 1
            if line_size > size_limit:
                if first_line:
                    string_temp += word + "\n"
                else:
                    string_temp += "\n" + word + " "
                    first_line = True
            else:
                first_line = False
                string_temp += word + " "
        return string_temp, linecount
        pass

    def apply_filter(img, text):
        # todo:
        #   - optimize textsize calls
        try:
            print("hello")
            if "|" in text:
                splitindex = text.index("|")
                text_top = text[:splitindex]
                text_bottom = text[splitindex + 1:]
            else:
                char_count = len(text)
                cur = 0
                half_len = 0
                while half_len < char_count:
                    half_len += len(text[cur]) * 2.1
                    cur += 1
                text_top = " ".join(text[:cur])
                text_bottom = " ".join(text[cur:])
            MIN_SIZE = 48
            MAX_SIZE = 144
            multiline = False
            img, size = ImageQueueable.apply_filter(img)
            size_limit = size[0] * 0.8
            font = ImageFont.truetype(font="impact.ttf", size=MAX_SIZE)
            text_top_str = " ".join(text_top)
            text_bot_str = " ".join(text_bottom)
            font_size = MAX_SIZE

            print("text split")

            brush = ImageDraw.Draw(img)
            max_width = max(brush.textsize(text_top_str, font=font)[0], brush.textsize(text_bot_str, font=font)[0])
            if max_width > size_limit:
                font_scale = size_limit / max_width
                if font_scale > (MAX_SIZE / MIN_SIZE):
                    multiline = True
                font_size = int(max(MIN_SIZE, MAX_SIZE * font_scale))
                print(font_size)
                font = ImageFont.truetype("impact.ttf", size=font_size)
            center = int(size[0] / 2)
            if multiline:
                text_top_str, linecount_top = MemeFilter.split_text(text_top, font, size_limit)
                text_bot_str, linecount_bottom = MemeFilter.split_text(text_bottom, font, size_limit)

                def draw_text(x, y, fill):
                    brush.multiline_text((center + x, 48 + y), text_top_str, fill=fill, font=font, align="center")
                    v_bottom = linecount_bottom * font_size  # rough guess
                    brush.multiline_text((center + x, size[1] - 48 - v_bottom + y), text_bot_str, fill=fill, font=font, align="center")

            else:
                def draw_text(x, y, fill):
                    top_pos = int(center - (brush.textsize(text_top_str, font=font)[0]) / 2)
                    bottom_pos = int(center - (brush.textsize(text_bot_str, font=font)[0]) / 2)
                    brush.text((top_pos + x, 48 + y), text_top_str, fill=fill, font=font)
                    brush.text((bottom_pos + x, size[1] - 48 - font_size + y), text_bot_str, fill=fill, font=font)

            BLACK = 0x000000
            WHITE = 0xffffff

            draw_text(-3, -3, BLACK)
            draw_text(-3, 0, BLACK)
            draw_text(-3, 3, BLACK)
            draw_text(0, 3, BLACK)
            draw_text(3, 3, BLACK)
            draw_text(3, 0, BLACK)
            draw_text(3, -3, BLACK)
            draw_text(0, -3, BLACK)
            draw_text(0, 0, WHITE)

            result = BytesIO()
            img.save(result, "JPEG", quality=80)
            result.seek(0)
            print("saved")
            return result
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())


class Pixelsort(ImageQueueable):
    '''Pixelsort implementation extending ImageQueueable.

If not provided, compare is set to the luminance function.

Pixelsort(channel, url, [filename='upload.png', isHorizontal=True, threshold=0.5, compare=luma])'''
    def __init__(self, *, channel, url, filename="upload.png", isHorizontal=True, threshold=0.5, compare=None):
        super().__init__(channel=channel, filename=filename, url=url)
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
        result = BytesIO()
        img.save(result, "PNG")
        result.seek(0)
        print("saved")
        return result


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

    def parse_string(host, content, message):
        array = host.split(content)
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
        url, args = ImageModule.parse_string(host, state.content, state.message)
        if len(args) >= 1:
            sort = Pixelsort(channel=state.message.channel, url=url, threshold=float(args[0]), isHorizontal=True)
        else:
            sort = Pixelsort(channel=state.message.channel, url=url, isHorizontal=True)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(sort)
        pass

    @Command.cooldown(scope=Scope.USER, time=20)
    @Command.register(name="stat")
    async def stat(host, state):
        target = state.message.author
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.callproc("GLOBALINFO", (target.id,))
                targetinfo = await cur.fetchone()
        statview = StatView(channel=state.message.channel, target=targetinfo, url=str(target.avatar_url_as(static_format="png", size=128)))
        await state.command_host.queue.add_to_queue(statview)

    @Command.cooldown(scope=Scope.CHANNEL, time=10)
    @Command.register(name="crunch")
    async def crunch(host, state):
        '''
Implementation of seam carving in Pillow. Relatively slow for now.
        '''
        # todo: implement FXAA step or something similar to smooth out the result
        url, args = ImageModule.parse_string(host, state.content, state.message)
        if len(args) >= 1:
            cruncher = Cruncher(channel=state.message.channel, url=url, scale=(float(args[0]) or 0.2))
        else:
            cruncher = Cruncher(channel=state.message.channel, url=url)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(cruncher)

    # todo: improve text here
    @Command.cooldown(scope=Scope.CHANNEL, time=3)
    @Command.register(name="meme")
    async def meme(host, state):
        url, args = ImageModule.parse_string(host, state.content, state.message)
        meme = MemeFilter(channel=state.message.channel, url=url, text=args)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(meme)

    @Command.cooldown(scope=Scope.CHANNEL, time=3)
    @Command.register(name="jpeg")
    async def jpeg(host, state):
        url, args = ImageModule.parse_string(host, state.content, state.message)
        jaypeg = JPEGFilter(channel=state.message.channel, url=url)
        print("dab")
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(jaypeg)
