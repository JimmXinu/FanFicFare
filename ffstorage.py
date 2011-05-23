# Copyright 2011 Fanficdownloader team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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
	config = db.BlobProperty()
