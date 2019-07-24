import asyncio
import aiohttp
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter, ImageOps
from discord import File
import multiprocessing as mp
from io import BytesIO
from .base import Module, Command, Scope
import random
import copyreg
import types
from functools import reduce

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
    def __init__(self, host):
        mp.set_start_method("spawn")
        self.host = host
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
        try:
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

                self.load_event.clear()
                func, args = process.bundle_filter_call()
                self.pool.apply_async(func, args=args, callback=lambda ret: self.prepare_upload(ret, process))
                print("done!")
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())

    # this is lame for now
    def prepare_upload(self, img, proc):
        asyncio.run_coroutine_threadsafe(self.post(img, proc), self.loop)

    async def post(self, data, q):
        try:
            msg = await q.channel.send(file=File(data, filename=q.filename))
            self.host.log_undo(msg, q.msg)
        except Exception as e:
            print(e)
            print("we got em")

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
        # if result is None:
        #     wipe item
        #     pass
        queueable.set_image(result)
        self.load_event.set()


class ImageQueueable:
    def __init__(self, *, msg, filename="upload.png", url=None):
        self.msg = msg
        self.channel = msg.channel
        self.filename = filename
        self.url = url
        self.size = None
        self.mode = None
        self.image = None

    def apply_filter(img, maxsize=1024):
        '''Rescales images to the passed size.'''
        exif_orientation = 0x0112  # thanks SO
        # list of valid exif orientations and their inverse transforms
        EXIF_ORIENTATIONS = [
            [],
            [],
            [Image.FLIP_LEFT_RIGHT],
            [Image.ROTATE_180],
            [Image.FLIP_TOP_BOTTOM],
            [Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
            [Image.ROTATE_270],
            [Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],
            [Image.ROTATE_90]
        ]
        resize = False
        #  https://stackoverflow.com/questions/4228530/pil-thumbnail-is-rotating-my-image
        #  i can't wait to get better at python
        try:
            if hasattr(img, '_getexif'):
                # use the recorded orientation attr to get the img orientation
                try:
                    tfs = EXIF_ORIENTATIONS[img._getexif()[exif_orientation]]
                # reduce with the Image func -- img is passed as self, tfs is passed as the transform
                # a for loop would work here as well but this solution is much more interesting (thanks SO!)
                    img = reduce(type(img).transpose, tfs, img)
                except (TypeError, KeyError):
                    pass
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())

        size = img.size
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

    def __init__(self, *, msg, url, scale=0.2):
        super().__init__(msg=msg)
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

    # todo: I implemented this wrong. redo it.
    # ideally:
    #  - work from bottom to top, recording the current standing min sum. The old algo does this. Look left right and center.
    #  - What the current algo does NOT do is record this minimum value in the image table. Use a new image for that.
    #  - From there, we can use the prefabbed exploration function to find our potential seeds. From there, we evaluate the seed cost of each option and choose the lowest one. The new algo relies on predetermined seed minimums.
    #  - This then iterates through the entire image.
    def apply_crunch(img, scale, debug=False, debug2=False):
        '''To return back to in the future -- a technically "proper" implementation'''
        img, size = ImageQueueable.apply_filter(img, 640)  # oop
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

        size = gradientMag.size
        data = gradientMag.load()

        seam_min = Image.new("I", size)
        dats = seam_min.load()
        try:
            for col in range(size[0]):
                dats[col, 0] = data[col, 0][0]

            for row in range(1, size[1]):
                for col in range(size[0]):
                    # calculate min above
                    if col <= 0:
                        l_val = 256 * size[1]
                    else:
                        l_val = dats[col - 1, row - 1]
                    c_val = dats[col, row - 1]
                    if col >= size[0] - 1:
                        r_val = 256 * size[1]
                    else:
                        r_val = dats[col + 1, row - 1]
                    dats[col, row] = data[col, row][0] + min(l_val, c_val, r_val)
            # seed record done -- keep moving (enough for 65536 x 65536, which we will not have)
            print("map crunched!")
            if debug:
                for i in range(size[0]):
                    for j in range(size[1]):
                        dats[i, j] = int(4 * dats[i, j] / (j + 1))  # weighted avg
                return seam_min
            for i in range(size_target):
                col_min = -1
                col_sum = size[1] * 256  # guaranteed maximum possible
                for j in range(size[0]):
                    if dats[j, size[1] - 1] < col_sum and data[j, size[1] - 1][3] != 128:
                        col_min = j
                        col_sum = dats[j, size[1] - 1]
                data[col_min, size[1] - 1] = (255, 0, 0, 128)
                for row in range(size[1] - 2, -1, -1):
                    c_pos = Cruncher.explore(col_min, 1, row, data, size)
                    if c_pos == -1:
                        c_pos = Cruncher.explore(col_min - 1, -1, row, data, size)
                        r_val = size[1] * 256
                    else:
                        r_pos = Cruncher.explore(c_pos + 1, 1, row, data, size)
                        if r_pos == -1:
                            r_val = size[1] * 256
                        else:
                            r_val = dats[r_pos, row]
                    c_val = dats[c_pos, row]
                    l_pos = Cruncher.explore(c_pos - 1, -1, row, data, size)
                    if l_pos == -1:
                        l_val = size[1] * 256
                    else:
                        l_val = dats[l_pos, row]
                    # values determined -- decide where to go
                    if l_val < c_val and l_val < r_val:
                        col_min = l_pos
                        col_temp = data[l_pos, row]
                    elif c_val < r_val:
                        col_min = c_pos
                        col_temp = data[c_pos, row]
                    else:
                        col_min = r_pos
                        col_temp = data[r_pos, row]
                    data[col_min, row] = (255, 0, 0, 128)
            size_final = (size[0] - size_target, size[1])
            finale = Image.new("RGB", size_final)
            f_data = finale.load()
            init_data = img.load()
            if debug2:
                return gradientMag
            for j in range(size[1]):
                cur_x = 0
                for i in range(size[0]):
                    col_temp = data[i, j]
                    if not (col_temp[0] == 255 and col_temp[3] == 128):
                        f_data[cur_x, j] = init_data[i, j][:3]
                        cur_x += 1

            print("calculated!")
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())
        return finale

    def apply_crunch_lazy(img, scale, debug=False):
        '''Faster seam carve function that runs better but crunches it up all nasty'''
        print("starting")
        img, size = ImageQueueable.apply_filter(img, maxsize=640)  # oop
        if scale > 0.9:
            scale = 0.9
        size_target = int(size[0] * scale)
        if size_target <= 0:
            return img
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
        try:
            for _ in range(size_target):
                x_min = random.randint(0, size[0] - 1)
                try:
                    while data[x_min, 0][3] == 128:
                        x_min = random.randint(0, size[0] - 1)
                except TypeError:
                    return img  # sometimes happens -- my guess is that the image becomes too small so just pass it on for now i guess
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
                    coltemp = data[i, j]
                    if coltemp[3] != 128:
                        f_data[cur_x, j] = init_data[i, j]
                        cur_x += 1
            print("done!")
            return finale
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())

    def apply_filter(img, scale, debug=False, ultradebug=False):
        if ultradebug:
            img_temp = Cruncher.apply_crunch(img, scale, False, False).convert("RGB").rotate(-90, expand=True)
            img_final = Cruncher.apply_crunch(img_temp, scale, False, True).convert("RGB").rotate(90, expand=True)
            scale = 0.025
        elif debug:
            img_temp = Cruncher.apply_crunch(img, scale, False).convert("RGB").rotate(90, expand=True)
            img_final = Cruncher.apply_crunch(img_temp, scale, False).convert("RGB").rotate(-90, expand=True)
            scale = 0.025
        else:
            img_temp = Cruncher.apply_crunch_lazy(img, scale).rotate(90, expand=True)
            img_final = Cruncher.apply_crunch_lazy(img_temp, scale).rotate(-90, expand=True)

        result = BytesIO()
        img_final.save(result, "JPEG", quality=int(max(100 / (scale * 25), 5)))
        result.seek(0)
        return result


