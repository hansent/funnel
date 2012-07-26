import re
import uuid
import types
import logging
import tornado.web
import tornado.options
import funnel.handlers
import funnel.util
import os.path
import tornado.options

config = funnel.util.YamlConfig()
config.parse_yaml("""
tornado:
    logging :  'info'
    log_to_stderr : true
    #log_file_num_backups : 1
    #log_file_prefix :  'tornado.log'

Application:
    static_path : 'static'
    static_url_prefix : '/static/'
    template_path:  'templates'
    cookie_secret : 'NOT SO SECRET'
    login_url : '/login'
    login_home : '/profile'
    signup_url : '/signup'
""")

if os.path.exists('config.yaml'):
    config.parse_file("config.yaml")
else:
    logging.warning("No default 'config.yaml found'")

tornado.options.parse_command_line()
for k,v in config['tornado'].iteritems():
    tornado.options.options[k] = v



class URLRoute(tornado.web.URLSpec):
    def __repr__(self):
        info = (self._path, self._group_count, self.name, self.kwargs)
        return "<URLRoute: '%s' =%d=> %s(%s) >" % info


class RouteList(list):
    def __init__(self, routes=None, prefix=""):
        self._prefix = prefix
        super(RouteList, self).__init__()
        if routes:
            self.extend(routes)

    def add_route(self, pattern, handler, kwargs={}, name=None):
        if isinstance(handler, basestring):
            handler = tornado.util.import_object(handler)
        route_name = name or handler.__name__
        url_spec = URLRoute(pattern, handler, kwargs, route_name)
        self.append(url_spec)
        logging.info(" '%s' ==> [%s.%s] " % (pattern, handler.__module__, handler.__name__))
        return url_spec

    def add_redirect(self, url_from, url_to, name=None):
        redirect = tornado.web.RedirectHandler(dict(url=url_to), name=name)
        self._routes.append( URLRoute(url_from, redirect) )

    def extend(self, iterable):
        for item in iterable:
            if isinstance(item, tornado.web.URLSpec):
                self.append(item)
            elif isinstance(item, RouteList):
                self.extend(item)
            else:
                self.add_route(*item)

    #add/concatenate with other RouteList or list of (url, handler) tuples
    def __add__(self, iterable):
        result = RouteList(self)
        result.extend(iterable)
        return result


    #use as decorator for RequestHandlers, to add them to this RouteSet
    def __call__(self, pattern):
        def route_decorator(handler_class):
            self.add_route(pattern, handler_class)
            return handler_class
        return route_decorator






class ApplicationMeta(type):
    def __new__(cls, name, bases, attrs):
        attrs['routes'] = RouteList(attrs.get('routes'))
        attrs['route'] = attrs['routes']
        return super(ApplicationMeta, cls).__new__(cls, name, bases, attrs)


class Application(tornado.web.Application):
    __metaclass__ = ApplicationMeta
    UserModel = None 
    routes = None

    def __init__(self, **settings):
        #use options key/values from config file        
        _settings = self._get_settings(**settings)
        super(Application,self).__init__(None, **_settings)
        self.add_handlers(".*$", self.routes)
        self.setup()

    def setup(self):
        pass

    def _get_settings(self, **kwargs):
        settings = {}
        classes = [self.__class__.__name__]
        for base in self.__class__.__bases__:
            classes.insert(0,base.__name__)
        for cls_name in classes:
            cls_config = funnel.config.get(cls_name, {})
            funnel.util.merge_dicts(settings, cls_config, inplace=True)
        funnel.util.merge_dicts(settings, kwargs, inplace=True)
        return settings

    def _get_host_pattern_handlers(self, host_pattern):
        if not host_pattern.endswith("$"):
            host_pattern += "$"
        handlers = None
        for h in self.handlers:
            if h[0].pattern == host_pattern:
                handlers = h[1]
                break
        if handlers == None:
            handlers = []
            self.handlers.append((re.compile(host_pattern), handlers))
        return handlers

    def add_handlers(self, host_pattern, host_handlers):
        for spec in host_handlers:
            self.add_handler(spec, host_pattern)

    def add_handler(self, spec, host_pattern=".*$"):
        handlers = self._get_host_pattern_handlers(host_pattern)
        if type(spec) is type(()):
            assert len(spec) in (2, 3)
            pattern = spec[0]
            handler = spec[1]
            if isinstance(handler, str):
                # import the Module and instantiate the class
                # Must be a fully qualified name (module.ClassName)
                handler = tornado.util.import_object(handler)
            if len(spec) == 3:
                kwargs = spec[2]
            else:
                kwargs = {}
            spec = tornado.web.URLSpec(pattern, handler, kwargs)
        handlers.append(spec)
        if spec.name:
            if spec.name in self.named_handlers:
                logging.warning(
                    "Multiple handlers named %s; replacing previous value",
                    spec.name)
            self.named_handlers[spec.name] = spec





def start_ioloop():
    tornado.ioloop.IOLoop.instance().start()
