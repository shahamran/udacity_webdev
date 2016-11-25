import re

from google.appengine.ext import db

from lib import utils


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
        pw_hash = utils.make_pw_hash(name, pw)
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


def valid_pw(name, pw, hash):
    return utils.valid_pw(name, pw, hash)
