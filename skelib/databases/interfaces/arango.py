"""
Arango database interface module.
"""


import pdb

import json
import re
import logging

from arango import ArangoClient as AC
import jsonpickle as jp

from skelib.utils import str_to_dict, has_jp_sig, zip_dict


__all__ = ['get_adbi']

AC_PARAMS = [
    'ADB_USERNAME',
    'ADB_PASSWORD',
    'ADB_HOST',
    'ADB_PORT',
]
ADBI = None


class ADBIError(Exception):
    pass

class ArangoCollectionWrapper():
    """Wrap ADB collections to provide extended ops."""

    def __init__(self, coll, parent=None):
        self._coll = coll
        self.log = logging
        self._callbacks = {'c': {}, 'r': {}, 'u': {}, 'd': {}}  # create, read, update, delete
        return

    def __getitem__(self, filter_):
        """Return a list of documents matching the filter."""
        query = str_to_dict(filter_)
        matches = [
            self.unserialize_complex(d)
            for d in self._coll.find(query).batch()
        ]

        for cb in self._callbacks['r'].values():
            cb(matches)
        return matches

    def __setitem__(self, key, doc):
        """Insert or update a document."""
        if isinstance(key, str): doc['_key'] = key
        if isinstance(key, dict): doc['_key'] = key['_key']
        key = doc['_key']
        if not isinstance(key, str):
            raise ADBIError(
                f'Document "_key" must be str, not {type(key)}'
            )
        doc = self.serialize_complex(doc)

        if not self._coll.has(key):
            self._coll.insert(doc)

            for cb in self._callbacks['c'].values():
                cb(doc)

        else:
            self._coll.update(doc)

            for cb in self._callbacks['u'].values():
                cb(doc)
        return

    def __getattr__(self, name):
        """Return attribute on the wrapped collection."""

        try:
            return getattr(self._coll, name)

        except Exception as e:
            print(f'Break in ACW: {repr(e)}')
            #pdb.post_mortem()
        return

    def __call__(self, *docs, **rest):
        """Insert one or more documents."""
        if False in [
                isinstance(d, dict)
                for d in docs
        ]: raise ADBIError('Bad document type found.')
        if isinstance(docs, tuple): docs = list(docs)
        #pdb.set_trace()
        if not isinstance(docs, list):
            newline, tab = '\n', '\t'
            raise ADBIError(
                f'Bad document type; must be a dict or list of dict but got {repr(docs).replace(newline, tab)} which is a {type(docs)}'
            )

        for cb in self._callbacks['c'].values():
            cb(docs)
        docs = [
            self.serialize_complex(d)
            for d in docs
        ]
        return self._coll.insert_many(docs)

    def __contains__(self, key):
        """Return true if the specified document exists"""
        if isinstance(key, dict): key = key['_key']
        return self._coll.has(key)

    def serialize_complex(self, obj, native=[]):
        """Make complex objects serializable"""
        # TODO: move to extern lib as object method
        #pdb.set_trace()
        if isinstance(obj, dict):
            ser_obj = {}

            for key in obj:

                try:
                    # TODO: should check for primitives instead?
                    json.loads(json.dumps(obj[key]))
                    ser_obj[key] = obj[key]

                except TypeError:
                    ser_obj[key] = jp.dumps(obj[key])
            return ser_obj

        else:
            raise NotImplementedError(f'{type(obj)} is currently unsupported')

    def unserialize_complex(self, ser_obj, native=[]):
        """Unserialize complex objects."""

        if isinstance(ser_obj, dict):
            obj = {}

            for key in ser_obj:

                if  has_jp_sig(ser_obj[key]):
                    obj[key] = jp.loads(ser_obj[key])

                else:
                    obj[key] = ser_obj[key]
            return obj

        else:
            raise NotImplementedError(f'{type(obj)} is currently unsupported')

    def all(self):
        """Return all documents in the collection."""
        return [
            self.unserialize_complex(doc)
            for doc in self._coll.all().batch()
        ]

    def callback(self, name='', cb=None, action='add', targets='cu'):
        """Handle callbacks."""
        if action == 'add' and not callable(cb): raise ADBIError(f'Invalid callback {cb} given.')
        if not name: name = repr(cb)

        if action == 'add':

            for t in targets:
                self._callbacks[t][name] = cb

class ArangoDBInterface():
    """Wrap an ArangoDB database object."""

    def __init__(self, config):
        clt = AC(**{
            p[4:].lower(): config.get(p)
            for p in config
            if p in AC_PARAMS
        })
        self._adb = clt.database(config.get('ADB_NAME'))
        self._clt = clt
        self._colls = {}
        self.log = logging
        return

    def __getattr__(self, name):
        """Access collections as attributes."""

        try:

            if name in self._colls:
                return self._colls[name]

            else:
                coll = ArangoCollectionWrapper(self._adb.collection(name))
                self._colls[name] = coll
                return coll

        except Exception as e:
            print(f'Break in ADBI __getattr__: {repr(e)}')
            #pdb.post_mortem()
        return


def get_adbi(config=None, share=True):
    """Return an ArangoDBInterface object, shared or new.
    """
    global ADBI
    adbi = None
    if not config and share and ADBI: return ADBI
    if config: adbi = ArangoDBInterface(config)
    if config and share and not ADBI: ADBI = adbi
    if not adbi: raise ADBIError('Something went wrong while creating the interface.')
    return adbi

