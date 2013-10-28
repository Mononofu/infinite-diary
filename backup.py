import webapp2
import json

from models import Entry, ToDo
from templates import indexTemplate, backupTemplate
from config import BACKUP_KEY

def enforce_key(self):
  if self.request.get("key") != BACKUP_KEY:
    self.redirect('/')

class ListModels(webapp2.RequestHandler):
  def get(self):
    enforce_key(self)
    self.response.out.write(json.dumps(['entries', 'todos']))

class HandleBackup(webapp2.RequestHandler):
  def post(self):
    enforce_key(self)
    rawEntries = self.request.get("entries")
    entries = json.loads(rawEntries)
    for e in entries:
      newEntry = Entry()
      newEntry.from_json(e)
      newEntry.put()

    rawTodos = self.request.get("todos")
    todos = json.loads(rawTodos)
    for t in todos:
      newToDo = ToDo()
      newToDo.from_json(t)
      newToDo.put()

    self.redirect("/backup")


class BackupEntries(webapp2.RequestHandler):
  def get(self):
    enforce_key(self)
    entries = [e.to_dict() for e in Entry.all().order('-date')]
    self.response.headers['Content-Type'] = "application/json"
    self.response.headers['Content-Disposition'] = (
        "attachment; filename=entries.json")
    self.response.out.write(json.dumps(entries))

class BackupToDos(webapp2.RequestHandler):
  def get(self):
    enforce_key(self)
    todos = [t.to_dict() for t in ToDo.all().order('-creation_time')]
    self.response.headers['Content-Type'] = "application/json"
    self.response.headers['Content-Disposition'] = (
        "attachment; filename=todos.json")
    self.response.out.write(json.dumps(todos))

app = webapp2.WSGIApplication([
  ('/backup/entries', BackupEntries),
  ('/backup/todos', BackupToDos),
  ('/backup/restore', HandleBackup),
  ('/backup/list', ListModels)],
                              debug=True)
