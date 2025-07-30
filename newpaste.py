from gi.repository import Gtk, Gdk
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg

AVAILABLE = ['ClipboardReviewPaste']

class ClipboardReviewPaste(plugin.MenuItem):
    capabilities = ['terminal_menu']

    _window = None
    _text_entry = None
    _target_terminal = None

    def __init__(self):
        plugin.MenuItem.__init__(self)
        dbg("ClipboardReviewPaste plugin loaded")
        kb = Terminator().keybindings
        kb.register_action("review_paste", self.review_paste)
        try:
            kb.bindkey("review_paste", "z")
        except Exception as e:
            dbg(f"Error binding key: {e}")

    def review_paste(self, *args):
        """Keybinding handler"""
        dbg("Review Paste keybinding triggered!")
        active_terminal = Terminator().get_focused_terminal()
        if active_terminal:
            self._show_window(None, active_terminal)

    def callback(self, menulist, menu, terminal):
        """Adds the 'Clipboard Review Paste' menu item"""
        item = Gtk.MenuItem.new_with_label("Clipboard Review Paste")
        item.connect('activate', self._show_window, terminal)
        menulist.append(item)

    def _show_window(self, menu_item, terminal):
        """Shows/creates the plugin window"""
        self._target_terminal = terminal
        if self._window and self._window.is_visible():
            self._window.present()
            self._update_clipboard_text()
            return

        self._window = Gtk.Window(title='Clipboard Review')
        self._window.set_default_size(500, 300)
        self._window.connect("destroy", self._on_window_destroy)
        self._window.connect("key-press-event", self._on_window_key_press)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_border_width(12)
        self._window.add(vbox)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        vbox.pack_start(scrolled_window, True, True, 0)

        self._text_entry = Gtk.TextView()
        self._text_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        scrolled_window.add(self._text_entry)

        self._update_clipboard_text()
        self._window.show_all()

    def _on_window_destroy(self, widget):
        self._window = None
        self._text_entry = None

    def _update_clipboard_text(self):
        if self._text_entry:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.request_text(self._on_clipboard_received)

    def _on_clipboard_received(self, clipboard, text):
        if self._text_entry:
            self._text_entry.get_buffer().set_text(text if text else "")

    def _on_window_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_F9 or \
           (event.keyval == Gdk.KEY_Return and (event.state & Gdk.ModifierType.ALT_MASK)):
            self._send_content()
            return True
        return False

    def _send_content(self):
        if not self._target_terminal or not self._text_entry:
            dbg("Error: No target terminal or textbox.")
            return

        buffer = self._text_entry.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)

        if text:
            self._target_terminal.vte.feed_child(text.encode('utf-8'))
            if self._window:
                self._window.destroy()
        else:
            dbg("ClipboardReviewPaste: Textbox empty.")