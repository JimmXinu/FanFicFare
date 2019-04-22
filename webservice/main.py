#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
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
import re
import sys
import zlib
import urllib
import datetime

import traceback
from io import StringIO

from google.appengine.ext import db
from google.appengine.api import taskqueue
from google.appengine.api import users
from google.appengine.api import mail
import webapp2
from google.appengine.ext.webapp import template
#from google.appengine.ext.webapp2 import util
from google.appengine.runtime import DeadlineExceededError

from ffstorage import *

from fanficfare import adapters, writers, exceptions
from fanficfare.htmlcleanup import stripHTML
from fanficfare.configurable import Configuration

class UserConfigServer(webapp2.RequestHandler):

    def getUserConfig(self,user,url,fileformat):

        configuration = Configuration(adapters.getConfigSectionsFor(url),fileformat)

        logging.debug('reading defaults.ini config file')
        configuration.read('fanficfare/defaults.ini')

        ## Pull user's config record.
        l = UserConfig.all().filter('user =', user).fetch(1)
        if l and l[0].config:
            uconfig=l[0]
            #logging.debug('reading config from UserConfig(%s)'%uconfig.config)
            configuration.readfp(StringIO(uconfig.config.decode('utf-8')))

        return configuration

class MainHandler(webapp2.RequestHandler):
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
                elif error == 'recentcleared':
                    template_values['error_message'] = 'Your Recent Downloads List has been Cleared'

            self.response.headers['Content-Type'] = 'text/html'
            path = os.path.join(os.path.dirname(__file__), 'index.html')

        else:
            logging.debug(users.create_login_url('/'))
            url = users.create_login_url(self.request.uri)
            template_values = {'login_url' : url, 'authorized': False}
            path = os.path.join(os.path.dirname(__file__), 'index.html')


        template_values['supported_sites'] = '<dl>\n'
        for (site,examples) in adapters.getSiteExamples():
            template_values['supported_sites'] += "<dt>%s</dt>\n<dd>Example Story URLs:<br>"%site
            for u in examples:
                template_values['supported_sites'] += "<a href='%s'>%s</a><br>\n"%(u,u)
            template_values['supported_sites'] += "</dd>\n"
        template_values['supported_sites'] += '</dl>\n'

        self.response.out.write(template.render(path, template_values))


class EditConfigServer(UserConfigServer):
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
            try:
                # just getting config for testing purposes.
                configuration = self.getUserConfig(user,"test1.com","epub")
                self.redirect("/?error=configsaved")
            except Exception as e:
                logging.info("Saved Config Failed:%s"%e)
                self.redirect("/?error=custom&errtext=%s"%urllib.quote(unicode(e),''))
        else: # not update, assume display for edit
            if uconfig is not None and uconfig.config:
                config = uconfig.config
            else:
                configfile = open("fanficfare/example.ini","rb")
                config = configfile.read()
                configfile.close()
            template_values['config'] = config

            configfile = open("fanficfare/defaults.ini","rb")
            config = configfile.read()
            configfile.close()
            template_values['defaultsini'] = config

            path = os.path.join(os.path.dirname(__file__), 'editconfig.html')
            self.response.headers['Content-Type'] = 'text/html'
            self.response.out.write(template.render(path, template_values))


class FileServer(webapp2.RequestHandler):

    def get(self):
        fileId = self.request.get('id')

        if fileId == None or len(fileId) < 3:
            self.redirect('/')
            return

        try:
            download = getDownloadMeta(id=fileId)

            name = download.name.encode('utf-8')

            logging.info("Serving file: %s" % name)

            if name.endswith('.epub'):
                self.response.headers['Content-Type'] = 'application/epub+zip'
            elif name.endswith('.html'):
                self.response.headers['Content-Type'] = 'text/html'
            elif name.endswith('.txt'):
                self.response.headers['Content-Type'] = 'text/plain'
            elif name.endswith('.mobi'):
                self.response.headers['Content-Type'] = 'application/x-mobipocket-ebook'
            elif name.endswith('.zip'):
                self.response.headers['Content-Type'] = 'application/zip'
            else:
                self.response.headers['Content-Type'] = 'application/octet-stream'

            self.response.headers['Content-disposition'] = 'attachment; filename="%s"' % name

            data = DownloadData.all().filter("download =", download).order("index")
            # epubs are all already compressed.
            # Each chunk is compress individually to avoid having
            # to hold the whole in memory just for the
            # compress/uncompress
            if download.format != 'epub':
                def decompress(data):
                    try:
                        return zlib.decompress(data)
                    # if error, assume it's a chunk from before we started compessing.
                    except zlib.error:
                        return data
            else:
                def decompress(data):
                    return data

            for datum in data:
                self.response.out.write(decompress(datum.blob))

        except Exception as e:
            fic = DownloadMeta()
            fic.failure = unicode(e)

            template_values = dict(fic = fic,
                                   #nickname = user.nickname(),
                                   #escaped_url = escaped_url
                                   )
            path = os.path.join(os.path.dirname(__file__), 'status.html')
            self.response.out.write(template.render(path, template_values))

