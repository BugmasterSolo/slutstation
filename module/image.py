from PIL import Image
import asyncio
from .base import Module, Command


class ImageQueue(Module):
    pass
    # the imageQueue is a means of managing a longer list of image commands. users may stack it high and they need to be managed
    # look into spawning threads and letting them run as asynchronous events so as to avoid blocking the main thread
    # for now: create a single queue that just cranks out images as necessary and prints them with done
    # later on: look into creating several queues
    # threading should be aware of the processor limitations as well
