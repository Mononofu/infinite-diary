import webapp2

from google.appengine.api import mail

from config import (DIARY_EMAIL, DIARY_NAME, RECIPIENT_NAME, RECIPIENT_EMAIL)
from templates import indexTemplate


class CheckHappyness(webapp2.RequestHandler):
  def get(self):
    mail.send_mail(sender="%s <%s>" % (DIARY_NAME, DIARY_EMAIL),
                   to="%s <%s>" % (RECIPIENT_NAME, RECIPIENT_EMAIL),
                   subject="Happyness Check",
                   body="")

    self.response.out.write(indexTemplate.render({
        'title': 'Happyness',
        'body': 'Reminder sent',
        'active_page': 'happyness'
      }))
