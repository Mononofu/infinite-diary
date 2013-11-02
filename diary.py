import webapp2
import re
import datetime
from pytz.gae import pytz
from collections import defaultdict

from google.appengine.ext.webapp import blobstore_handlers

from models import Entry, Attachment, ToDo
from templates import (attachmentTemplate, entryTemplate, indexTemplate,
    entryAppendTemplate, backupTemplate)
from mail import EntryReminder, MailReceiver
from config import BACKUP_KEY

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
    todos = defaultdict(list)
    for t in ToDo.all().filter('done_time =', None).order('-creation_time'):
      todos[t.category].append(t)
    for t in ToDo.all().filter('done_time >', datetime.datetime.now() -
                               datetime.timedelta(days=7)):
      todos[t.category].append(t)

    body_text = ""
    for category, items in todos.iteritems():
      body_text += "<h2>%s</h2>\n<ul class='todo'>" % category
      for t in items:
        if t.done_time:
          body_text += "\t<li class='done'>%s</li>\n" % t.content
        else:
          body_text += "\t<a href='/todo/finish/%s'><li>%s</li></a>\n" % (
            t.key(), t.content)
      body_text += "</ul>"

    self.response.out.write(indexTemplate.render({
        'title': 'To-Do',
        'body': body_text,
        'active_page': 'todo'
    }))

class FinishToDo(webapp2.RequestHandler):
  def get(self, key):
    t = ToDo.get(key)
    t.done_time = datetime.datetime.now()
    t.put()
    self.redirect('/todo?refresh')

class ShowBackup(webapp2.RequestHandler):
  def get(self):
    self.response.out.write(indexTemplate.render({
      'title': 'Backup',
      'body': backupTemplate.render({'key': BACKUP_KEY}),
      'active_page': 'backup'
    }))

app = webapp2.WSGIApplication([
  ('/', MainPage),
  MailReceiver.mapping(),
  ('/reminder', EntryReminder),
  ('/attachments', ShowAttachments),
  ('/attachment/([^/]+)', ServeAttachment),
  ('/ideas', ShowIdeas),
  ('/todo', ShowToDo),
  ('/todo/finish/([^/]+)', FinishToDo),
  ('/append/([^/]+)', EntryAppendForm),
  ('/append', EntryAppendSubmit),
  ('/backup', ShowBackup),
  webapp2.Route('/_ah/admin', webapp2.RedirectHandler, defaults={
    '_uri': 'https://appengine.google.com/dashboard?app_id=s~infinite-diary'})
  ],
                              debug=True)
