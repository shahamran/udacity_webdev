import json

from handlers import Handler
from lib.db import Users
from lib.db.Posts import Post


from google.appengine.api import memcache
from datetime import datetime, timedelta
import time


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


def top_posts(update=False):
    key = 'TOP_POSTS'
    posts, age = age_get(key)
    if update or (posts is None):
        posts = Post.all().order('-created').fetch(limit=10)
        age_set(key, posts)
        age = 0

    return posts, age


def add_post(post):
    post.put()
    post_id = post.key().id()
    time.sleep(0.1)
    top_posts(update=True)
    return post_id


def age_str(age):
    age = int(age)
    return 'queried %d seconds ago' % (age)


class BlogFront(Handler):
    """
    A handler for the main page. Displays the front blog page with at most
    10 posts on it.
    """

    def get(self):
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
            post_id = add_post(p)
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


class FlushCache(Handler):
    def get(self):
        memcache.flush_all()
        self.redirect('/blog')


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
        if not Users.valid_username(username):
            params['error_username'] = "That's not a valid username."
            has_error = True
        else:
            existing_user = Users.User.by_name(username)
            if existing_user:
                params['error_username'] = "This username already exists."
                has_error = True

        if not Users.valid_password(password):
            params['error_password'] = "That's not a valid password."
            has_error = True
        elif password != verify:
            params['error_verify'] = "Your passwords didn't match."
            has_error = True

        if not Users.valid_email(email):
            params['error_email'] = "That's not a valid email."
            has_error = True

        if has_error:
            self.render('signup.html', **params)
            return

        user = Users.User.register(name=username, pw=password, email=email)
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

        if not Users.valid_username(username):
            self.render_error(username)
            return

        user = Users.User.by_name(username)
        if not user:
            self.render_error(username)
            return

        if not Users.valid_pw(username, password, user.password_hash):
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
