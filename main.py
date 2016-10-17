#!/usr/bin/env python
import os
import re
import string
import random
import hashlib

import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


# ===== Blog Stuff =====

class Post(db.Model):
    """The blog-posts database for the datastore"""
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p=self)


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


def render_post(response, post):
    response.out.write('<b>' + post.subject + '</b><br>')
    response.out.write(post.content)


class BlogFront(Handler):
    """
    A handler for the main page. Displays the front blog page with at most
    10 posts on it.
    """

    def get(self):
        posts = db.GqlQuery(
            "SELECT * FROM Post ORDER BY created DESC LIMIT 10"
        )
        self.render("front.html", posts=posts)


class NewPost(Handler):
    def get(self):
        self.render("new_post.html")

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')

        if subject and content:
            p = Post(subject=subject, content=content)
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
        post_id = int(post_id)
        post = Post.get_by_id(post_id)
        if not post:
            self.error(404)
            return

        self.render("permalink.html", post=post)


# ===== User accounts =====

class User(db.Model):
    """A user in the blog"""
    name = db.StringProperty(required=True)
    password_hash = db.StringProperty(required=True)
    email = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)


USER_RE = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')
PASS_RE = re.compile(r'^.{3,20}$')
EMAIL_RE = re.compile(r'^[\S]+@[\S]+\.[\S]+$')

DELIM = '|'
COOKIE_NAME = 'user_id'


def valid_username(username):
    return username and USER_RE.match(username)


def valid_password(password):
    return password and PASS_RE.match(password)


def valid_email(email):
    return not email or EMAIL_RE.match(email)


def make_salt():
    return ''.join(random.choice(string.ascii_letters) for x in range(5))


def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s%s%s' % (h, DELIM, salt)


def hash_str(s):
    return hashlib.sha256(str(s)).hexdigest()


def make_secure_val(s):
    return '%s%s%s' % (s, DELIM, hash_str(s))


def check_secure_val(h):
    s, hash_s = h.split(DELIM)
    if hash_str(s) == hash_s:
        return s


def valid_pw(name, pw, h):
    salt = h.split(DELIM)[-1]
    my_h = make_pw_hash(name, pw, salt)
    return h == my_h


def create_user_cookie(response, user_id):
    cookie_val = make_secure_val(user_id)
    response.headers.add_header(
        'Set-Cookie', '%s=%s; Path=/' % (COOKIE_NAME, cookie_val)
    )


def create_new_user(response, name, password, email):
    password_hash = make_pw_hash(name, password)
    user = User(name=name, password_hash=password_hash, email=email)
    create_user_cookie(response, user.put().id())


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
            existing_user = db.GqlQuery(
                "SELECT * FROM User WHERE name = '%s'" % username
            ).get()
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
        else:
            create_new_user(self.response, username, password, email)
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

        user = User.gql("WHERE name = '%s'" % username).get()
        if not user:
            self.render_error(username)
            return

        if not valid_pw(username, password, user.password_hash):
            self.render_error(username)
            return

        create_user_cookie(self.response, user.key().id())
        self.redirect('/blog/welcome')


class WelcomePage(Handler):
    def get(self):
        cookie_val = self.request.cookies.get(COOKIE_NAME)
        if cookie_val:
            user_id = check_secure_val(cookie_val)
            if user_id:
                user_id = int(user_id)
                user = User.get_by_id(user_id)
                self.render('welcome.html', name=user.name)
                return
        self.redirect('/blog/signup')


app = webapp2.WSGIApplication([
    (r'/blog/?', BlogFront),
    (r'/blog/newpost/?', NewPost),
    (r'/blog/(\d+)/?', PostPage),
    (r'/blog/signup/?', SignupHandler),
    (r'/blog/welcome/?', WelcomePage),
    (r'/blog/login/?', LoginHandler)
], debug=True)