class StatView(ImageQueueable):
    def __init__(self, *, msg, target, url):
        super().__init__(msg=msg)  # christ
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
        brush.rectangle((12, 108, levelbar_x, 118), fill=GRAY)

        fontBig = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=64)
        fontSmall = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=32)
        fontTiny = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=16)
        fontMiniscule = ImageFont.truetype(font="RobotoMono-Bold.ttf", size=8)

        level = str(target[7])
        rank_global = "#" + str(target[6])
        rank_local = "#" + str(target[11])
        expnext = str(target[8])
        expcur = str(target[9])

        levelWidth = brush.textsize(level, font=fontBig)
        brush.text((10, 30), level, font=fontBig, fill=GRAY)
        brush.text((10, 140), "GR", font=fontBig, fill=GRAY)
        brush.text((138, 140), "LR", font=fontBig, fill=GRAY)
        brush.text((levelWidth[0] + 15, 60), expcur, font=fontTiny, fill=GRAY)
        brush.text((levelWidth[0] + 15, 80), expnext, font=fontTiny, fill=GRAY)
        grWidth = brush.textsize(rank_global, font=fontSmall)
        lrWidth = brush.textsize(rank_local, font=fontSmall)
        brush.text((118 - grWidth[0], 208), rank_global, font=fontSmall, fill=GRAY)
        brush.text((246 - lrWidth[0], 208), rank_local, font=fontSmall, fill=GRAY)
        brush.text((14, 108), "EXP", font=fontMiniscule, fill=GREEN)

        result = BytesIO()
        canvas.save(result, "PNG")
        result.seek(0)
        return result


