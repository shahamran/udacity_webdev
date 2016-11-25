import hmac
import hashlib
import random
import string


DELIM = '|'
SECRET = '41oSxXU0kuHuRugauSYz'


def make_secure_val(val):
    return '%s%s%s' % (val, DELIM, hmac.new(SECRET, str(val)).hexdigest())


def check_secure_val(secure_val):
    val = secure_val.split(DELIM)
    if val:
        val = val[0]
    if make_secure_val(val) == secure_val:
        return val


def make_salt(length=5):
    return ''.join(random.choice(string.ascii_letters) for x in range(length))


def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s%s%s' % (h, DELIM, salt)


def valid_pw(name, pw, h):
    salt = h.split(DELIM)[-1]
    my_h = make_pw_hash(name, pw, salt)
    return h == my_h
