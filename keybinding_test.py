from terminatorlib import plugin
from gi.repository import Gtk, Gdk
from terminatorlib.util import dbg
from terminatorlib.terminator import Terminator

AVAILABLE = ['KeybindingTest']

class KeybindingTest(plugin.MenuItem):
    capabilities = ['terminal_menu']

    def __init__(self):
        super(KeybindingTest, self).__init__()
        dbg("KeybindingTest: Plugin initialized.")
        self.terminator = Terminator()

    def callback(self, menu, menuitems, terminal):
        dbg("KeybindingTest CB: Menu generated for terminal: %s" % terminal)
        item = Gtk.MenuItem.new_with_mnemonic('_Keybinding Test')
        
        window = terminal.get_toplevel()
        accel_group = Gtk.AccelGroup()
        window.add_accel_group(accel_group)
        
        key, mod = Gtk.accelerator_parse("<Primary><Shift>v")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        
        # We connect on_activate to the specific terminal from the callback
        item.connect("activate", self.on_activate, terminal)
        menu.append(item)

    def on_activate(self, menu_item, target_terminal):
        """This is the function that is called when the menu item is activated."""
        dbg("KeybindingTest ACTIVATE: Triggered.")
        
        active_terminal = None
        for term in self.terminator.terminals:
            if term.vte.is_focus():
                active_terminal = term
                break

        dbg("KeybindingTest ACTIVATE: Intended target terminal is %s" % target_terminal)
        dbg("KeybindingTest ACTIVATE: Found active terminal by is_focus(): %s" % active_terminal)
        
        if active_terminal:
            message = "SUCCESS: Writing to active terminal: %s\n" % active_terminal
            active_terminal.vte.feed_child(message.encode('utf-8'))
        else:
            dbg("KeybindingTest ACTIVATE: No active terminal found, falling back to target_terminal.")
            message = "SUCCESS: Writing to target terminal: %s\n" % target_terminal
            target_terminal.vte.feed_child(message.encode('utf-8'))

