#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
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

import logging
logging.getLogger().setLevel(logging.DEBUG)

import os
from os.path import dirname, basename, normpath
import sys
import zlib
import urllib

import traceback
import StringIO

from google.appengine.runtime import DeadlineExceededError

from google.appengine.api import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from fanficdownloader.downloader import *
from fanficdownloader.ffnet import *
from fanficdownloader.output import *
from fanficdownloader import twilighted
from fanficdownloader import adastrafanfic

from google.appengine.ext import db

from fanficdownloader.zipdir import *

from ffstorage import *

from fanficdownloader import adapters, writers, exceptions
import ConfigParser

class MainHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            error = self.request.get('error')
            template_values = {'nickname' : user.nickname(), 'authorized': True}
            url = self.request.get('url')
            template_values['url'] = url
            
            if error:
                if error == 'login_required':
                    template_values['error_message'] = 'This story (or one of the chapters) requires you to be logged in.'
                elif error == 'bad_url':
                    template_values['error_message'] = 'Unsupported URL: ' + url
                elif error == 'custom':
                    template_values['error_message'] = 'Error happened: ' + self.request.get('errtext')
                elif error == 'configsaved':
                    template_values['error_message'] = 'Configuration Saved'
            
            filename = self.request.get('file')
            if len(filename) > 1:
                template_values['yourfile'] = '''<div id='yourfile'><a href='/file?id=%s'>"%s" by %s</a></div>''' % (filename, self.request.get('name'), self.request.get('author'))
            
            self.response.headers['Content-Type'] = 'text/html'
            path = os.path.join(os.path.dirname(__file__), 'index.html')

            self.response.out.write(template.render(path, template_values))
        else:
            logging.debug(users.create_login_url('/'))
            url = users.create_login_url(self.request.uri)
            template_values = {'login_url' : url, 'authorized': False}
            path = os.path.join(os.path.dirname(__file__), 'index.html')
            self.response.out.write(template.render(path, template_values))


class EditConfigServer(webapp.RequestHandler):
    def get(self):
        self.post()

    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        template_values = {'nickname' : user.nickname(), 'authorized': True}

        ## Pull user's config record.
        l = UserConfig.all().filter('user =', user).fetch(1)
        if l:
            uconfig=l[0]
        else:
            uconfig=None

        if self.request.get('update'):
            if uconfig is None:
                uconfig = UserConfig()
            uconfig.user = user
            uconfig.config = self.request.get('config').encode('utf8')[:10000] ## just in case.
            uconfig.put()
            self.redirect("/?error=configsaved")
        else: # not update, assume display for edit
            if uconfig is not None and uconfig.config:
                config = uconfig.config
            else:
                configfile = open("example.ini","rb")
                config = configfile.read()
                configfile.close()
            template_values['config'] = config

            configfile = open("defaults.ini","rb")
            config = configfile.read()
            configfile.close()
            template_values['defaultsini'] = config
            
            path = os.path.join(os.path.dirname(__file__), 'editconfig.html')
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))

        
class FileServer(webapp.RequestHandler):

    def get(self):
        fileId = self.request.get('id')
        
        if fileId == None or len(fileId) < 3:
            self.redirect('/')
            return
        
        key = db.Key(fileId)
        fanfic = db.get(key)

        # check for completed & failure.
        
        name = fanfic.name.encode('utf-8')
        
        #name = urllib.quote(name)
        
        logging.info("Serving file: %s" % name)

        if name.endswith('.epub'):
            self.response.headers['Content-Type'] = 'application/epub+zip'
        elif name.endswith('.html'):
            self.response.headers['Content-Type'] = 'text/html'
        elif name.endswith('.txt'):
            self.response.headers['Content-Type'] = 'text/plain'
        elif name.endswith('.zip'):
            self.response.headers['Content-Type'] = 'application/zip'
        else:
            self.response.headers['Content-Type'] = 'application/octet-stream'
            
        self.response.headers['Content-disposition'] = 'attachment; filename="%s"' % name 

        data = DownloadData.all().filter("download =", fanfic).order("index")
        # epubs are all already compressed.
        # Each chunk is compress individually to avoid having
        # to hold the whole in memory just for the
        # compress/uncompress
        if fanfic.format != 'epub':
            def dc(data):
                try:
                    return zlib.decompress(data)
                # if error, assume it's a chunk from before we started compessing.
                except zlib.error:
                    return data
        else:
            def dc(data):
                return data
                
        for datum in data:
            self.response.out.write(dc(datum.blob))

