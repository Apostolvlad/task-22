import time

def set(func):
    def wrapper(*arg, **kwarg):
        func_name = func.__qualname__
        print('run', func_name)
        start_time = time.monotonic()
        result = func(*arg, **kwarg)
        end_time = time.monotonic()
        print('finish', func_name, ':', end_time - start_time)
        return result
    return wrapper