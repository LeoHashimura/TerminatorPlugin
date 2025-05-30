import re
from gi.repository import Gtk

from terminatorlib.config import Config
import terminatorlib.plugin as plugin
from terminatorlib.translation import _
from terminatorlib.util import get_config_dir, err, dbg, gerr

AVAILABLE = ['Menutest']

class Menutest(plugin.MenuItem):
   capabilities = ['terminal_menu']
   config = None
   SENDLINE = "ls"
   WAITTXT = "$"
   bl_match = False
   def __init__(self):
      plugin.MenuItem.__init__(self)
   def sendText(self,_widget,terminal):#これを起動できれば一旦保存
       term = terminal
       term.vte.feed_child("echo MOMOnokiMO\n\n\n\n".encode())
       ##the content above does not show immediatly because the terminal refreshes after these line end.
       
       text_content, _ = term.vte.get_text()
       txtlines = text_content.split()

       for ln in txtlines:
         if not(ln):
             next
         dbg(ln)
   def callback(self, menuitems, menu, terminal):
      item = Gtk.MenuItem.new_with_label('Insert terminal name')
      #item.connect('activate', lambda x: terminal.vte.feed_child("echo bea\n".encode()))
      item.connect('activate', self.sendText,terminal)
      terminal.vte.connect('contents-changed', self.debugtxt,terminal)

      menuitems.append(item)
   def debugtxt(self,_widget,terminal):
       #text_content, _ = terminal.vte.get_text()
       #txtlines = text_content.split()
       (col, row) = terminal.vte.get_cursor_position()
       lntxt ,_= terminal.vte.get_text_range(row, 0, row, col,lambda *a: True)
       dbgtxt = "row{}col{}  {}".format(row,col,lntxt)
       dbg(dbgtxt)