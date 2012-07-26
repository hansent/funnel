import logging
import socket
import json
import urllib
import urlparse
import tornado.web
from lepl.apps import rfc3696
from types import FunctionType
from funnel.util import JSONEncoder


log = logging.getLogger()

"""
def hook_before(handler_method):
    def hook_deco(func):
        if not hasattr(func, '_hooks_before'):
            func._hooks_before = []
        func._hooks_before.append(handler_method)
        return func
    return hook_deco


class BaseHandlerMeta(type):

    def __new__(self, name, bases, attrs):
        attrs['_hooks_before'] = {}
        if bases and hasattr(bases[0], '_hooks_before'):
            attrs['_hooks_before'] = dict((k,list(v)) for k,v in bases[0]._hooks_before.iteritems())
        for k,v in attrs.iteritems():
            if type(v) != FunctionType:
                continue
            if not hasattr(v,'_hooks_before'):
                continue
            for handler_method in v._hooks_before:
                hooks = attrs['_hooks_before'].setdefault(handler_method, [])
                hooks.append(v)
        klass = super(BaseHandlerMeta, self).__new__(self, name, bases, attrs)
        return klass
"""

class BaseHandler(tornado.web.RequestHandler):
    login_required = False

    @property
    def db(self):
        return self.application.db

    @property
    def settings(self):
        return self.application.settings

    def setup(self, *args, **kwargs):
        pass

    def load_json(self):
        try:
            self.json_data = json.loads(self.request.body)
            return self.json_data
        except ValueError:
            logging.error("Could not decode JSON: %s", self.request.body)
            raise tornado.web.HTTPError(400, "failed to decode JSON request body: %s" %self.request.body )

    def get_current_user(self):
        self.user = None
        user_id = self.get_secure_cookie("user")
        if user_id:
            self.user = self.application.UserModel.get_by_id(user_id)
        self.ui.user = self.user
        return self.user

    def redirect_login(self):
        #redirect to applciation login page
        url = self.settings.get('login_url', '/login')
        #come back here once loged in
        next_url = self.request.uri
        if urlparse.urlsplit(url).scheme: # absolute URL?
            next_url = self.request.full_url() 
        url += "?" + urllib.urlencode(dict(next=next_url))
        self.redirect(url)

    def _verify_login(self):
        #current_user is present and logged in!
        if self.current_user:
            return self.current_user
        # Non GET or HEAD requests -> respond with 403 unauthorized
        if self.request.method not in ("GET", "HEAD"):
            raise tornado.web.HTTPError(403)
        self.redirect_login()

    def _verify_xsrf(self):
        if self.request.method in ("POST", "PUT", "DELETE"):
            self.check_xsrf()

    def _execute(self, transforms, *args, **kwargs):
        """Executes this request with the given output transforms."""
        self._transforms = transforms
        try:
            method = self.request.method
            if method not in self.SUPPORTED_METHODS:
                raise tornado.web.HTTPError(405)

            # verify xsrf cookie on post/put request
            if self.settings.get("xsrf_cookies"):
                self.verify_xsrf()

            # if login required, make sure
            if self.login_required:
                self._verify_login()

            #call prepare regardless of HTTP method for ctHommon initialization
            if not self._finished:
                self.prepare()

            #get url routes from regex group, and call member function based
            #on which http method is used in cleint request
            if not self._finished:
                args = [self.decode_argument(arg) for arg in args]
                kwargs = dict((k, self.decode_argument(v, name=k))
                              for (k, v) in kwargs.iteritems())

                #just like prepare, but with same args/kwargs from route
                self.setup(*args, **kwargs)
                #call actual handler function fro http method used
                method = getattr(self, self.request.method.lower())
                response_data = method(*args, **kwargs)
                if response_data != None:
                    self.write_response(response_data)

                if self._auto_finish and not self._finished:
                    self.finish()

        except Exception, e:
            self._handle_request_exception(e)

    def write_response(self, response):
        if isinstance(response, unicode):
            self.write(response)
        else:
            self.write_json(response)

    def write_json(self, data):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        if self.settings['debug']:
            json_data = json.dumps(data, cls=JSONEncoder, indent=4)
        else:
            json_data = json.dumps(data, cls=JSONEncoder)
        self.write(json_data)