class JPEGFilter(ImageQueueable):
    def __init__(self, *, msg, url):
        super().__init__(msg=msg, url=url)

    def bundle_filter_call(self):
        return JPEGFilter.apply_filter, (self.image,)

    def apply_filter(img, quality=5):
        result = BytesIO()
        img.convert("RGB").save(result, "JPEG", quality=quality)
        result.seek(0)
        return result


class MemeFilter(ImageQueueable):
    def __init__(self, *, msg, url, text):
        super().__init__(msg=msg, url=url)
        self.text = text

    def bundle_filter_call(self):
        return MemeFilter.apply_filter, (self.image, self.text)

    def split_text(text_arr, font, size_limit, brush):
        line_size = 0
        string_temp = ""
        first_line = True
        linecount = 0
        for index in range(len(text_arr)):
            word = text_arr[index]
            line_cur = brush.textsize(word + " ", font=font)[0]
            line_size += line_cur
            if first_line:
                linecount += 1
            if line_size > size_limit:
                line_size = 0
                if first_line:
                    string_temp += word + "\n"
                else:
                    string_temp += "\n" + word + " "
                    first_line = True
                    line_size = line_cur
            else:
                first_line = False
                string_temp += word + " "
        return string_temp

    def fit_text(brush, font, maxim, minim, text, width, height=0):
        fontface = ImageFont.truetype(font, size=maxim)
        text_format = " ".join(text)
        textbox = brush.textsize(text_format, font=fontface)

        widthratio = textbox[0] / width

        if height:
            widthratio = max(widthratio, textbox[1] / height)

        multiline = False

        fontface = ImageFont.truetype(font=font, size=max(minim, min(maxim, int(maxim / widthratio))))

        if widthratio > (maxim / minim):
            text_format = MemeFilter.split_text(text, fontface, width, brush)
            multiline = True

        return (text_format, fontface, multiline)

    def apply_filter(img, text):
        # todo:
        #   - optimize textsize calls
        try:
            if "|" in text:
                splitindex = text.index("|")
                text_top = text[:splitindex]
                text_bottom = text[splitindex + 1:]
            else:
                char_count = reduce(lambda i, j: i + len(j), text, 0)
                cur = 0
                half_len = 0
                while half_len < char_count:
                    half_len += len(text[cur]) * 2.1
                    cur += 1
                text_top = text[:cur]
                text_bottom = text[cur:]
            MIN_SIZE = 24
            MAX_SIZE = 224
            multiline = False

            img, size = ImageQueueable.apply_filter(img)
            size_limit = size[0] * 0.8
            height_limit = size[1] * 0.3
            v_offset = min(size[0] * 0.05, 48)

            brush = ImageDraw.Draw(img)

            text_top_str, font_top, multiline_top = MemeFilter.fit_text(brush, "impact.ttf", MAX_SIZE, MIN_SIZE, text_top, size_limit, height_limit)

            text_bot_str, font_bot, multiline_bot = MemeFilter.fit_text(brush, "impact.ttf", MAX_SIZE, MIN_SIZE, text_bottom, size_limit, height_limit)

            multiline = multiline_top or multiline_bot

            center = int(size[0] / 2)
            if multiline:
                top_size = brush.textsize(text_top_str, font=font_top)
                bot_size = brush.textsize(text_bot_str, font=font_bot)
                top_pos = int(center - (top_size[0]) / 2)
                bot_pos = int(center - (bot_size[0]) / 2)

                v_bottom = size[1] - v_offset - bot_size[1]

                def draw_text(x, y, fill):
                    brush.multiline_text((top_pos + x, v_offset + y), text_top_str, fill=fill, font=font_top, align="center")
                    brush.multiline_text((bot_pos + x, v_bottom + y), text_bot_str, fill=fill, font=font_bot, align="center")

            else:
                top_size = brush.textsize(text_top_str, font=font_top)
                bot_size = brush.textsize(text_bot_str, font=font_bot)
                top_pos = int(center - (top_size[0]) / 2)
                bot_pos = int(center - (bot_size[0]) / 2)

                v_bottom = size[1] - v_offset - bot_size[1]

                def draw_text(x, y, fill):
                    brush.text((top_pos + x, v_offset + y), text_top_str, fill=fill, font=font_top)
                    brush.text((bot_pos + x, v_bottom + y), text_bot_str, fill=fill, font=font_bot)

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
            img.convert("RGB").save(result, "JPEG", quality=80)
            result.seek(0)
            return result
        except Exception as e:
            print(e)
            import traceback
            print(traceback.format_exc())


