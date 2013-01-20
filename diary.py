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


jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

indexTemplate = jinja_environment.get_template('templates/index.html')
entryTemplate = jinja_environment.get_template('templates/entry.html')
attachmentTemplate = jinja_environment.get_template('templates/attachment.html')


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
  def get(self):
      self.response.headers['Content-Type'] = 'text/html'

      body = ""

      for e in Entry.all():
        attachments = ""
        for a in Attachment.all().filter("entry =", e.key()):
          attachments += attachmentTemplate.render({
            'name': a.name,
            'thumbnail': a.thumbnail,
            'key': a.content
            })
        body += entryTemplate.render({
          'entry_day': e.date.strftime("%A, %d %B"),
          'content': e.content.replace("\n", "<br>\n"),
          'creation_time': e.creation_time.strftime("%A, %d %B - %H:%M"),
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
            'key': a.content
            })
    self.response.out.write(indexTemplate.render({
        'title': 'Attachments',
        'body': attachments
      }))


class EntryReminder(webapp2.RequestHandler):
  def get(self):
    today = datetime.date.fromtimestamp(time.time())

    q = Entry.all().filter("date >", today - datetime.timedelta(days=1))

    if q.count() <= 0:
      mail.send_mail(sender="Infinite Diary <diary@furidamu.org>",
              to="Julian Schrittwieser <j.schrittwieser@gmail.com>",
              subject="Entry reminder",
              body="""Don't forget to update your diary!

Just respond to this message with todays entry.


-----
diaryentry%dtag
""" % int(time.time()))
      self.response.write("Reminder sent")
    else:
      self.response.write("I already have an entry for today")


class MailReceiver(InboundMailHandler):
  def strip_quote(self, body):
    return re.split(".*On.*(\\n)?wrote:", body)[0]

  def receive(self, message):
    logging.info("Received a message from: " + message.sender)

    entry = Entry(author='Julian')
    for content_type, body in message.bodies("text/plain"):
      entry.content = self.strip_quote(body.decode())
      logging.debug(entry.content)

    matches = re.search("diaryentry(\d+)", entry.content)
    if matches == None:
      logging.error("received mail that wasn't a diary entry")
      logging.error(entry.content)
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
        attachment.thumbnail = images.get_serving_url(attachment.content, size=400)

        attachment.put()


app = webapp2.WSGIApplication([
  ('/', MainPage),
  MailReceiver.mapping(),
  ('/reminder', EntryReminder),
  ('/attachments', ShowAttachments)],
                              debug=True)
