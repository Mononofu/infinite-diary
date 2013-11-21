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
        out += "<h2>%s</h2>\n" % month.strftime("%B %Y")
        out += h.entry.render()
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
      out += """%s
<form action='/highlights/month/%s' method='POST'>
  <input type='hidden' name='key' value='%s'>
  <input type='submit' value='Pick'>
</form><br><br>""" % (e.render(), ordinal, e.key())

    self.response.out.write(indexTemplate.render({
      'title': 'Highlights - Monthly',
      'body': out,
      'active_page': 'highlights'
    }))

  def post(self, ordinal):
    e = Entry.get(self.request.get('key'))
    h = Highlight(period='month', entry=e, date=date.fromordinal(int(ordinal)))
    h.put()
    self.redirect('/highlights')
