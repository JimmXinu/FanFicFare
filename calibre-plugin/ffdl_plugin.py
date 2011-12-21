#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import,
                        print_function)

__license__   = 'GPL v3'
__copyright__ = '2011, Jim Miller'
__docformat__ = 'restructuredtext en'

from StringIO import StringIO
import ConfigParser
from functools import partial

# The class that all interface action plugins must inherit from
from calibre.ptempfile import PersistentTemporaryFile
from calibre.ebooks.metadata import MetaInformation
from calibre.gui2 import error_dialog, warning_dialog, question_dialog, info_dialog
from calibre.gui2.actions import InterfaceAction
from calibre.gui2.threaded_jobs import ThreadedJob

from calibre_plugins.fanfictiondownloader_plugin.fanficdownloader import adapters, writers, exceptions
from calibre_plugins.fanfictiondownloader_plugin.config import prefs
from calibre_plugins.fanfictiondownloader_plugin.dialogs import (
    DownloadDialog, MetadataProgressDialog, UserPassDialog, OVERWRITE, ADDNEW, SKIP)

# because calibre immediately transforms html into zip and don't want
# to have an 'if html'.  db.has_format is cool with the case mismatch,
# but if I'm doing it anyway...
formmapping = {
    'epub':'EPUB',
    'mobi':'MOBI',
    'html':'ZIP',
    'txt':'TXT'
    }

