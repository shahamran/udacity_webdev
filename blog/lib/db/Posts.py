import json

from google.appengine.ext import db
from lib import templates


class Post(db.Model):
    """The blog-posts database for the datastore"""
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    created_by = db.StringProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return templates.render_str("post.html", p=self)

    def create_dict(self):
        return dict(subject=self.subject, content=self.content,
                    created=self.created.strftime('%a %b %d %H:%M:%S %Y'))

    def create_json(self):
        return json.dumps(self.create_dict())