class FileStatusServer(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        fileId = self.request.get('id')
        
        if fileId == None or len(fileId) < 3:
            self.redirect('/')
        
        key = db.Key(fileId)
        fic = db.get(key)

        logging.info("Status url: %s" % fic.url)
        if fic.completed and fic.format=='epub':
            escaped_url = urlEscape(self.request.host_url+"/file/"+fic.name+"."+fic.format+"?id="+fileId+"&fake=file."+fic.format)
        else:
            escaped_url=False
        template_values = dict(fic = fic,
                       nickname = user.nickname(),
                       escaped_url = escaped_url
                       )
        path = os.path.join(os.path.dirname(__file__), 'status.html')
        self.response.out.write(template.render(path, template_values))
        
class RecentFilesServer(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        q = DownloadMeta.all()
        q.filter('user =', user).order('-date')
        fics = q.fetch(100)

        for fic in fics:
            if fic.completed and fic.format == 'epub':
                fic.escaped_url = urlEscape(self.request.host_url+"/file/"+fic.name+"."+fic.format+"?id="+str(fic.key())+"&fake=file."+fic.format)
        
        template_values = dict(fics = fics, nickname = user.nickname())
        path = os.path.join(os.path.dirname(__file__), 'recent.html')
        self.response.out.write(template.render(path, template_values))

class UserConfigServer(webapp.RequestHandler):
    def getUserConfig(self,user):
        config = ConfigParser.SafeConfigParser()

        logging.debug('reading defaults.ini config file')
        config.read('defaults.ini')
        
        ## Pull user's config record.
        l = UserConfig.all().filter('user =', user).fetch(1)
        ## TEST THIS
        if l and l[0].config:
            uconfig=l[0]
            #logging.debug('reading config from UserConfig(%s)'%uconfig.config)
            config.readfp(StringIO.StringIO(uconfig.config))                

        return config
        
class FanfictionDownloader(UserConfigServer):
    def get(self):
        self.post()

    def post(self):
        logging.getLogger().setLevel(logging.DEBUG)
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return
        
        format = self.request.get('format')
        url = self.request.get('url')
        login = self.request.get('login')
        password = self.request.get('password')
        is_adult = self.request.get('is_adult') == "on"
        
        logging.info("Queuing Download: " + url)

        # use existing record if available.
        q = DownloadMeta.all().filter('user =', user).filter('url =',url).filter('format =',format).fetch(1)
        if( q is None or len(q) < 1 ):
            download = DownloadMeta()
        else:
            download = q[0]
            download.completed=False
            download.failure=None
            for c in download.data_chunks:
                c.delete()
                
        download.user = user
        download.url = url
        download.format = format

        adapter = None
        try:
            config = self.getUserConfig(user)
            adapter = adapters.getAdapter(config,url)
            logging.info('Created an adaper: %s' % adapter)
        
            if len(login) > 1:
                adapter.username=login
                adapter.password=password
            adapter.is_adult=is_adult
            ## This scrapes the metadata, which will be
            ## duplicated in the queue task, but it
            ## detects bad URLs, bad login, bad story, etc
            ## without waiting for the queue.  So I think
            ## it's worth the double up.  Could maybe save
            ## it all in the download object someday.
            story = adapter.getStoryMetadataOnly()
            download.title = story.getMetadata('title')
            download.author = story.getMetadata('author')
            download.put()

            taskqueue.add(url='/fdowntask',
                      queue_name="download",
                      params={'format':format,
                              'url':url,
                              'login':login,
                              'password':password,
                              'user':user.email(),
                              'is_adult':is_adult})
        
            logging.info("enqueued download key: " + str(download.key()))

        except (exceptions.FailedToLogin,exceptions.AdultCheckRequired), e:
            logging.exception(e)
            download.failure = str(e)
            download.put()
            logging.debug('Need to Login, display log in page')
            is_login= ( isinstance(e, exceptions.FailedToLogin) )
            template_values = dict(nickname = user.nickname(),
                                   url = url,
                                   format = format,
                                   site = adapter.getSiteDomain(),
                                   fic = download,
                                   is_login=is_login,
                                   )
            # thewriterscoffeeshop.com can do adult check *and* user required.
            if isinstance(e,exceptions.AdultCheckRequired):
                template_values['login']=login
                template_values['password']=password
                
            path = os.path.join(os.path.dirname(__file__), 'login.html')
            self.response.out.write(template.render(path, template_values))
            return
        except Exception, e:
            logging.exception(e)
            download.failure = str(e)
            download.put()
        
        self.redirect('/status?id='+str(download.key()))

        return


class FanfictionDownloaderTask(UserConfigServer):
    def _printableVersion(self, text):
        text = removeEntities(text)
        try:
            d = text.decode('utf-8')
        except:
            d = text
        return d
    

    def post(self):
        logging.getLogger().setLevel(logging.DEBUG)
        format = self.request.get('format')
        url = self.request.get('url')
        login = self.request.get('login')
        password = self.request.get('password')
        is_adult = self.request.get('is_adult')
        # User object can't pass, just email address
        user = users.User(self.request.get('user'))
        
        logging.info("Downloading: " + url + " for user: "+user.nickname())
        
        adapter = None
        writerClass = None

        # use existing record if available.
        q = DownloadMeta.all().filter('user =', user).filter('url =',url).filter('format =',format).fetch(1)
        if( q is None or len(q) < 1 ):
            download = DownloadMeta()
        else:
            download = q[0]
            download.completed=False
            for c in download.data_chunks:
                c.delete()
                
        download.user = user
        download.url = url
        download.format = format
        download.put()
        logging.info('Creating adapter...')
        
        try:
            config = self.getUserConfig(user)
            adapter = adapters.getAdapter(config,url)
        except Exception, e:
            logging.exception(e)
            download.failure = str(e)
            download.put()
            return
        
        logging.info('Created an adapter: %s' % adapter)
        
        if len(login) > 1:
            adapter.username=login
            adapter.password=password
        adapter.is_adult=is_adult

        try:
            # adapter.getStory() is what does all the heavy lifting.
            writer = writers.getWriter(format,config,adapter.getStory())
        except Exception, e:
            logging.exception(e)
            download.failure = str(e)
            download.put()
            return
        
        download.name = writer.getOutputFileName()
        download.title = adapter.getStory().getMetadata('title')
        download.author = adapter.getStory().getMetadata('author')
        download.put()
        index=0

        outbuffer = StringIO.StringIO()
        writer.writeStory(outbuffer)
        data = outbuffer.getvalue()
        outbuffer.close()
        del writer
        del adapter

        # epubs are all already compressed.
        # Each chunk is compressed individually to avoid having
        # to hold the whole in memory just for the
        # compress/uncompress.
        if format != 'epub':
            def c(data):
                return zlib.compress(data)
        else:
            def c(data):
                return data
            
        while( len(data) > 0 ):
            DownloadData(download=download,
                     index=index,
                     blob=c(data[:1000000])).put()
            index += 1
            data = data[1000000:]
        download.completed=True
        download.put()
            
        logging.info("Download finished OK")
        return
                
def toPercentDecimal(match): 
    "Return the %decimal number for the character for url escaping"
    s = match.group(1)
    return "%%%02x" % ord(s)

def urlEscape(data):
    "Escape text, including unicode, for use in URLs"
    p = re.compile(r'([^\w])')
    return p.sub(toPercentDecimal, data.encode("utf-8"))

def main():
  application = webapp.WSGIApplication([('/', MainHandler),
                                        ('/fdowntask', FanfictionDownloaderTask),
                                        ('/fdown', FanfictionDownloader),
                                        (r'/file.*', FileServer),
                                        ('/status', FileStatusServer),
                                        ('/recent', RecentFilesServer),
                                        ('/editconfig', EditConfigServer),
                                        ],
                                       debug=False)
  util.run_wsgi_app(application)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main()
