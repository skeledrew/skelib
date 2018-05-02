"""
Util funcs.
"""


import re
from zlib import adler32


__all__ = [
    'Group',
    'has_jp_sig',
    'zip_dict',
    'str_to_dict',
    'hash_sum',
]

class Group(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        [setattr(self, k, kwargs[k]) for k in kwargs]
        return

    def __call__(self, key, val={'': [None]}):
        neut = {'': [None]}
        if not key : return ValueError('No key given')
        if val == neut:

            if isinstance(key, str):

                if not hasattr(self, key):
                    return ValueError('Key not found')

                else:
                    val = dict.__getitem__(self, key)
                    return val

            if isinstance(key, dict):
                [setattr(self, k, key[k]) for k in key]
                return True
        dict.__setitem__(self, key, val)
        setattr(self, key, val)
        return True

    def __getitem__(self, key):
        val = self.__call__(key)
        return val

    def __setitem__(self, key, val):
        self.__call__(key, val)
        return

    def to_dict(self):
        """Return a regular dict"""
        d = {k: v for k, v in zip(self.keys(), self.values())}
        return d


def has_jp_sig(obj):
    """Return true if the object has a jsonpickle signature."""
    # TODO: move extern
    jp_sig = r'\{\".+\":\s.+}'
    if isinstance(obj, str) and re.match(jp_sig, obj): return True
    return False

def zip_dict(dict_obj):
    """Return a dict zipped for dict comprehension."""
    if not isinstance(dict_obj, dict): raise TypeError(f'"zip_dict" needs a dict, not {type(dict_obj)}')
    return zip(dict_obj.keys(), dict_obj.values())

def str_to_dict(s, main_sep='&', map_sep='=', use_re=False):
    # 17-08-01 - initial
    # -12 - update to support regex
    # -09-11 - default if no value for a key
    final = {}
    items = s.split(main_sep) if not use_re else re.split(main_sep, s)

    for item in items:
        item = item.split(map_sep) if not use_re else re.split(map_sep, item)
        final[item[0]] = item[1] if len(item) == 2 else None
    return final

def hash_sum(data):
    return adler32(bytes(data, 'utf-8'))


