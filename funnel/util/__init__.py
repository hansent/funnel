import yaml
import json
import datetime
import decimal
import tornado.httpclient
from funnel.util.rfc822 import email_address_re

def async_fetch(url, response_callback):
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch(url, response_callback)


def validate_email(email):
    return email_address_re.match(email) != None


def merge_dicts(original, update, inplace=False):
    '''Recursively updates dictionary'''
    if inplace:
        return _merge_dicts_inplace(original, update)
    #if not inplace, merge {} <- original <- updates
    return _merge_dicts_inplace({}, original, update)

def _merge_dicts_inplace(original, *updates):
    for update in updates:
        for key, val in update.iteritems():
            if isinstance(val, dict):
                section = original.setdefault(key,{})
                _merge_dicts_inplace(section, val)
            else:
                original[key] = val
    return original


class _property(object):
    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__

class classproperty(_property):
    def __get__(self, obj, cls):
        return self.fget(cls)

class cached_property(_property):
    def __get__(self, obj, cls):
        if obj is None:
            return self
        setattr(obj, self.__name__, self.fget(obj))
        return getattr(obj, self.__name__)

class cached_classproperty(cached_property):
    def __get__(self, obj, cls):
        setattr(cls, self.__name__, self.fget(cls))
        return getattr(cls, self.__name__)


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode datetime types and 
    """
    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            if o.microsecond:
                r = r[:23] + r[26:]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        if isinstance(o, datetime.time):
            if o.tzinfo is not None and o.tzinfo.utcoffset(o) is not None:
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        if isinstance(o, decimal.Decimal):
            return str(o)
        if hasattr(o, '__jsonic__'):
            return o.__jsonic__()
        return super(JSONEncoder, self).default(o)


class YamlConfig(dict):
    def parse_file(self, fname="config.yaml"):
        with open(fname, 'r') as config_file:
            self.parse_yaml(config_file)

    def parse_yaml(self, yaml_src):
        update = yaml.load(yaml_src)
        merge_dicts(self, update, inplace=True)

        for k,v in self['tornado'].iteritems():
            tornado.options.options[k].set(v)

    def __getattr__(self, name):
        return self[name]





