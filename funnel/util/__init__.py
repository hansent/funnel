import yaml
import tornado.httpclient


def _merge_dicts_inplace(original, *updates):
    for update in updates:
        for key, val in update.iteritems():
            if isinstance(val, dict):
                section = original.setdefault(key,{})
                _merge_dicts_inplace(section, val)
            else:
                original[key] = val
    return original


def merge_dicts(original, update, inplace=False):
    '''Recursively updates dictionary'''
    if inplace:
        return _merge_dicts_inplace(original, update)
    #if not inplace, merge {} <- original <- updates
    return _merge_dicts_inplace({}, original, update)



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


def async_fetch(url, response_callback):
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch(url, response_callback)


