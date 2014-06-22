import random
import webapp2

from google.appengine.api import mail

from config import (DIARY_EMAIL, DIARY_NAME, RECIPIENT_NAME, RECIPIENT_EMAIL)
from templates import indexTemplate


class CheckHappiness(webapp2.RequestHandler):
  def get(self):
    frequency = 1.0
    if self.request.get('frequency') != '':
      frequency = float(self.request.get('frequency'))

    result = 'no action'
    if random.random() < frequency:
      mail.send_mail(sender='%s <%s>' % (DIARY_NAME, DIARY_EMAIL),
                     to='%s <%s>' % (RECIPIENT_NAME, RECIPIENT_EMAIL),
                     subject='Happiness Check',
                     body='')
      result = 'happiness check sent'

    self.response.out.write(indexTemplate.render({
        'title': 'Happyness',
        'body': result,
        'active_page': 'happiness'
      }))
