import requests
import datetime
import sys
import os
from config import BACKUP_KEY

site = "http://diary.furidamu.org"

def usage():
  print "Usage: %s backup|restore [site]" % sys.argv[0]
  sys.exit(1)

if len(sys.argv) < 2 or len(sys.argv) > 3:
  usage()

if len(sys.argv) == 3:
  site = sys.argv[2]

s = requests.session()
params = {
  'key': BACKUP_KEY
}

if sys.argv[1] == 'backup':
  list_of_models = s.get("%s/backup/list" % site, params=params).json()
  print list_of_models

  backup_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")

  for model in list_of_models:
    print model
    backup = s.get("%s/backup/%s" % (site, model), params=params).text
    with open('backup/%s-%s.backup' % (backup_time, model), 'w') as f:
      f.write(backup)

elif sys.argv[1] == 'restore':
  files = os.listdir('backup/')
  files.sort()
  newest_backup = "-".join(files[0].split("-")[:3])
  backup_files = [f for f in files if newest_backup in f]
  print backup_files

  list_of_models = s.get("%s/backup/list" % site, params=params).json()
  print list_of_models

  def get_backup(model):
    return 'backup/' + ([b for b in backup_files if model in b][0])

  files = dict([(model, open(get_backup(model))) for model in list_of_models])
  files['key'] = BACKUP_KEY
  print files
  print requests.post("%s/backup/restore" % site, files=files).text

else:
  usage()
