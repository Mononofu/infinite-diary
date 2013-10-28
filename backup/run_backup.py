import requests
import datetime

SITE = "http://localhost:8888"
BACKUP_KEY = 'Cev2pDLLAOiO5YMsrgmWaMytysXDmy'

s = requests.session()
params = {
  'key': BACKUP_KEY
}

list_of_models = s.get("%s/backup/list" % SITE, params=params).json()
print list_of_models

backup_time = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M")

for model in list_of_models:
  backup = s.get("%s/backup/%s" % (SITE, model), params=params).text
  with open('%s-%s.backup' % (backup_time, model), 'w') as f:
    f.write(backup)
