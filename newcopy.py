from gi.repository import Gtk, Gdk
# Essential Terminator plugin imports
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg # Keep dbg for minimal feedback

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
        
        # Connect to all terminals existing at plugin init
        for terminal in Terminator().terminals:
            # Connect key-press-event to the VTE widget of each terminal
            terminal.vte.connect("key-press-event", self._on_vte_key_press)

    def callback(self, menulist, menu, terminal):
        self._target_terminal = terminal # Set target if opened via menu
        item = Gtk.MenuItem.new_with_label("Clipboard Paste")
        item.connect('activate', self._show_window)
        menulist.append(item)
        for terminal in Terminator().terminals:
            # Connect key-press-event to the VTE widget of each terminal
            terminal.vte.connect("key-press-event", self._on_vte_key_press)
            
    
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
        text_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add(text_entry)
        vbox.pack_start(scrolled_window, True, True, 0)
        
        self._window = window
        self._text_entry = text_entry
        
        window.connect("destroy", self._on_window_destroy)
        window.connect("key-press-event", self._on_window_key_press) # Key to SEND content

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

    # Key press handler for TERMINAL VTE (to OPEN window)
    def _on_vte_key_press(self, vte_widget, event):
        if self._window and self._window.is_visible():
            return False # Window already open, don't interfere
        if event.keyval == Gdk.KEY_F9:
            for term in Terminator().terminals:
                if term.vte == vte_widget:
                    self._target_terminal = term # Set target if opened via keypress
                    break
            if self._target_terminal:
                self._show_window()
                return True # Event handled
        return False # Let other handlers process
    def _on_window_key_press(self, widget, event):
        # Example: F9 or Alt+Enter to send content
        if event.keyval == Gdk.KEY_F9 
#           (event.keyval == Gdk.KEY_Return and (event.state & Gdk.ModifierType.ALT_MASK)):
            if (event.keyval == Gdk.KEY_F9 and (event.state & Gdk.ModifierType.ALT_MASK)):
                debug("send one line")
            elif:
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
