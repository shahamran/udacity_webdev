#!/usr/bin/env python
import os
import webapp2
import jinja2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def render_str(template, **kw):
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


class Post(db.Model):
    """The blog-posts database for the datastore"""
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class MainPage(Handler):
    """
    A handler for the main page. Displays the front blog page with at most
    10 posts on it.
    """

    def render_front(self):
        posts = db.GqlQuery(
            "SELECT * FROM Post ORDER BY created DESC LIMIT 10"
        )
        self.render("front.html", posts=posts)

    def get(self):
        self.render_front()


class NewPost(Handler):
    def render_post(self, subject="", content="", error=""):
        self.render("new_post.html",
                    subject=subject,
                    content=content,
                    error=error)

    def get(self):
        self.render_post()

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if subject and content:
            p = Post(subject=subject, content=content)
            post_id = p.put().id()
            self.redirect("/blog/%d" % post_id)
        else:
            error = "we need both a subject and some content!"
            self.render_post(subject, content, error)


class PostHandler(Handler):
    def get(self, post_id):
        if post_id:
            post_id = int(post_id)
            post = Post.get_by_id(post_id)
            self.render("post.html", post=post)
        else:
            self.error("404")


app = webapp2.WSGIApplication([
    (r'/blog/?', MainPage),
    (r'/blog/newpost/?', NewPost),
    (r'/blog/(\d+)/?', PostHandler)
], debug=True)
