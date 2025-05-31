from gi.repository import Gtk, Gdk
import os
import sys

try:
    from terminatorlib import plugin
    from terminatorlib.terminator import Terminator
    from terminatorlib.util import dbg, err
    from terminatorlib.config import Config
except ImportError:
    # Fallback for testing outside Terminator, though this approach is highly
    # dependent on Terminator's internal structure.
    print("Warning: terminatorlib not found. This plugin might not work correctly outside Terminator.")
    class DummyPlugin:
        pass
    plugin = DummyPlugin()
    dbg = print
    err = print
    Config = type('Config', (object,), {'get_item': lambda s, k: None}) # Dummy Config class

# Name of your plugin class
AVAILABLE = ['ClipboardP']

class ClipboardP(plugin.MenuItem): # Still inherit from plugin.MenuItem for menu integration
    capabilities = ['terminal_menu']
    
    # Static variable to hold the single instance of the plugin's window
    # This prevents multiple windows if the menu item is clicked repeatedly
    _instance_window = None
    _instance_text_entry = None
    _instance_terminal = None # The terminal that last opened the window or received the keybind

    def __init__(self):
        plugin.MenuItem.__init__(self)
        self.config = Config() # Get Terminator's configuration
        self.keybinding_active = False # Flag to control if our keybinding is active
        self.terminal_key_connections = {} # Store signal IDs for each terminal VTE
        
        # Connect to Terminator's terminal creation/destruction signals
        # This is how we ensure our key listener is on all relevant terminals
        Terminator().connect('terminal_created', self.on_terminal_created)
        Terminator().connect('terminal_closed', self.on_terminal_closed)

        # Initial scan for existing terminals
        for terminal in Terminator().terminals:
            self.on_terminal_created(Terminator(), terminal)

    # This 'callback' method is specific to plugin.MenuItem and is called by Terminator
    def callback(self, menulist, menu, terminal):
        # The terminal passed here is the one where the right-click occurred
        # We'll use this to ensure the window opens relative to that terminal
        ClipboardP._instance_terminal = terminal
        item = Gtk.MenuItem.new_with_label("Clipboard Paste (Keybind)")
        item.connect('activate', self.show_clipboard_window) # No need to pass terminal here, use _instance_terminal
        menulist.append(item)

    # Handler for when a new terminal is created
    def on_terminal_created(self, terminator, terminal):
        dbg(f"ClipboardP: Terminal created: {terminal.uuid}")
        # Connect our key press handler to the VTE widget of the new terminal
        # This makes the keybinding work when this specific terminal is focused
        handler_id = terminal.vte.connect("key-press-event", self.on_vte_key_press_event)
        self.terminal_key_connections[terminal.uuid] = handler_id
        dbg(f"ClipboardP: Connected key-press-event to terminal {terminal.uuid}")


    # Handler for when a terminal is closed
    def on_terminal_closed(self, terminator, terminal):
        dbg(f"ClipboardP: Terminal closed: {terminal.uuid}")
        # Disconnect our key press handler from the VTE widget
        if terminal.uuid in self.terminal_key_connections:
            handler_id = self.terminal_key_connections.pop(terminal.uuid)
            terminal.vte.disconnect(handler_id)
            dbg(f"ClipboardP: Disconnected key-press-event from terminal {terminal.uuid}")

    # This method creates and manages the plugin's window
    def show_clipboard_window(self, menu_item=None, *args):
        # If the window exists and is visible, just present it and refresh clipboard
        if ClipboardP._instance_window and ClipboardP._instance_window.is_visible():
            ClipboardP._instance_window.present()
            self.update_from_cb()
            return

        # Create the window for the first time
        window = Gtk.Window(title='Clipboard Paste')
        window.set_default_size(400, 200)
        window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        window.set_resizable(True)
        window.set_keep_above(True)
        window.set_transient_for(Gtk.Window.get_toplevel(ClipboardP._instance_terminal.vte)) # Attach to Terminator window

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_border_width(10)
        window.add(vbox)

        text_entry = Gtk.TextView()
        text_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        text_entry.set_editable(True)
        text_entry.set_cursor_visible(True)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(text_entry)
        vbox.pack_start(scrolled_window, True, True, 0)
        
        # Store references to the window and textbox on the class itself
        # so they can be accessed from any instance of the plugin
        ClipboardP._instance_window = window
        ClipboardP._instance_text_entry = text_entry
        
        # Connect the destroy signal to ensure we clear references when the window is closed
        window.connect("destroy", self.on_window_destroy)

        window.show_all()
        self.update_from_cb()

    def on_window_destroy(self, widget):
        dbg("ClipboardP: Plugin window destroyed, clearing references.")
        ClipboardP._instance_window = None
        ClipboardP._instance_text_entry = None
        # Don't clear _instance_terminal here, it's still potentially active

    def update_from_cb(self):
        # Check if the text_entry instance exists before trying to use it
        if ClipboardP._instance_text_entry:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.request_text(self.on_clipboard_text_received)
        else:
            dbg("ClipboardP: No text_entry instance found to update from clipboard.")


    def on_clipboard_text_received(self, clipboard, text):
        if ClipboardP._instance_text_entry:
            buffer = ClipboardP._instance_text_entry.get_buffer()
            buffer.set_text(text if text else "")

    # This is the key press handler for the VTE (terminal content) widgets
    def on_vte_key_press_event(self, vte_widget, event):
        # We only want to open the window if it's not already open
        if ClipboardP._instance_window and ClipboardP._instance_window.is_visible():
            return False # Don't interfere if window is already open

        # Determine the key combination you want to use to show the window
        # Example: Ctrl+Shift+C (or any key that won't conflict)
        # Using a more obscure key to avoid conflicts with existing Terminator/shell bindings
        # Let's try F8 (no modifiers) to open the window
        # Or you could use something like Ctrl+Shift+C/V/X to differentiate from normal paste
        
        # Example: F8 to open the window
        if event.keyval == Gdk.KEY_F8 and not (event.state & GGdk.ModifierType.CONTROL_MASK or event.state & Gdk.ModifierType.SHIFT_MASK or event.state & Gdk.ModifierType.ALT_MASK):
            dbg("ClipboardP: F8 pressed in VTE. Attempting to show window.")
            # Set the terminal from which the keypress originated
            # This is critical for knowing where to paste later
            # vte_widget.get_parent_window() might lead to the Gtk.Terminal (parent of Vte)
            # Find the Terminal object associated with this vte_widget
            for term in Terminator().terminals:
                if term.vte == vte_widget:
                    ClipboardP._instance_terminal = term
                    break
            
            if ClipboardP._instance_terminal:
                self.show_clipboard_window()
                return True # Event handled, don't let it pass to terminal
            else:
                dbg("ClipboardP: Could not identify the originating terminal for F8 keypress.")

        return False # Key not handled by our plugin, let VTE process it


    # This is the key press handler for the plugin's own window
    def on_key_press_event(self, widget, event):
        # Check for F9 key
        if event.keyval == Gdk.KEY_F9:
            self.send_content_to_terminal()
            return True

        # Check for Alt+Return (Enter)
        elif event.keyval == Gdk.KEY_Return and (event.state & Gdk.ModifierType.ALT_MASK):
            self.send_content_to_terminal()
            return True

        return False # Key not handled by our plugin, let GTK process it

    def send_content_to_terminal(self):
        # Use the stored _instance_terminal
        if not ClipboardP._instance_terminal:
            dbg("ClipboardP: No active terminal set to send to.")
            return

        if not ClipboardP._instance_text_entry:
            dbg("ClipboardP: Text entry not initialized.")
            return

        buffer = ClipboardP._instance_text_entry.get_buffer()
        start_iter, end_iter = buffer.get_bounds()
        text = buffer.get_text(start_iter, end_iter, False)

        if text:
            # Send to the stored _instance_terminal
            ClipboardP._instance_terminal.vte.feed_child((text + '\n').encode('utf-8'))
            dbg(f"ClipboardP: Sent {len(text)} characters to terminal: '{text[:50]}...'")
            
            # Close the window after sending
            if ClipboardP._instance_window:
                ClipboardP._instance_window.destroy()
                # on_window_destroy will clear _instance_window and _instance_text_entry
        else:
            dbg("ClipboardP: Textbox is empty, nothing to send.")
