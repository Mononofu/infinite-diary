import webapp2
import datetime
import time
import base64
import logging
import re

from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api import files, mail, images

from models import Entry, ToDo, Attachment
from config import (DIARY_EMAIL, DIARY_NAME, RECIPIENT_NAME, RECIPIENT_EMAIL,
    TODO_EMAIL)
from templates import indexTemplate

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

      q = Entry.all().filter("date =", today - datetime.timedelta(days=180))
      if q.count() > 0:
        old_entry += "\tEntry from 180 days ago\n%s\n\n" % q[0].content

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
    body = body.replace("\r", "")
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
      logging.error("unknown receiver: %s\n%s", message.to, message.original)

  def get_content(self, message):
    for content_type, body in message.bodies("text/plain"):
      return (body.decode(), self.restore_newlines(
        self.strip_quote(body.decode())))

    return None

  def handle_todo(self, message):
    raw, content = self.get_content(message)

    for todo_text in [s.lstrip(" -").strip() for s in content.split("\n")]:
      todo = ToDo(author='Julian', category=message.subject.lower(),
          content=todo_text)
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
