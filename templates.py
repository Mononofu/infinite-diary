import jinja2
import os

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

indexTemplate = jinja_environment.get_template('templates/index.html')
entryTemplate = jinja_environment.get_template('templates/entry.html')
attachmentTemplate = jinja_environment.get_template(
  'templates/attachment.html')
entryAppendTemplate = jinja_environment.get_template(
  'templates/entry_append.html')
