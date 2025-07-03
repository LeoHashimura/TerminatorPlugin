from gi.repository import Gtk
import terminatorlib.plugin as plugin
from terminatorlib.config import Config
from terminatorlib.terminator import Terminator
AVAILABLE = ['New01MenuItem']

class New01MenuItem(plugin.MenuItem):
    capabilities = ['terminal_menu']    
    def __init__(self):
        self.config = Config()
        self.cwd = ""
        self.terminal = None
    def get_name(self):
        return "Echo Text"
    def _ontor(self,menu_item_add_tag):
        self.terminal = terminal
        term = terminal.terminator.get_target_terms(terminal)
        term.vte.feed_child("echo buzz")

    def callback(self, menuitem,menu,terminal):
        self.cwd = terminal.get_cwd()
        self.terminal = terminal

        menuitem = Gtk.ImageMenuItem(_('Open current directory'))
        menuitem.connect("activate", self._ontor)

        menuitems.append(menuitem)
