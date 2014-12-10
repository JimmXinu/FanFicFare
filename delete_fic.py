import os
import cgi
import sys
import logging
import traceback
import StringIO

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from fanficdownloader.downaloder import *
from fanficdownloader.ffnet import *
from fanficdownloader.output import *

from google.appengine.ext import db

from fanficdownloader.zipdir import *

from ffstorage import *

def create_mac(user, fic_id, fic_url):
  return str(abs(hash(user)+hash(fic_id)))+str(abs(hash(fic_url)))
  
def check_mac(user, fic_id, fic_url, mac):
  return (create_mac(user, fic_id, fic_url) == mac)

def create_mac_for_fic(user, fic_id):
  key = db.Key(fic_id)
	fanfic = db.get(key)
	if fanfic.user != user:
	  return None
	else:
	  return create_mac(user, key, fanfic.url)

class DeleteFicHandler(webapp.RequestHandler):
	def get(self):
		user = users.get_current_user()
		if not user:
			self.redirect('/login')

    fic_id = self.request.get('fic_id')
    fic_mac = self.request.get('key_id')
    
    actual_mac = create_mac_for_fic(user, fic_id)
    if actual_mac != fic_mac:
      self.response.out.write("Ooops")
    else:
      key = db.Key(fic_id)
    	fanfic = db.get(key)
      fanfic.delete()
      self.redirect('/recent')
    

		fics = db.GqlQuery("Select * From DownloadedFanfic WHERE user = :1", user)
		template_values = dict(fics = fics, nickname = user.nickname())
		path = os.path.join(os.path.dirname(__file__), 'recent.html')
		self.response.out.write(template.render(path, template_values))
	