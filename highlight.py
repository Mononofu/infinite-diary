import webapp2
from datetime import date, timedelta

from models import Entry, Highlight
from templates import indexTemplate, entryTemplate

def next_month(month):
  month += timedelta(days=40)
  return date(month.year, month.month, 1)

class ShowHighlights(webapp2.RequestHandler):
  def get(self):
    out = ""
    first_entry = Entry.all().order('date').get().date

    month = date(first_entry.year, first_entry.month, 1)
    while month < date.today():
      h = Highlight.all().filter("date =", month).filter("period =", "month").get()

      if h:
        pass
      else:
        out += "<a href='/highlights/month/%d'><h2>%s</h2></a>" % (
          month.toordinal(), month.strftime("%B %Y"))
      month = next_month(month)

    self.response.out.write(indexTemplate.render({
      'title': 'Highlights',
      'body': out,
      'active_page': 'highlights'
    }))

class PickMonthlyHighlight(webapp2.RequestHandler):
  def get(self, ordinal):
    out = ""
    month = date.fromordinal(int(ordinal))
    for e in Entry.all().filter("date >=", month).filter("date <", next_month(month)):
      out += "<br><a href='/highlights/month/%s/pick/%s'>Pick below entry:</a>%s" % (
        ordinal, e.key(), e.render())

    self.response.out.write(indexTemplate.render({
      'title': 'Highlights - Monthly',
      'body': out,
      'active_page': 'highlights'
    }))