class PeterGriffinFilter(MemeFilter):
    def __init__(self, *, msg, url, text):
        super().__init__(msg=msg, url=url, text=text)
        # griffin from Wikipedia: https://en.wikipedia.org/wiki/Peter_Griffin

    def bundle_filter_call(self):
        return PeterGriffinFilter.apply_filter, (self.image, self.text)

    def apply_filter(img, text):
        try:
            img, size = ImageQueueable.apply_filter(img)
            griffin = Image.open('module/module_resources/putridgriffith.png')
            GRIFFIN_RATIO = griffin.size[1] / griffin.size[0]
            griffin = griffin.resize((int(img.size[0] * 0.2), int(img.size[0] * 0.2 * GRIFFIN_RATIO)), Image.BICUBIC)
            # TODO: refactor
            MIN_SIZE = 21
            MAX_SIZE = 72
            FONT_NAME = 'arial.ttf'
            multiline = False
            size_limit = size[0] * 0.6
            brush = ImageDraw.Draw(img)

            text_format, font, multiline = PeterGriffinFilter.fit_text(brush, FONT_NAME, MAX_SIZE, MIN_SIZE, text, size_limit)

            textbox = brush.textsize(text_format, font=font)
            # 40px margin on each size
            img_final = Image.new("RGB", (img.size[0], img.size[1] + textbox[1] + 80), color=0)

            brush = ImageDraw.Draw(img_final)
            text_loc = (int(img.size[0] * 0.3), img.size[1] + 40)
            img_final.paste(img)
            img_final.paste(griffin, (int(img.size[0] * 0.05), img.size[1] + 20))
            if multiline:
                brush.multiline_text(text_loc, text_format, fill=0xffffff, font=font, align="center")
            else:
                brush.text(text_loc, text_format, fill=0xffffff, font=font)

            result = BytesIO()
            img_final.save(result, "JPEG", quality=80)
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
    def __init__(self, *, msg, url, filename="upload.png", isHorizontal=True, threshold=0.5, compare=None):
        super().__init__(msg=msg, filename=filename, url=url)
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


