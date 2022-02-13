from google.appengine.ext import db
from google.appengine.ext import blobstore
from pytz.gae import pytz

import datetime
import re

from templates import entryTemplate, attachmentTemplate

local_tz = pytz.timezone('Europe/London')


def markup_text(text):
  def add_a_tag(match):
    return "<a href='%s'>%s</a>" % (match.group(0), match.group(0))
  text = re.sub("https?://([0-9a-zA-Z-]+)(\.[a-zA-Z0-9]+){1,6}[\S]*",
                add_a_tag, text)

  return text.replace("\n", "<br>\n")


class Entry(db.Model):
  author = db.StringProperty()
  content = db.TextProperty()
  date = db.DateProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)

  def to_dict(self):
    return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

  def from_json(self, json):
    self.author = json['author']
    self.content = json['content']
    self.date = datetime.datetime.strptime(json['date'], '%Y-%m-%d').date()
    self.creation_time = datetime.datetime.strptime(json['creation_time'],
                                                    '%Y-%m-%d %H:%M:%S.%f')

  def render(self):
    attachments = ""
    for a in Attachment.all().filter("entry =", self.key()):
      attachments += attachmentTemplate.render({
        'name': a.name,
        'thumbnail': a.thumbnail,
        'key': a.key()
      })
    return entryTemplate.render({
      'entry_day': self.date.strftime("%A, %d %B"),
      'content': markup_text(self.content),
      'creation_time': pytz.utc.localize(self.creation_time).astimezone(
          local_tz).strftime("%A, %d %B - %H:%M"),
      'attachments': attachments,
      'key': self.key()
    })


class ToDo(db.Model):
  author = db.StringProperty()
  content = db.TextProperty()
  category = db.StringProperty()
  done_time = db.DateTimeProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)

  def to_dict(self):
    return dict([(p, unicode(getattr(self, p))) for p in self.properties()])

  def from_json(self, json):
    self.author = json['author']
    self.content = json['content']
    self.category = json['category']
    self.creation_time = datetime.datetime.strptime(json['creation_time'],
                                                    '%Y-%m-%d %H:%M:%S.%f')
    if json['done_time'] != 'None':
      self.done_time = datetime.datetime.strptime(json['done_time'],
                                                  '%Y-%m-%d %H:%M:%S.%f')


class Attachment(db.Model):
  name = db.StringProperty()
  thumbnail = db.StringProperty()
  content_type = db.StringProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)
  content = blobstore.BlobReferenceProperty()
  entry = db.ReferenceProperty(reference_class=Entry)


class Highlight(db.Model):
  period = db.StringProperty(choices=['week', 'month', 'year'])
  entry = db.ReferenceProperty(reference_class=Entry)
  date = db.DateProperty()


class Status(db.Model):
  date = db.DateTimeProperty(auto_now_add=True)
  happyness = db.IntegerProperty()
  tags = db.StringListProperty()
