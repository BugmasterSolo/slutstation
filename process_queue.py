# In progress general-case implementation of the ImageQueue for all-purpose multitasking
# (u kno ... th4 GOOD STUFF!!!)
# in progress ofc
import types
import copyreg
import multiprocessing as mp
import asyncio


# grab from the blueprint or grab from Dad (if he present)
def pickler_method(method):
    # pickle accepts a function call, and a tuple containing the call's params
    if method.__self__ is None:
        return getattr, (method.__class__, method.__name__)
    else:
        return getattr, (method.__self__, method.__name__)


copyreg.pickle(types.MethodType, pickler_method)


class JobQueue:

    def __init__(self):
        mp.set_start_method("spawn")
        self.queue = asyncio.Queue()                            # handles task queue
        self.pool = mp.Pool(processes=mp.cpu_count() - 1)       # pool for submitting tasks


class Job:
    '''Jobs are a general case classification for tasks which submit information to a multiprocess.
Any class that implements the Job class will be able to submit work to the JobQueue, provided it meets
the conditions mandated by the queue.

Each job must implement a "bundle" function, which provides arguments to the internal filter function
(note: check if pickler will take care of "self" parameters, I don't think it will
if it doesn't, use bundle to provide a static reference to the filter function, and ensure that it
accepts the necessary parameters)
    '''
    pass