class InvertFilter(ImageQueueable):
    def bundle_filter_call(self):
        return InvertFilter.apply_filter, (self.image, )

    def apply_filter(img):
        img, _ = ImageQueueable.apply_filter(img)
        img = ImageOps.invert(img)
        result = BytesIO()
        img.save(result, "JPEG", quality=88)
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
        self.queue = ImageQueue(host)

    def parse_string(host, content, message):
        array = host.split(content)
        url = None
        if (len(message.attachments)):
            attachment = message.attachments[0]
            if attachment.height is not None:
                url = attachment.proxy_url
        if not url and len(array) > 0:
            url = array.pop(0)
        if not url:
            raise ImageNotFoundException("Image not provided!")
        return url, array

    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="pixelsort")
    async def pixelsort(host, state):
        '''
Quick pixelsorting function. URL or image upload must be provided.

Usage:
g pixelsort (<url> or ignore if uploaded image) [threshold (0 - 1, default 0.5)]

Undoable.
        '''
        try:
            url, args = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        if len(args) >= 1:
            try:
                threshold = float(args[0])
            except ValueError:
                threshold = 0.5
            sort = Pixelsort(msg=state.message, url=url, threshold=threshold, isHorizontal=True)
        else:
            sort = Pixelsort(msg=state.message, url=url, isHorizontal=True)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(sort)

    @Command.cooldown(scope=Scope.USER, time=20)
    @Command.register(name="stat")
    async def stat(host, state):
        '''
Display your user statistics in an image!

Usage:
g stat

Undoable.
        '''
        target = state.message.author
        async with host.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.callproc("GLOBALINFO", (target.id, state.message.guild.id))
                targetinfo = await cur.fetchone()
        statview = StatView(msg=state.message, target=targetinfo, url=str(target.avatar_url_as(static_format="png", size=128)))
        await state.command_host.queue.add_to_queue(statview)

    @Command.cooldown(scope=Scope.CHANNEL, time=10)
    @Command.register(name="crunch")
    async def crunch(host, state):
        '''
Naive seam carving (Content aware scale) algorithm with JPEG filter.

Usage:
g crunch (<url> or ignore if uploaded image) [crunch amount(0 - 0.9, default 0.2)]

Undoable.
        '''
        # todo: implement FXAA step or something similar to smooth out the result
        try:
            url, args = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        if len(args) >= 1:
            try:
                scale = float(args[0])
            except ValueError:
                scale = 0.2
            cruncher = Cruncher(msg=state.message, url=url, scale=scale)
        else:
            cruncher = Cruncher(msg=state.message, url=url)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(cruncher)

    # todo: improve text here
    @Command.cooldown(scope=Scope.CHANNEL, time=3)
    @Command.register(name="meme")
    async def meme(host, state):
        '''
Make a meme.

Usage:
g meme (<url> or ignore if uploaded image) (<TEXT> or <TOPTEXT> | <BOTTOMTEXT>)

Undoable.
        '''
        try:
            url, args = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        if len(args) == 0:
            args = ["ERR", "|", "TRANSLATION", "SERVICE", "UNAVAILABLE"]
        meme = MemeFilter(msg=state.message, url=url, text=args)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(meme)

    @Command.cooldown(scope=Scope.CHANNEL, time=3)
    @Command.register(name="jpeg")
    async def jpeg(host, state):
        '''
Do I look like I-- no no not doing that.

Usage:
g jpeg (<url> or ignore if uploaded image)

Undoable.
        '''
        try:
            url, _ = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        jaypeg = JPEGFilter(msg=state.message, url=url)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(jaypeg)

    @Command.cooldown(scope=Scope.CHANNEL, time=3)
    @Command.register(name="invert")
    async def invert(host, state):
        '''
Invert the colors.

Usage:
g invert (<url> or ignore if uploaded image)

Undoable.
        '''
        try:
            url, _ = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        inverter = InvertFilter(msg=state.message, url=url)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(inverter)

    @Command.cooldown(scope=Scope.CHANNEL, time=5)
    @Command.register(name="peterhere")
    async def peterhere(host, state):
        '''
Hey guys, peter here.

Usage:
g peterhere (<url> or ignore if uploaded image) <text>

Undoable.
        '''
        try:
            url, args = ImageModule.parse_string(host, state.content, state.message)
        except ImageNotFoundException:
            await state.message.channel.send("Please include an image URL or attachment!")
            return
        if len(args) == 0:
            args = ['fortnite']
        griffin = PeterGriffinFilter(msg=state.message, url=url, text=args)
        await state.message.channel.trigger_typing()
        await state.command_host.queue.add_to_queue(griffin)
