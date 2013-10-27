import webapp2
import json

from models import Entry
from templates import indexTemplate

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


class BackupEntries(webapp2.RequestHandler):
  def get(self):
    entries = [e.to_dict() for e in Entry.all().order('-date')]
    self.response.headers['Content-Type'] = "application/json"
    self.response.headers['Content-Disposition'] = (
        "attachment; filename=entries.json")
    self.response.out.write(json.dumps(entries))