class FileStatusServer(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        fileId = self.request.get('id')

        if fileId == None or len(fileId) < 3:
            self.redirect('/')

        escaped_url=False

        try:
            download = getDownloadMeta(id=fileId)

            if download:
                logging.info("Status url: %s" % download.url)
                if download.completed and download.format=='epub':
                    escaped_url = urllib.quote(self.request.host_url+"/file/"+download.name+"."+download.format+"?id="+fileId+"&fake=file."+download.format,'')
            else:
                download = DownloadMeta()
                download.failure = "Download not found"

        except Exception as e:
            download = DownloadMeta()
            download.failure = unicode(e)

        template_values = dict(fic = download,
                               nickname = user.nickname(),
                               escaped_url = escaped_url
                               )
        path = os.path.join(os.path.dirname(__file__), 'status.html')
        self.response.out.write(template.render(path, template_values))

class ClearRecentServer(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        logging.info("Clearing Recent List for user: "+user.nickname())
        q = DownloadMeta.all()
        q.filter('user =', user)
        num=0
        while( True ):
            results = q.fetch(100)
            if results:
                for d in results:
                    d.delete()
                    for chunk in d.data_chunks:
                        chunk.delete()
                    num = num + 1
                    logging.debug('Delete '+d.url)
            else:
                break
        logging.info('Deleted %d instances download.' % num)
        self.redirect("/?error=recentcleared")

class RecentFilesServer(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        q = DownloadMeta.all()
        q.filter('user =', user).order('-date')
        fics = q.fetch(100)
        logging.info("Recent fetched %d downloads for user %s."%(len(fics),user.nickname()))

        for fic in fics:
            if fic.completed and fic.format == 'epub':
                fic.escaped_url = urllib.quote(self.request.host_url+"/file/"+fic.name+"."+fic.format+"?id="+unicode(fic.key())+"&fake=file."+fic.format,'')

        template_values = dict(fics = fics, nickname = user.nickname())
        path = os.path.join(os.path.dirname(__file__), 'recent.html')
        self.response.out.write(template.render(path, template_values))

class AllRecentFilesServer(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url(self.request.uri))
            return

        q = SavedMeta.all()
        if self.request.get('bydate'):
            q.order('-date')
        else:
            q.order('-count')

        fics = q.fetch(200)
        logging.info("Recent fetched %d downloads for user %s."%(len(fics),user.nickname()))

        sendslugs = []

        for fic in fics:
            ficslug = FicSlug(fic)
            sendslugs.append(ficslug)

        template_values = dict(fics = sendslugs, nickname = user.nickname())
        path = os.path.join(os.path.dirname(__file__), 'allrecent.html')
        self.response.out.write(template.render(path, template_values))

class FicSlug():
    def __init__(self,savedmeta):
        self.url = savedmeta.url
        self.count = savedmeta.count
        for k, v in savedmeta.meta.iteritems():
            if k == 'description':
                v = stripHTML(v)
            setattr(self,k,v)

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

        if not url or url.strip() == "":
            self.redirect('/')
            return

        # Allow chapter range with URL.
        # like test1.com?sid=5[4-6] or [4,6]
        url,ch_begin,ch_end = adapters.get_url_chapter_range(url)

        logging.info("Queuing Download: %s" % url)
        login = self.request.get('login')
        password = self.request.get('password')
        is_adult = self.request.get('is_adult') == "on"
        email = self.request.get('email')

        # use existing record if available.  Fetched/Created before
        # the adapter can normalize the URL in case we need to record
        # an exception.
        download = getDownloadMeta(url=url,user=user,format=format,new=True)

        adapter = None
        try:
            try:
                configuration = self.getUserConfig(user,url,format)
            except exceptions.UnknownSite:
                self.redirect("/?error=custom&errtext=%s"%urllib.quote("Unsupported site in URL (%s).  See 'Support sites' list below."%url,''))
                return
            except Exception as e:
                self.redirect("/?error=custom&errtext=%s"%urllib.quote("There's an error in your User Configuration: "+unicode(e),'')[:2048]) # limited due to Locatton header length limit.
                return

            adapter = adapters.getAdapter(configuration,url)
            adapter.setChaptersRange(ch_begin,ch_end)
            logging.info('Created an adaper: %s' % adapter)

            if login or password:
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

            ## Fetch again using normalized story URL.  The one
            ## fetched/created above, if different, will not be saved.
            download = getDownloadMeta(url=story.getMetadata('storyUrl'),
                                       user=user,format=format,new=True)

            download.title = story.getMetadata('title')
            download.author = story.getMetadata('author')
            download.url = story.getMetadata('storyUrl')
            download.ch_begin = ch_begin
            download.ch_end = ch_end
            download.put()

            taskqueue.add(url='/fdowntask',
                      queue_name="download",
                          params={'id':unicode(download.key()),
                                  'format':format,
                                  'url':download.url,
                                  'login':login,
                                  'password':password,
                                  'user':user.email(),
                                  'email':email,
                                  'is_adult':is_adult})

            logging.info("enqueued download key: " + unicode(download.key()))

        except (exceptions.FailedToLogin,exceptions.AdultCheckRequired), e:
            download.failure = unicode(e)
            download.put()
            logging.info(unicode(e))
            is_login= ( isinstance(e, exceptions.FailedToLogin) )
            is_passwdonly = is_login and e.passwdonly
            template_values = dict(nickname = user.nickname(),
                                   url = url,
                                   format = format,
                                   site = adapter.getConfigSection(),
                                   fic = download,
                                   is_login=is_login,
                                   is_passwdonly=is_passwdonly
                                   )
            # thewriterscoffeeshop.com can do adult check *and* user required.
            if isinstance(e,exceptions.AdultCheckRequired):
                template_values['login']=login
                template_values['password']=password

            path = os.path.join(os.path.dirname(__file__), 'login.html')
            self.response.out.write(template.render(path, template_values))
            return
        except (exceptions.InvalidStoryURL,exceptions.UnknownSite,exceptions.StoryDoesNotExist), e:
            logging.warn(unicode(e))
            download.failure = unicode(e)
            download.put()
        except Exception as e:
            logging.error("Failure Queuing Download: url:%s" % url)
            logging.exception(e)
            download.failure = unicode(e)
            download.put()

        self.redirect('/status?id='+unicode(download.key()))

        return


class FanfictionDownloaderTask(UserConfigServer):

    def post(self):
        logging.getLogger().setLevel(logging.DEBUG)
        fileId = self.request.get('id')
        # User object can't pass, just email address
        user = users.User(self.request.get('user'))
        format = self.request.get('format')
        url = self.request.get('url')
        login = self.request.get('login')
        password = self.request.get('password')
        is_adult = self.request.get('is_adult')
        email = self.request.get('email')

        logging.info("Downloading: " + url + " for user: "+user.nickname())
        logging.info("ID: " + fileId)

        adapter = None
        writerClass = None

        # use existing record if available.
        # fileId should have record from /fdown.
        download = getDownloadMeta(id=fileId,url=url,user=user,format=format,new=True)
        for chunk in download.data_chunks:
            chunk.delete()
        download.put()

        logging.info('Creating adapter...')

        try:
            configuration = self.getUserConfig(user,url,format)
            adapter = adapters.getAdapter(configuration,url)
            adapter.setChaptersRange(download.ch_begin,download.ch_end)

            logging.info('Created an adapter: %s' % adapter)

            if login or password:
                adapter.username=login
                adapter.password=password
            adapter.is_adult=is_adult

            # adapter.getStory() is what does all the heavy lifting.
            # adapter.getStoryMetadataOnly() only fetches enough to
            # get metadata.  writer.writeStory() will call
            # adapter.getStory(), too.
            writer = writers.getWriter(format,configuration,adapter)
            download.name = writer.getOutputFileName()
            #logging.debug('output_filename:'+writer.getConfig('output_filename'))
            logging.debug('getOutputFileName:'+writer.getOutputFileName())
            download.title = adapter.getStory().getMetadata('title')
            download.author = adapter.getStory().getMetadata('author')
            download.url = adapter.getStory().getMetadata('storyUrl')
            download.put()

            allmeta = adapter.getStory().getAllMetadata(removeallentities=True,doreplacements=False)

            outbuffer = BytesIO()
            writer.writeStory(outbuffer)
            data = outbuffer.getvalue()
            outbuffer.close()
            del outbuffer
            #del writer.adapter
            #del writer.story
            del writer
            #del adapter.story
            del adapter

            # logging.debug("Email: %s"%email)
            # if email and re.match(r"^[^@]+@[^@]+", email):
            #     try:
            #         logging.info("Email Attempt")
            #         send_mail_attachment(user.email(),
            #                              email.strip(),
            #                              download.title + " by " + download.author,
            #                              download.title + " by " + download.author + " URL: "+download.url,
            #                              download.name,
            #                              data)
            #         logging.info("Email Sent")
            #     except Exception as e:
            #         # download.failure = "Failed to send Email %s"%unicode(e)
            #         logging.warn(e, exc_info=True)

            # epubs are all already compressed.  Each chunk is
            # compressed individually to avoid having to hold the
            # whole in memory just for the compress/uncompress.
            if format != 'epub':
                def compress(data):
                    return zlib.compress(data)
            else:
                def compress(data):
                    return data

            # delete existing chunks first
            for chunk in download.data_chunks:
                chunk.delete()

            index=0
            while( len(data) > 0 ):
                # logging.info("len(data): %s" % len(data))
                DownloadData(download=download,
                             index=index,
                             blob=compress(data[:1000000])).put()
                index += 1
                data = data[1000000:]
            download.completed=True
            download.put()

            smetal = SavedMeta.all().filter('url =', allmeta['storyUrl'] ).fetch(1)
            if smetal and smetal[0]:
                smeta = smetal[0]
                smeta.count += 1
            else:
                smeta=SavedMeta()
                smeta.count = 1

            smeta.url = allmeta['storyUrl']
            smeta.title = allmeta['title']
            smeta.author = allmeta['author']
            smeta.meta = allmeta
            smeta.date = datetime.datetime.now()
            smeta.put()

            logging.info("Download finished OK")
            del data

        except Exception as e:
            logging.exception(e)
            download.failure = unicode(e)
            download.put()
            return

        return

def getDownloadMeta(id=None,url=None,user=None,format=None,new=False):
    ## try to get download rec from passed id first.  then fall back
    ## to user/url/format
    download = None
    if id:
        try:
            download = db.get(db.Key(id))
            logging.info("DownloadMeta found by ID:"+id)
        except:
            pass

    if not download and url and user and format:
        try:
            q = DownloadMeta.all().filter('user =', user).filter('url =',url).filter('format =',format).fetch(1)
            if( q is not None and len(q) > 0 ):
                logging.debug("DownloadMeta found by user:%s url:%s format:%s"%(user,url,format))
                download = q[0]
        except:
            pass

    if new:
        # NOT clearing existing chunks here, because this record may
        # never be saved.
        if not download:
            logging.debug("New DownloadMeta")
            download = DownloadMeta()

        download.completed=False
        download.failure=None
        download.date=datetime.datetime.now()

        download.version = "%s:%s" % (os.environ['APPLICATION_ID'],os.environ['CURRENT_VERSION_ID'])
        if user:
            download.user = user
        if url:
            download.url = url
        if format:
            download.format = format

    return download

def send_mail_attachment(sender,to,subject,body,attach_fn,attach_data):
    msg = mail.EmailMessage()
    msg.sender = sender
    msg.to = [to]
    msg.subject = subject
    msg.body = body
    msg.attachments = [mail.Attachment(attach_fn,attach_data)]
    msg.check_initialized()
    msg.send()

logging.getLogger().setLevel(logging.DEBUG)
app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/fdowntask', FanfictionDownloaderTask),
                               ('/fdown', FanfictionDownloader),
                               (r'/file.*', FileServer),
                               ('/status', FileStatusServer),
                               ('/allrecent', AllRecentFilesServer),
                               ('/recent', RecentFilesServer),
                               ('/editconfig', EditConfigServer),
                               ('/clearrecent', ClearRecentServer),
                               ],
                              debug=False)
