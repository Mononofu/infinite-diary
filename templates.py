import jinja2
import os

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

indexTemplate = jinja_environment.get_template('templates/index.html')
entryTemplate = jinja_environment.get_template('templates/entry.html')
attachmentTemplate = jinja_environment.get_template(
  'templates/attachment.html')
entryEditTemplate = jinja_environment.get_template(
  'templates/entry_edit.html')
backupTemplate = jinja_environment.get_template('templates/backup.html')
