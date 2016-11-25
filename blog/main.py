#!/usr/bin/env python
import webapp2
import blog


class DefaultPage(webapp2.RequestHandler):
    def get(self):
        self.redirect('/blog')


app = webapp2.WSGIApplication([
    (r'/', DefaultPage),
    (r'/blog/?', blog.BlogFront),
    (r'/blog/newpost/?', blog.NewPost),
    (r'/blog/(\d+)/?', blog.PostPage),
    (r'/blog/signup/?', blog.SignupHandler),
    (r'/blog/welcome/?', blog.WelcomePage),
    (r'/blog/login/?', blog.LoginHandler),
    (r'/blog/logout/?', blog.LogoutPage),
    (r'/blog/(\d+)/?\.json/?', blog.PostJSON),
    (r'/blog/?\.json/?', blog.BlogJSON),
    (r'/blog/flush/?', blog.FlushCache)
], debug=True)
