#!/usr/bin/env python
import os
import re
from string import ascii_letters
import random
import hmac
import hashlib
import json

import webapp2
import jinja2

from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)

SECRET = '41oSxXU0kuHuRugauSYz'
DELIM = '|'
COOKIE_NAME = 'user_id'


# ===== Blog Stuff =====

def make_secure_val(val):
    return '%s%s%s' % (val, DELIM, hmac.new(SECRET, str(val)).hexdigest())


def check_secure_val(secure_val):
    val = secure_val.split(DELIM)
    if val:
        val = val[0]
    if make_secure_val(val) == secure_val:
        return val


def make_salt(length=5):
    return ''.join(random.choice(ascii_letters) for x in range(length))


def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s%s%s' % (h, DELIM, salt)


def valid_pw(name, pw, h):
    salt = h.split(DELIM)[-1]
    my_h = make_pw_hash(name, pw, salt)
    return h == my_h


class Post(db.Model):
    """The blog-posts database for the datastore"""
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    created_by = db.StringProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p=self)

    def create_dict(self):
        return dict(subject=self.subject, content=self.content,
                    created=self.created.strftime('%a %b %d %H:%M:%S %Y'))

    def create_json(self):
        return json.dumps(self.create_dict())


def render_str(template, **kw):
    """Renders a template with the given keyword arguments"""
    t = jinja_env.get_template(template)
    return t.render(**kw)


class Handler(webapp2.RequestHandler):
    """
    Base handler class. Defines useful functions to render templates and
    write responses.
    """

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **kw):
        return render_str(template, **kw)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie(COOKIE_NAME, user.key().id())

    def logout(self):
        self.response.headers.add_header('Set-Cookie',
                                         COOKIE_NAME + '=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie(COOKIE_NAME)
        self.user = uid and User.by_id(int(uid))


# === Memcache wrapper ===
def age_set(key, val):
    save_time = datetime.utcnow()
    memcache.set(key, (val, save_time))


def age_get(key):
    cached_val = memcache.get(key)
    if cached_val:
        val, save_time = cached_val
        age = (datetime.utcnow() - save_time).total_seconds()
    else:
        val, age = None, 0

    return val, age


class FlushCache(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')
# =========================


def top_posts(update=False):
    key = 'TOP_POSTS'
    posts, age = age_get(key)
    if posts is None or update:
        posts = Post.all().order('-created').fetch(limit=10)
        posts = list(posts)
        age_set(key, posts)

    return posts, age


def add_post(post):
    post.put()
    top_posts(update=True)
    return str(post.key().id())


def age_str(age):
    age = int(age)
    return 'queried %d seconds ago' % (age)


class BlogFront(Handler):
    """
    A handler for the main page. Displays the front blog page with at most
    10 posts on it.
    """

    def get(self):
        global query_time

        posts, age = top_posts()
        self.render("front.html",
                    posts=posts,
                    age=age_str(age))


class JSONHandler(Handler):
    def get(self, post_id=None):
        self.response.headers.add_header('Content-Type',
                                         'application/json; charset=UTF-8')
        self.done(post_id)

    def done(self, post_id):
        raise NotImplementedError


class BlogJSON(JSONHandler):
    def done(self, post_id):
        posts = Post.all().order('-created').fetch(limit=10)
        posts_dicts = [post.create_dict() for post in posts]
        self.write(json.dumps(posts_dicts))


class PostJSON(JSONHandler):
    def done(self, post_id):
        post = Post.get_by_id(int(post_id))
        if not post:
            self.error(404)
        else:
            self.write(post.create_json())


class NewPost(Handler):
    def get(self):
        self.render("new_post.html")

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')
        user = self.user.name if self.user else ''

        if subject and content:
            p = Post(subject=subject, content=content, created_by=user)
            post_id = p.put().id()
            self.redirect("/blog/%d" % post_id)
        else:
            error = "we need both a subject and some content!"
            self.render("new_post.html",
                        subject=subject,
                        content=content,
                        error=error)


class PostPage(Handler):
    def get(self, post_id):
        post_key = 'POST_%s' % post_id

        post, age = age_get(post_key)

        if not post:
            post_id = int(post_id)
            post = Post.get_by_id(post_id)
            age_set(post_key, post)
            age = 0

        if not post:
            self.error(404)
            return

        self.render("permalink.html",
                    post=post,
                    age=age_str(age))


# ===== User accounts =====

class User(db.Model):
    """A user in the blog"""
    name = db.StringProperty(required=True)
    password_hash = db.StringProperty(required=True)
    email = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_id(cls, uid):
        return cls.get_by_id(uid)

    @classmethod
    def by_name(cls, name):
        return cls.all().filter('name =', name).get()

    @classmethod
    def register(cls, name, pw, email=None):
        pw_hash = make_pw_hash(name, pw)
        return cls(name=name, password_hash=pw_hash, email=email)

    @classmethod
    def check_login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.password_hash):
            return u


USER_RE = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')
PASS_RE = re.compile(r'^.{3,20}$')
EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')


def valid_username(username):
    return username and USER_RE.match(username)


def valid_password(password):
    return password and PASS_RE.match(password)


def valid_email(email):
    return not email or EMAIL_RE.match(email)


class SignupHandler(Handler):
    def get(self):
        self.render("signup.html")

    def post(self):
        has_error = False
        username = self.request.get('username')
        password = self.request.get('password')
        verify = self.request.get('verify')
        email = self.request.get('email')

        params = dict(username=username, email=email)
        if not valid_username(username):
            params['error_username'] = "That's not a valid username."
            has_error = True
        else:
            existing_user = User.by_name(username)
            if existing_user:
                params['error_username'] = "This username already exists."
                has_error = True

        if not valid_password(password):
            params['error_password'] = "That's not a valid password."
            has_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords didn't match."
            has_error = True

        if not valid_email(email):
            params['error_email'] = "That's not a valid email."
            has_error = True

        if has_error:
            self.render('signup.html', **params)
            return

        user = User.register(name=username, pw=password, email=email)
        user.put()

        self.login(user)
        self.redirect('/blog/welcome')


class LoginHandler(Handler):
    def render_error(self, username=''):
        self.render('login.html',
                    username=username,
                    error='Invalid login.')

    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        if not valid_username(username):
            self.render_error(username)
            return

        user = User.by_name(username)
        if not user:
            self.render_error(username)
            return

        if not valid_pw(username, password, user.password_hash):
            self.render_error(username)
            return

        self.login(user)
        self.redirect('/blog/welcome')


class LogoutPage(Handler):
    def get(self):
        self.logout()
        self.redirect('/blog/signup')


class WelcomePage(Handler):
    def get(self):
        if self.user:
            self.render('welcome.html', name=self.user.name)
        else:
            self.redirect('/blog/signup')


app = webapp2.WSGIApplication([
    (r'/blog/?', BlogFront),
    (r'/blog/newpost/?', NewPost),
    (r'/blog/(\d+)/?', PostPage),
    (r'/blog/signup/?', SignupHandler),
    (r'/blog/welcome/?', WelcomePage),
    (r'/blog/login/?', LoginHandler),
    (r'/blog/logout/?', LogoutPage),
    (r'/blog/(\d+)/?\.json/?', PostJSON),
    (r'/blog/?\.json/?', BlogJSON),
    (r'/blog/flush/?', FlushCache)
], debug=True)
