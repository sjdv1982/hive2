_cache = {}


def memoize(func):
    func_cache = _cache[func] = {}

    def wrapper(self, *args):
        key = self, args

        try:
            return func_cache[key]

        except KeyError:
            result = func_cache[key] = func(self, *args)
            return result

    return wrapper