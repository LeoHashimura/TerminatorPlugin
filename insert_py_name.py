import time
import gi
from gi.repository import Gtk
from gi.repository import GObject

from terminatorlib.config import Config
import terminatorlib.plugin as plugin
from terminatorlib.translation import _
from terminatorlib.util import err, dbg
from terminatorlib.version import APP_NAME

AVAILABLE = ['InsertTermName']

class InsertTermName(plugin.MenuItem):
   capabilities = ['terminal_menu']
   config = None

   def __init__(self):
      plugin.MenuItem.__init__(self)
   def sendText(self,_widget,terminal):#これを起動できれば一旦保存
       term = terminal
       term.vte.feed_child("echo MOMOMO\n\n\n\n".encode())
   def callback(self, menuitems, menu, terminal):
      item = Gtk.MenuItem.new_with_label('Insert terminal name')
      #item.connect('activate', lambda x: terminal.vte.feed_child("echo bea\n".encode()))
      item.connect('activate', self.sendText,terminal)
      menuitems.append(item)
