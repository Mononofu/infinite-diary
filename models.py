from google.appengine.ext import db
from google.appengine.ext import blobstore

import datetime

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


class ToDo(db.Model):
  author = db.StringProperty()
  content = db.TextProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)


class Attachment(db.Model):
  name = db.StringProperty()
  thumbnail = db.StringProperty()
  content_type = db.StringProperty()
  creation_time = db.DateTimeProperty(auto_now_add=True)
  content = blobstore.BlobReferenceProperty()
  entry = db.ReferenceProperty(reference_class=Entry)
