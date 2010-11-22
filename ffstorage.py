from google.appengine.ext import db

class OneDownload(db.Model):
	user = db.UserProperty()
	url = db.StringProperty()
	format = db.StringProperty()
	login = db.StringProperty()
	password = db.StringProperty()
	failure = db.StringProperty()
	date = db.DateTimeProperty(auto_now_add=True)
	
class DownloadedFanfic(db.Model):
	user = db.UserProperty()
	url = db.StringProperty()
	name = db.StringProperty()
	author = db.StringProperty()
	format = db.StringProperty()
	date = db.DateTimeProperty(auto_now_add=True)
	blob = db.BlobProperty()
	mac = db.StringProperty()
	cleared = db.BooleanProperty(default=False)