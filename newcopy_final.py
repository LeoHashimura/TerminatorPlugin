from gi.repository import Gtk, Gdk
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg

AVAILABLE = ['SmartPaste']

class SmartPaste(plugin.MenuItem):
    capabilities = ['terminal_menu']
    
    _window = None
    _text_entry = None
    _target_terminal = None

    def __init__(self):
        super(SmartPaste, self).__init__()
        self.terminator = Terminator()
        dbg("SmartPaste: Plugin initialized.")

    def callback(self, menu, menuitems, terminal):
        item = Gtk.MenuItem.new_with_mnemonic('_Smart Paste')
        
        window = terminal.get_toplevel()
        accel_group = Gtk.AccelGroup()
        window.add_accel_group(accel_group)
        
        key, mod = Gtk.accelerator_parse("<Primary><Shift>v")
        item.add_accelerator("activate", accel_group, key, mod, Gtk.AccelFlags.VISIBLE)
        
        item.connect("activate", self.on_activate, terminal)
        menu.append(item)

    def get_active_terminal(self):
        """Finds the currently focused terminal."""
        for term in self.terminator.terminals:
            if term.vte.is_focus():
                return term
        return None

    def on_activate(self, menu_item, fallback_terminal):
        """Called by the keybinding or menu click."""
        self._target_terminal = self.get_active_terminal()
        if not self._target_terminal:
            self._target_terminal = fallback_terminal

        if not self._target_terminal:
            dbg("SmartPaste: Could not determine target terminal.")
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.request_text(self._on_clipboard_text_received)

    def _on_clipboard_text_received(self, clipboard, text):
        """Checks clipboard content and decides whether to show the window."""
        if text and '\n' in text:
            dbg("SmartPaste: Multi-line text detected, showing window.")
            self._show_window()
        elif self._target_terminal:
            dbg("SmartPaste: Single-line text detected, pasting directly.")
            self._target_terminal.paste_clipboard()
        else:
            dbg("SmartPaste: No text on clipboard or no terminal.")

    def _show_window(self, menu_item=None, *args):
        if self._window and self._window.is_visible():
            self._window.present()
            self._update_clipboard_text()
            return

        window = Gtk.Window(title='Smart Paste')
        window.set_default_size(400, 200)

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
        window.connect("key-press-event", self._on_window_key_press)

        window.show_all()
        self._update_clipboard_text()

    def _on_window_destroy(self, widget):
        self._window = None
        self._text_entry = None

    def _update_clipboard_text(self):
        if self._text_entry:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.request_text(self._on_clipboard_received_for_window)

    def _on_clipboard_received_for_window(self, clipboard, text):
        if self._text_entry:
            self._text_entry.get_buffer().set_text(text if text else "")

    def _on_window_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Return and (event.state & Gdk.ModifierType.ALT_MASK):
            self._send_content()
            return True
        return False

    def _send_content(self):
        if not self._target_terminal or not self._text_entry:
            dbg("SmartPaste: No target terminal or textbox.")
            return

        text_buffer = self._text_entry.get_buffer()
        text = text_buffer.get_text(text_buffer.get_start_iter(), text_buffer.get_end_iter(), False)

        if text:
            self._target_terminal.vte.feed_child(text.encode('utf-8'))
            dbg(f"SmartPaste: Sent {len(text)} chars to terminal.")
            if self._window:
                self._window.destroy()
        else:
            dbg("SmartPaste: Textbox empty.")
