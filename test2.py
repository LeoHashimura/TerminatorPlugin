import terminatorlib.plugin as plugin
from terminatorlib.config import Config
# AVAILABLE must contain a list of all the classes that you want exposed
AVAILABLE = ['TestPlugin2']

class TestPlugin2(plugin.MenuItem):
    capabilities = ['test']
    config = None
    def do_test(self):
        return('TestPluginWin')
    def __init__(self):
        self.config = Config()
        myconfig = self.config.plugin_get_config(self.__class__.__name__)
        # Now extract valid data from sections{}

    def callback(self, menuitems, menu, terminal):
        menuitems.append(gtk.MenuItem('some jazz'))
        term = menuitem.terminator
        current_tab = term.get_active_tab()
        if current_tab:
            current_terminal = current_tab.get_active_terminal()
            if current_terminal:
                current_terminal.feed_child_binary(b"echo 'Hello World'\n")
