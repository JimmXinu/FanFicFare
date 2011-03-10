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

class DownloadMeta(db.Model):
	user = db.UserProperty()
	url = db.StringProperty()
	name = db.StringProperty()
	title = db.StringProperty()
	author = db.StringProperty()
	format = db.StringProperty()
	failure = db.StringProperty()
	completed =  db.BooleanProperty(default=False)
	date = db.DateTimeProperty(auto_now_add=True)
	# data_chunks is implicit from DownloadData def.

class DownloadData(db.Model):
	download = db.ReferenceProperty(DownloadMeta,
					collection_name='data_chunks')
	blob = db.BlobProperty()
	index = db.IntegerProperty()
