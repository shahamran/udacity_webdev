import webapp2

from lib import utils, templates
from lib.db import Users

COOKIE_NAME = 'user_id'


class Handler(webapp2.RequestHandler):
    """
    Base handler class. Defines useful functions to render templates and
    write responses.
    """

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **kw):
        return templates.render_str(template, **kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = utils.make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and utils.check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie(COOKIE_NAME, user.key().id())

    def logout(self):
        self.response.headers.add_header('Set-Cookie',
                                         COOKIE_NAME + '=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie(COOKIE_NAME)
        self.user = uid and Users.User.by_id(int(uid))
