import os
import jinja2

template_dir = os.path.join(os.path.dirname(__file__), '..')
template_dir = os.path.join(template_dir, 'templates')
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                               autoescape=True)


def render_str(template, **kw):
    """Renders a template with the given keyword arguments"""
    t = jinja_env.get_template(template)
    return t.render(**kw)
