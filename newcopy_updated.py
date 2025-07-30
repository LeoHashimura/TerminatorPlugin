from gi.repository import Gtk, Gdk
# Essential Terminator plugin imports
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg # Keep dbg for minimal feedback
from terminatorlib.config import Config
from terminatorlib.plugin import KeyBindUtil

PluginActShow = "plugin_show_clipboard"
PluginActSend = "plugin_send_clipboard"

PluginShowDesc = "Show Clipboard Window"
PluginSendDesc = "Send Clipboard Content"

# Plugin name for Terminator to find
AVAILABLE = ['ClipboardD']

class ClipboardD(plugin.MenuItem):
    capabilities = ['terminal_menu']
    
    # Class-level attributes for the single window and textbox instance
    _window = None
    _text_entry = None
    _target_terminal = None # The terminal to send content to

    def __init__(self):
        plugin.MenuItem.__init__(self)
        config = Config()
        self.keyb = KeyBindUtil(config)
        self.keyb.bindkey_check_config([PluginShowDesc, PluginActShow, "<Alt>c"])
        self.keyb.bindkey_check_config([PluginSendDesc, PluginActSend, "<Alt>v"])

        # Connect to all terminals existing at plugin init
        for terminal in Terminator().terminals:
            # Connect key-press-event to the VTE widget of each terminal
            terminal.vte.connect("key-press-event", self.on_keypress)

    def unload(self):
        dbg("unloading ClipboardD")
        for terminal in Terminator().terminals:
            try:
                terminal.vte.disconnect_by_func(self.on_keypress)
            except:
                dbg("no connected signals for on_keypress")
        self.keyb.unbindkey([PluginShowDesc, PluginActShow, "<Alt>c"])
        self.keyb.unbindkey([PluginSendDesc, PluginActSend, "<Alt>v"])

    def callback(self, menulist, menu, terminal):
        self._target_terminal = terminal # Set target if opened via menu
        item = Gtk.MenuItem.new_with_label("Clipboard Paste")
        item.connect('activate', self._show_window)
        menulist.append(item)

    # Shows/creates the plugin window
    def _show_window(self, menu_item=None, *args):
        if self._window and self._window.is_visible():
            self._window.present()
            self._update_clipboard_text()
            return

        window = Gtk.Window(title='Clipboard')
        window.set_default_size(300, 150) # Minimal default size

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_border_width(6)
        window.add(vbox)

        text_entry = Gtk.TextView()
        text_entry.set_wrap_mode(Gtk.WrapMode.CHAR)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(text_entry)
        vbox.pack_start(scrolled_window, True, True, 0)
        
        self._window = window
        self._text_entry = text_entry
        
        window.connect("destroy", self._on_window_destroy)
        window.connect("key-press-event", self.on_keypress) # Key to SEND content

        window.show_all()
        self._update_clipboard_text()

    # Clears window/textbox references on destroy
    def _on_window_destroy(self, widget):
        self._window = None
        self._text_entry = None

    # Requests clipboard content asynchronously
    def _update_clipboard_text(self):
        if self._text_entry:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.request_text(self._on_clipboard_received)

    # Callback for received clipboard text
    def _on_clipboard_received(self, clipboard, text):
        if self._text_entry:
            self._text_entry.get_buffer().set_text(text if text else "")

    def on_keypress(self, widget, event):
        act = self.keyb.keyaction(event)
        dbg(f"keyaction: {act} {event.keyval}")

        if act == PluginActShow:
            if self._window and self._window.is_visible():
                return False # Window already open, don't interfere
            
            # Find the Terminal object that owns this vte_widget or window
            if isinstance(widget, Gtk.Vte.Terminal):
                for term in Terminator().terminals:
                    if term.vte == widget:
                        self._target_terminal = term
                        break
            elif isinstance(widget, Gtk.Window):
                # If the keypress is from the plugin window itself, the target terminal should already be set
                pass

            if self._target_terminal:
                self._show_window()
                return True # Event handled
            return False

        if act == PluginActSend:
            self._send_content()
            return True
        return False

    # Sends textbox content to the target terminal
    def _send_content(self):
        if not self._target_terminal or not self._text_entry:
            dbg("self: No target terminal or textbox.")
            return

        text = self._text_entry.get_buffer().get_text(
            self._text_entry.get_buffer().get_bounds()[0],
            self._text_entry.get_buffer().get_bounds()[1],
            False
        )

        if text:
            self._target_terminal.vte.feed_child((text + '\n').encode('utf-8'))
            dbg(f"self: Sent {len(text)} chars to terminal.")
            if self._window:
                self._window.destroy()
        else:
            dbg("ClipboardP: Textbox empty.")