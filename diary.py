import webapp2
import jinja2
import os
import re
import logging
import base64
import time
import datetime
from google.appengine.ext import db, blobstore
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import files, images, mail
from google.appengine.ext.webapp import blobstore_handlers

from pytz.gae import pytz

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

indexTemplate = jinja_environment.get_template('templates/index.html')
entryTemplate = jinja_environment.get_template('templates/entry.html')
attachmentTemplate = jinja_environment.get_template(
  'templates/attachment.html')

local_tz = pytz.timezone('Europe/Vienna')
dummy_var = "dumm"


class Entry(db.Model):
  author = db.StringProperty()
  content = db.TextProperty()
  date = db.DateProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)


class Attachment(db.Model):
  name = db.StringProperty()
  thumbnail = db.StringProperty()
  content_type = db.StringProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)
  content = blobstore.BlobReferenceProperty()
  entry = db.ReferenceProperty(reference_class=Entry)


class MainPage(webapp2.RequestHandler):
  def markup_text(self, text):
    def add_a_tag(match):
      return "<a href='%s'>%s</a>" % (match.group(0), match.group(0))
    text = re.sub("https?://([0-9a-zA-Z-]+)(\.[a-zA-Z0-9]+){1,6}[\S]*",
      add_a_tag, text)

    return text.replace("\n", "<br>\n")

  def get(self):
      self.response.headers['Content-Type'] = 'text/html'

      body = ""

      for e in Entry.all().order('-date'):
        attachments = ""
        for a in Attachment.all().filter("entry =", e.key()):
          attachments += attachmentTemplate.render({
            'name': a.name,
            'thumbnail': a.thumbnail,
            'key': a.key()
            })
        body += entryTemplate.render({
          'entry_day': e.date.strftime("%A, %d %B"),
          'content': self.markup_text(e.content),
          'creation_time': pytz.utc.localize(e.creation_time).astimezone(
            local_tz).strftime("%A, %d %B - %H:%M"),
          'attachments': attachments
          })

      self.response.out.write(indexTemplate.render({
        'title': 'Home',
        'body': body
      }))


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


class EntryReminder(webapp2.RequestHandler):
  def get(self):
    today = datetime.date.fromtimestamp(time.time())

    q = Entry.all().filter("date >", today - datetime.timedelta(days=1))
    msg = ""

    if q.count() <= 0:
      mail.send_mail(sender="Infinite Diary <diary@furidamu.org>",
              to="Julian Schrittwieser <j.schrittwieser@gmail.com>",
              subject="Entry reminder",
              body="""Don't forget to update your diary!

Just respond to this message with todays entry.


-----
diaryentry%dtag
""" % int(time.time()))
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
    raw = ""

    entry = Entry(author='Julian')
    for content_type, body in message.bodies("text/plain"):
      raw = body.decode()
      entry.content = self.restore_newlines(
        self.strip_quote(raw))

    if raw == "":
      logging.error("Failed to find message body")
      logging.error(message)
      return

    matches = re.search("diaryentry(\d+)", raw)
    if matches == None:
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
  webapp2.Route('/_ah/admin', webapp2.RedirectHandler, defaults={
    '_uri': 'https://appengine.google.com/dashboard?app_id=s~infinite-diary'})
  ],
                              debug=True)
