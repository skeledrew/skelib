"""
Newly made utils.
"""


import pdb
#from ptpython.repl import embed

import re
from importlib import import_module
from os.path import exists, isfile, join, sep
from functools import wraps


"""
Plugin manager loads plugin modules from given dirs based on include regex, calls a designated function that should provide a collection of callables, and calls another calable from a using object with the callables.
- get using callable (w/ double dispatcher?)
- get list of files from dirs w/ `os.listdirs`
- select required with regex
- attempt to load w/ `import_module`
- check for and call named/std func, or get all
- get returned callables
- store callables in dict
- pass each to using callable
- optional FS-event triggered hot reloading
"""

class PluginManager():

    def __init__(self):
        self._loaded_plugins = {}
        return

    def load(
            self,
            caller,
            paths,
            include_pattern='.*',
            collector='',
            reload_triggers='',
            reverse=False,
    ):
        """Load matching modules and pass functionality to target."""
        if not callable(caller):
            raise TypeError('"caller" must be a callable.')
        if isinstance(paths, str): paths = [paths]
        if not isinstance(paths, list):
            raise TypeError('"paths" must be a string or list.')
        if not all((isinstance(path, str) and exists(path)) for path in paths):
            raise OSError('Bad or non-existent path found.')
        pattern = re.compile(include_pattern)
        if not isinstance(collector, str):
            raise TypeError('"collector" must be a string.')
        files = []

        for path in paths:
            files += [
                f
                for f in get_file_list(path)
                if (isfile(f) and pattern.match(f))
            ]
        modules = {
            f: import_module(f.split('.')[0].replace(sep, '.'))
            for f in files
            # TODO: check for FS events here?
        }
        # TODO: save in loaded dict
        call_coll = [
            getattr(mod, collector)()
            for mod in modules.values()
            if hasattr(mod, collector)
        ]
        [
            [
                caller(callee)
                for callee in coll
            ]
            for coll in call_coll
        ]
        return

class DecoTest():
    """Testing decorator."""

    def __init__(
            self,
            data=[],
            handler=None,
            collector=None,
            analyzer=None,
    ):
        if callable(data): data = data()
        if not (
                isinstance(data, list)
                and all(isinstance(itm, dict) for itm in data)
        ):
            raise TypeError('"data" must be a list of dicts')
        self._data = data
        self._enabled = False
        if callable(handler): self._handler = handler
        self._collect = True
        if callable(collector): self._process_collected = collector
        if callable(analyzer): self._process_test_stats = analyzer
        self._ignore_exceptions = False
        self._debug = False
        return

    def __get__(self, obj, type=None):
        # descriptor in decorator hack
        # http://www.ianbicking.org/blog/2008/10/decorators-and-descriptors.html
        #if obj is None: return self
        new_func = self.func.__get__(obj, type)
        return self.__class__(new_func)

    def __call__(self, func):
        self._handler(self)
        self._func_name = func.__name__

        @wraps(func)
        def wrapper(*args, **kwds):
            if self._debug: pdb.set_trace()

            if not self._enabled:
                # testing mode disabled
                if not self._collect: return func(*args, **kwds)
                retv = None
                exc = None

                try:
                    retv = func(*args, **kwds)

                except Exception as e:
                    exc = e
                self._process_collected({
                    'args': args,
                    'kwds': kwds,
                    'retv': retv,
                    'exc': exc,
                })
                if exc and not self._ignore_exceptions: raise exc
                return retv

            else:
                # testing enabled
                self._setup()
                stats = []

                for data in self._data:
                    argv = data.get('argv')
                    args = argv[0] if argv and isinstance(argv[0], list) else []
                    kwds = argv[-1] if argv and isinstance(argv[-1], dict) else {}
                    stat = {}

                    try:

                        retv = func(*args, **kwds)
                        if 'retv' in data:
                            if not retv == data['retv']:
                                stat['retv'] = retv

                        if 'rett' in data:
                            if not isinstance(retv, data['rett']):
                                stat['rett'] = type(retv)

                        if 'retf' in data:
                            stat['retf'] = data['retf'](retv)

                    except Exception as e:
                        if 'exc' in data:
                            if not type(e) in data['exc']:
                                stat['exc'] = e
                                #stats.append(stat)
                                continue
                            stats.append(stat)
                            continue
                        stat['exc'] = e  # unanticipated
                    stats.append(stat)
                self._teardown()
                self._process_test_stats(stats)
        return wrapper

    def _process_collected(self, colld):
        print(f'Collected: {colld}')
        return

    def _process_test_stats(self, stats):
        print('Test stats: {}'.format([
            'successful!' if not s else s
            for s in stats
        ]))
        return

    def _handler(self, _):
        print('Default handler active.')
        return

    def _setup(self):
        print('Nothing to setup.')
        return

    def _teardown(self):
        print('Nothing to teardown.')
        return

    def enabled(self, bln):
        self._enabled = not not bln
        return

    def collect(self, bln):
        self._collect = not not bln
        return

    def configure(self, **kwds):

        for key in kwds:
            val = kwds[key]
            if not hasattr(self, key): key = f'_{key}'
            setattr(self, key, val)
        return self

    def debug(self, bln):
        self._debug = not not bln
        return


def try_except(
        error_action=lambda err: print(
            f'Something broke: {repr(err)}'
        ),
        errors=(Exception, ),
):
    """Decorate functions with try-except and option to call another function on exception."""

    def decorator(func):

        def wrapper(*args, **kwargs):

            try:
                return func(*args, **kwargs)

            except Exception as e:
                return error_action(e)
        return wrapper
    return decorator

def add(a, b):
    """Just a test function."""
    c = a + b
    print(f'Sum is {c}')
    return c


if __name__ == '__main__':
    #embed(globals(), locals())
    pass