class FanFictionDownLoaderPlugin(InterfaceAction):

    name = 'FanFictionDownLoader'

    # Declare the main action associated with this plugin
    # The keyboard shortcut can be None if you dont want to use a keyboard
    # shortcut. Remember that currently calibre has no central management for
    # keyboard shortcuts, so try to use an unusual/unused shortcut.
    # (text, icon_path, tooltip, keyboard shortcut)
    # icon_path isn't in the zip--icon loaded below.
    action_spec = ('FanFictionDownLoader', None,
                   'Download FanFiction stories from various web sites', None)

    action_type = 'global'
    
    def genesis(self):
        # This method is called once per plugin, do initial setup here

        # Set the icon for this interface action
        # The get_icons function is a builtin function defined for all your
        # plugin code. It loads icons from the plugin zip file. It returns
        # QIcon objects, if you want the actual data, use the analogous
        # get_resources builtin function.
        #
        # Note that if you are loading more than one icon, for performance, you
        # should pass a list of names to get_icons. In this case, get_icons
        # will return a dictionary mapping names to QIcons. Names that
        # are not found in the zip file will result in null QIcons.
        icon = get_icons('images/icon.png')
        
        # The qaction is automatically created from the action_spec defined
        # above
        self.qaction.setIcon(icon)
        # Call function when plugin triggered.
        self.qaction.triggered.connect(self.show_dialog)

    def show_dialog(self):
        # The base plugin object defined in __init__.py
        base_plugin_object = self.interface_action_base_plugin
        # Show the config dialog
        # The config dialog can also be shown from within
        # Preferences->Plugins, which is why the do_user_config
        # method is defined on the base plugin class
        do_user_config = base_plugin_object.do_user_config

        # The current database shown in the GUI
        # db is an instance of the class LibraryDatabase2 from database.py
        # This class has many, many methods that allow you to do a lot of
        # things.
        self.db = self.gui.current_db

        rows = self.gui.library_view.selectionModel().selectedRows()
        if rows:
            book_ids = self.gui.library_view.get_selected_ids()
            print("book_ids: %s"%book_ids)

        row = self.gui.library_view.currentIndex()
        if row.isValid():
            print("current id:%d"%self.gui.library_view.model().id(row))
        #self.db.get_identifiers()['url']
            
        # self.gui is the main calibre GUI. It acts as the gateway to access
        # all the elements of the calibre user interface, it should also be the
        # parent of the dialog
        # DownloadDialog just collects URLs, format and presents buttons.
        d = DownloadDialog(self.gui,
                           prefs,
                           self.qaction.icon(),
                           do_user_config,  # method for config button
                           self.start_downloads, # method to start downloads
                           )
        d.show()

    def apply_settings(self):
        # No need to do anything with perfs here, but we could.
        prefs

    def start_downloads(self,urls,fileform,
                        collision,updatemeta):
        self.ffdlconfig = ConfigParser.SafeConfigParser()
        self.ffdlconfig.readfp(StringIO(get_resources("defaults.ini")))
        self.ffdlconfig.readfp(StringIO(prefs['personal.ini']))

        url_list = get_url_list(urls)

        self.fetchmeta_qpd = \
            MetadataProgressDialog(self.gui,
                                url_list,
                                fileform,
                                partial(self.get_adapter_for_story, collision=collision),
                                partial(self.download_list,collision=collision,updatemeta=updatemeta),
                                self.db)
            
    def get_adapter_for_story(self,url,fileform,collision=SKIP):
        '''
        Returns adapter object for story at URL.  To be called from
        MetadataProgressDialog 'loop' to build up list of adapters.  Also
        pops dialogs for is adult, user/pass, duplicate
        '''
        
        print("URL:"+url)
        adapter = adapters.getAdapter(self.ffdlconfig,url)

        try:
            adapter.getStoryMetadataOnly()
        except exceptions.FailedToLogin:
            print("Login Failed, Need Username/Password.")
            userpass = UserPassDialog(self.gui,url)
            userpass.exec_() # exec_ will make it act modal
            if userpass.status:
                adapter.username = userpass.user.text()
                adapter.password = userpass.passwd.text()
            # else:
            #     del adapter
            #     return
        except exceptions.AdultCheckRequired:
            if question_dialog(self.gui, 'Are You Adult?', '<p>'+
                               "%s requires that you be an adult.  Please confirm you are an adult in your locale:"%url,
                               show_copy_button=False):
                adapter.is_adult=True
            # else:
            #     del adapter
            #     return

        # let exceptions percolate up.
        story = adapter.getStoryMetadataOnly()

        add=True
        if collision != ADDNEW:
            mi = MetaInformation(story.getMetadata("title"),
                                 (story.getMetadata("author"),)) # author is a list.

            identicalbooks = self.db.find_identical_books(mi)
            print(identicalbooks)
            ## more than one match will need to be handled differently.
            if identicalbooks and collision == SKIP:
                add=False
                #            book_id = identicalbooks.pop()
                #            print("formats:"+self.db.formats(book_id,index_is_id=True))
                #            print("has format:%s"%self.db.has_format(book_id,formmapping[fileform],index_is_id=True))
                #            if self.db.has_format(book_id,formmapping[fileform],index_is_id=True):
                # if question_dialog(self.gui, 'Update?', '<p>'+
                #                    "%s by %s is already in your library more than once.  Add/Replace this format?"%
                #                    (story.getMetadata("title"),story.getMetadata("author")),
                #                    show_copy_button=False):
                #     add=True

        if add:
            return adapter
        else:
            return None
        
    def download_list(self,adaptertuple_list,fileform,
                      collision=ADDNEW,
                      updatemeta=True):
        '''
        Called by MetadataProgressDialog to start story downloads BG processing.
        adapter_list is a list of tuples of (url,adapter)
        '''
        print("download_list")
        
        job = ThreadedJob('FanFictionDownload',
                          'Downloading FanFiction Stories',
                          func=self.do_story_downloads,
                          args=(adaptertuple_list, fileform, self.db),
                          kwargs={'collision':collision,'updatemeta':updatemeta},
                          callback=self._get_stories_completed)
        
        
        self.gui.job_manager.run_threaded_job(job)
        
        self.gui.status_bar.show_message('Downloading %d stories'%len(adaptertuple_list))

    def _get_stories_completed(self, job):
        print("_get_stories_completed")

    def do_story_downloads(self, adaptertuple_list, fileform, db,
                           **kwargs): # lambda x,y:x lambda makes small anonymous function.
        # abort=None, log=None, 
        '''
        Master job, loop to download this list of stories
        '''
        print("do_story_downloads")
        abort = kwargs['abort']
        notifications=kwargs['notifications']
        log = kwargs['log']
        notifications.put((0.01, 'Start Downloading Stories'))
        count = 0.01
        total = len(adaptertuple_list)
        # Queue all the jobs
        for (url,adapter) in adaptertuple_list:
            if abort.is_set():
                notifications.put(1.0,'Aborting...')
                return
            notifications.put((float(count)/total,
                               'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title")))
            log.prints(log.INFO,'Downloading %s'%adapter.getStoryMetadataOnly().getMetadata("title"))
            try:
                self.do_story_download(adapter,fileform,db,kwargs['collision'],kwargs['updatemeta'])
            except Exception as e:
                log.prints(log.ERROR,'Failed Downloading %s: %s'%
                           (adapter.getStoryMetadataOnly().getMetadata("title"),e))
                
            count = count + 1
        return
    
    def do_story_download(self,adapter,fileform,db,collision,updatemeta):
        print("do_story_download")
    
        story = adapter.getStoryMetadataOnly()
    
        mi = MetaInformation(story.getMetadata("title"),
                             (story.getMetadata("author"),)) # author is a list.
        
        writer = writers.getWriter(fileform,adapter.config,adapter)
        tmp = PersistentTemporaryFile("."+fileform)
        print("%s by %s"%(story.getMetadata("title"), story.getMetadata("author")))
        print("tmp: "+tmp.name)

        writer.writeStory(tmp)
        
        mi.set_identifiers({'url':story.getMetadata("storyUrl")})
        mi.publisher = story.getMetadata("site")    
        mi.tags = writer.getTags()
        mi.languages = ['en']
        mi.pubdate = story.getMetadataRaw('datePublished').strftime("%Y-%m-%d")
        mi.timestamp = story.getMetadataRaw('dateCreated').strftime("%Y-%m-%d")
        mi.comments = story.getMetadata("description")
    
        identicalbooks = self.db.find_identical_books(mi)
        print(identicalbooks)
        addedcount=0
        if identicalbooks and collision == OVERWRITE:
            ## more than one match?  add to first off the list.
            book_id = identicalbooks.pop()
            if updatemeta:
                db.set_metadata(book_id,mi)
            db.add_format_with_hooks(book_id, fileform, tmp, index_is_id=True)
        else:
            (notadded,addedcount)=db.add_books([tmp],[fileform],[mi], add_duplicates=True)
            
            
        # Otherwise list of books doesn't update right away.
        if addedcount:
            self.gui.library_view.model().books_added(addedcount)
    
        del adapter
        del writer

def f(x):
    if x.strip(): return True
    else: return False
    
def get_url_list(urls):
    return filter(f,urls.strip().splitlines())
