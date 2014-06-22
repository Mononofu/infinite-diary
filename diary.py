import webapp2
import datetime
from collections import defaultdict

from google.appengine.ext.webapp import blobstore_handlers

from models import Entry, Attachment, ToDo
from templates import (attachmentTemplate, indexTemplate,
                       entryEditTemplate, backupTemplate)
from mail import EntryReminder, MailReceiver
from highlight import ShowHighlights, PickMonthlyHighlight
from config import BACKUP_KEY
from happiness import CheckHappiness


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
      body += e.render()
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


class EntryEditForm(webapp2.RequestHandler):
  def get(self, key):
    e = Entry.get(key)
    body = entryEditTemplate.render({
      'entry_day': e.date.strftime("%A, %d %B"),
      'content': e.content,
      'key': e.key()
    })

    self.response.out.write(indexTemplate.render({
      'title': 'Append to Entry',
      'body': body
    }))


class EntryEditSubmit(webapp2.RequestHandler):
  def post(self):
    key = self.request.get('key')
    try:
      e = Entry.get(key)
      e.content = self.request.get('content')
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
  ('/happiness/check', CheckHappiness),
  ('/attachments', ShowAttachments),
  ('/attachment/([^/]+)', ServeAttachment),
  ('/ideas', ShowIdeas),
  ('/todo', ShowToDo),
  ('/todo/finish/([^/]+)', FinishToDo),
  ('/highlights', ShowHighlights),
  ('/highlights/month/(\d+)', PickMonthlyHighlight),
  ('/edit/([^/]+)', EntryEditForm),
  ('/edit', EntryEditSubmit),
  ('/backup', ShowBackup),
  webapp2.Route('/_ah/admin', webapp2.RedirectHandler, defaults={
    '_uri': 'https://appengine.google.com/dashboard?app_id=s~infinite-diary'})
  ],
                              debug=True)