class BaseView(BaseHandler):
    template = "index.html"

    def get_template_path(self):
        return self.settings['template_path']

    def prepare(self):
        self._load_flashed_messages()

    def get(self, *args, **kwargs):
        self.render(self.template)

    def flash_message(self, message, key='error'):
        self._flashed_messages[key] = message

    def _load_flashed_messages(self):
        #add any messages from last request to template
        val = self.get_secure_cookie('flash_msg')
        self.ui.flashed = json.loads(val or "{}")
        #storage for messages to flash for next request
        self.clear_cookie('flash_msg')
        self._flashed_messages = {}

    def _save_flashed_messages(self):
        if self._flashed_messages:
            json_data = json.dumps(self._flashed_messages)
            self.set_secure_cookie('flash_msg', json_data)

    def finish(self, chunk=None):
        if hasattr(self, "_flashed_messages"):
            self._save_flashed_messages()
        super(BaseHandler, self).finish(chunk=chunk)


class UserView(BaseView):
    login_required = True


class LoginHandler(BaseView):
    template = "login.html"

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        url_next = self.get_argument('next', self.settings.get('login_home'))
        user = self.application.UserModel.get_by_login(username, password)
        if user:
          self.set_secure_cookie("user", "%s" % user.id)
          self.redirect(url_next)
        else:
          self.clear_cookie("user")
          self.flash_message("Login incorrect!")
          self.redirect(self.settings.get('login_url'))


class LogoutHandler(BaseHandler):
    def get(self):
      self.clear_cookie("user")
      self.redirect(self.settings.get('login_url'))


class SignupHandler(BaseView):
    template = "signup.html"
    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        password2 = self.get_argument("password_confirm")
        email = self.get_argument("email", "")
        url_next = self.get_argument('next', self.settings.get('login_home'))

        email_validator = rfc3696.Email()
        if not email_validator(email):
            self.flash_message("invalid email address!")
            self.redirect(self.settings.get('signup_url'))
            return
        if password != password2:
            self.flash_message("password do not match!")
            self.redirect(self.settings.get('signup_url'))
            return
        if len(password) < 6 :
            self.flash_message("password must be at least 6 charachter long!")
            self.redirect(self.settings.get('signup_url'))
            return
        if self.application.UserModel.get_by_username(username):
            self.flash_message("Username already taken!")
            self.redirect(self.settings.get('signup_url'))
            return

        logging.warning("register: %s, %s, %s :  %s", username, password, email, self.request.arguments)
        new_user = self.application.UserModel.register(username, password, email=email)
        self.set_secure_cookie("user", "%s" % new_user.id)
        self.redirect(url_next)





class ProxyHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ['GET', 'POST', 'CONNECT']
    proxy_source = "http://s3.amazonaws.com"

    @tornado.web.asynchronous
    def get(self, resource_name):

        def handle_response(response):
            if response.error and not isinstance(response.error,
                    tornado.httpclient.HTTPError):
                self.set_status(500)
                self.write('Internal server error:\n' + str(response.error))
                self.finish()
            else:
                self.set_status(response.code)
                for header in ('Date', 'Cache-Control', 'Server',
                        'Content-Type', 'Location'):
                    v = response.headers.get(header)
                    if v:
                        self.set_header(header, v)
                if response.body:
                    self.write(response.body)
                self.finish()

        uri = "%s/%s" % (self.proxy_source, resource_name)
        log.info("proxying: %s", uri)
        req = tornado.httpclient.HTTPRequest(url=uri,
            method=self.request.method,  follow_redirects=False,
            allow_nonstandard_methods=True)

        client = tornado.httpclient.AsyncHTTPClient()
        try:
            client.fetch(req, handle_response)
        except tornado.httpclient.HTTPError, e:
            if hasattr(e, 'response') and e.response:
                self.handle_response(e.response)
            else:
                self.set_status(500)
                self.write('Internal server error:\n' + str(e))
                self.finish()

