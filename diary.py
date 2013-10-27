import webapp2
import jinja2
import os
import re
import logging
import base64
import time
import datetime
import json
from google.appengine.ext import blobstore
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import files, images, mail
from google.appengine.ext.webapp import blobstore_handlers

from pytz.gae import pytz

from config import *
from models import *

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

indexTemplate = jinja_environment.get_template('templates/index.html')
entryTemplate = jinja_environment.get_template('templates/entry.html')
attachmentTemplate = jinja_environment.get_template(
  'templates/attachment.html')
entryAppendTemplate = jinja_environment.get_template(
  'templates/entry_append.html')

local_tz = pytz.timezone('Europe/London')


def markup_text(text):
  def add_a_tag(match):
    return "<a href='%s'>%s</a>" % (match.group(0), match.group(0))
  text = re.sub("https?://([0-9a-zA-Z-]+)(\.[a-zA-Z0-9]+){1,6}[\S]*",
    add_a_tag, text)

  return text.replace("\n", "<br>\n")


class MainPage(webapp2.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    older_than = int(self.request.get("older_than",
        datetime.datetime.now().date().toordinal() + 1))
    older_than = datetime.date.fromordinal(older_than)

    body = ""

    oldest = datetime.datetime.now().date().toordinal() + 1

    for e in Entry.all().filter("date <", older_than).order('-date').run(
        limit=20):
      attachments = ""
      for a in Attachment.all().filter("entry =", e.key()):
        attachments += attachmentTemplate.render({
          'name': a.name,
          'thumbnail': a.thumbnail,
          'key': a.key()
        })
      body += entryTemplate.render({
        'entry_day': e.date.strftime("%A, %d %B"),
        'content': markup_text(e.content),
        'creation_time': pytz.utc.localize(e.creation_time).astimezone(
            local_tz).strftime("%A, %d %B - %H:%M"),
        'attachments': attachments,
        'key': e.key()
      })
      oldest = e.date.toordinal()

    nav = """
<div class='row'>
  <div class='span4 offset4'>
    <a href='/?older_than=%d'>Newer</a> -- <a href='/?older_than=%d'>Older</a>
  </div>
</div>""" % (oldest + 41, oldest)

    body = nav + body + nav
    self.response.out.write(indexTemplate.render({
      'title': 'Home',
      'body': body
    }))


class BackupEntries(webapp2.RequestHandler):
  def get(self):
    entries = [e.to_dict() for e in Entry.all().order('-date')]
    self.response.headers['Content-Type'] = "application/json"
    self.response.headers['Content-Disposition'] = (
        "attachment; filename=entries.json")
    self.response.out.write(json.dumps(entries))


class HandleBackup(webapp2.RequestHandler):
  def get(self):
    self.response.out.write(indexTemplate.render({
      'title': 'Backup',
      'body': """
<a href="/backup/entries">Create Backup</a>
<form action="/backup" method="post" enctype="multipart/form-data">
  <input type="file" name="entries"/>
  <input type="submit" value="Submit">
</form>""",
      'active_page': 'backup'
    }))

  def post(self):
    rawEntries = self.request.get("entries")
    entries = json.loads(rawEntries)
    for e in entries:
      newEntry = Entry()
      newEntry.from_json(e)
      newEntry.put()

      self.redirect("/backup")


class ShowAttachments(webapp2.RequestHandler):
  def get(self):
    attachments = ""
    for a in Attachment.all():
      attachments += attachmentTemplate.render({
            'name': a.name,
            'thumbnail': a.thumbnail,
            'key': a.key()
      })
    self.response.out.write(indexTemplate.render({
        'title': 'Attachments',
        'body': attachments,
        'active_page': 'attachments'
    }))


class EntryAppendForm(webapp2.RequestHandler):
  def get(self, key):
    e = Entry.get(key)
    body = entryAppendTemplate.render({
      'entry_day': e.date.strftime("%A, %d %B"),
      'content': markup_text(e.content),
      'key': e.key()
    })

    self.response.out.write(indexTemplate.render({
      'title': 'Append to Entry',
      'body': body
    }))


class EntryAppendSubmit(webapp2.RequestHandler):
  def post(self):
    key = self.request.get('key')
    try:
      e = Entry.get(key)
      content = self.request.get('content')
      e.content += "\n\n<b>extended on %s</b>\n%s" % (
        pytz.utc.localize(datetime.datetime.now()).astimezone(
            local_tz).strftime("%A, %d %B - %H:%M"),
        content)
      e.put()
      self.redirect("/")
    except Exception as e:
      self.response.out.write(indexTemplate.render({
        'title': 'Append to Entry',
        'body': "Error: No entry for key %s, exception %s" % (key, e)
      }))


class ServeAttachment(blobstore_handlers.BlobstoreDownloadHandler):
  def get(self, key):
    a = Attachment.get(key)
    self.send_blob(a.content, content_type=a.content_type)


class ShowIdeas(webapp2.RequestHandler):
  def scrape_ideas(self, text):
    return [line.split(":", 2)[1] for line in text.split("\n")
      if line.startswith("--") and "idea" in line and ":" in line]

  def get(self):
    ideas = []
    for e in Entry.all().order('-date'):
      if "--" in e.content:
        ideas += self.scrape_ideas(e.content)

    body_text = "<ul>\n"
    for idea in ideas:
      body_text += "\t<li>%s</li>\n" % idea
    body_text += "</ul>"

    self.response.out.write(indexTemplate.render({
        'title': 'Ideas',
        'body': body_text,
        'active_page': 'ideas'
    }))


class ShowToDo(webapp2.RequestHandler):
  def get(self):
    todos = []
    for t in ToDo.all().order('-date'):
      todos.append(t.content)

    body_text = "<ul>\n"
    for t in todos:
      body_text += "\t<li>%s</li>\n" % t
    body_text += "</ul>"

    self.response.out.write(indexTemplate.render({
        'title': 'To-Do',
        'body': body_text,
        'active_page': 'todo'
    }))


class EntryReminder(webapp2.RequestHandler):
  def get(self):
    today = datetime.date.fromtimestamp(time.time())

    q = Entry.all().filter("date >", today - datetime.timedelta(days=1))
    msg = ""

    if q.count() <= 0:
      q = Entry.all().filter("date =", today - datetime.timedelta(days=30))
      old_entry = ""
      if q.count() > 0:
        old_entry = "\tEntry from 30 days ago\n%s\n\n" % q[0].content
      mail.send_mail(sender="%s <%s>" % (DIARY_NAME, DIARY_EMAIL),
              to="%s <%s>" % (RECIPIENT_NAME, RECIPIENT_EMAIL),
              subject="Entry reminder",
              body="""Don't forget to update your diary!

Just respond to this message with todays entry.

%s
-----
diaryentry%dtag
""" % (old_entry, int(time.time())))
      msg = "Reminder sent"
    else:
      msg = "I already have an entry for today"

    self.response.out.write(indexTemplate.render({
        'title': 'Ideas',
        'body': msg,
        'active_page': 'reminder'
      }))


class MailReceiver(InboundMailHandler):
  def strip_quote(self, body):
    return re.split(".*On.*(\\n)?wrote:", body)[0]

  def restore_newlines(self, body):
    clean = ""
    for line in body.split("\n"):
      clean += line
      if len(line) < 65:    # line break made by the user - keep it!
        clean += "\n"
      else:                 # add space to replace old newline
        clean += " "
    return clean.strip(' \t\n\r')

  def receive(self, message):
    logging.info("Received a message from: " + message.sender)

    if DIARY_EMAIL in message.to:
      self.handle_entry(message)
    elif TODO_EMAIL in message.to:
      self.handle_todo(message)
    else:
      logging.error("unknown receiver: %s", message.to)

  def get_content(self, message):
    for content_type, body in message.bodies("text/plain"):
      return (body.decode(), self.restore_newlines(
        self.strip_quote(body.decode())))

    return None

  def handle_todo(self, message):
    todo = ToDo(author='Julian')
    raw, todo.content = self.get_content(message)

    if todo.content is None:
      logging.error("Failed to find message body")
      logging.error(message)
      return

    todo.put()

  def handle_entry(self, message):

    entry = Entry(author='Julian')
    raw, entry.content = self.get_content(message)

    if entry.content is None:
      logging.error("Failed to find message body")
      logging.error(message)
      return

    matches = re.search("diaryentry(\d+)", raw)
    if matches is None:
      logging.error("received mail that wasn't a diary entry")
      logging.error(raw)
      return

    entry.date = datetime.date.fromtimestamp(int(matches.group(1)))
    entry.put()

    # fall back to raw mail message for attachment parsing
    for part in message.original.walk():
      content_type = part.get_content_type()
      if content_type not in ["text/plain", "text/html", "multipart/mixed",
        "multipart/alternative"]:
        attachment = Attachment(name=part.get_param("name"),
          content_type=content_type)

        # store attachment in blobstore
        blob = files.blobstore.create(mime_type='application/octet-stream')

        with files.open(blob, 'a') as f:
          f.write(base64.b64decode(part.get_payload()))

        files.finalize(blob)
        attachment.content = files.blobstore.get_blob_key(blob)
        attachment.entry = entry.key()
        attachment.thumbnail = images.get_serving_url(attachment.content,
          size=400)

        attachment.put()


app = webapp2.WSGIApplication([
  ('/', MainPage),
  MailReceiver.mapping(),
  ('/reminder', EntryReminder),
  ('/attachments', ShowAttachments),
  ('/attachment/([^/]+)', ServeAttachment),
  ('/ideas', ShowIdeas),
  ('/todo', ShowToDo),
  ('/append/([^/]+)', EntryAppendForm),
  ('/append', EntryAppendSubmit),
  ('/backup/entries', BackupEntries),
  ('/backup', HandleBackup),
  webapp2.Route('/_ah/admin', webapp2.RedirectHandler, defaults={
    '_uri': 'https://appengine.google.com/dashboard?app_id=s~infinite-diary'})
  ],
                              debug=True)
