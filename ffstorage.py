from google.appengine.ext import db

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

class UserConfig(db.Model):
	user = db.UserProperty()
	config = db.TextProperty()
