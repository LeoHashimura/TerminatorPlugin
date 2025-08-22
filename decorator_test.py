
import inspect
from gi.repository import Gtk, Gdk
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg

# This is the decorator. It "tags" a function with the signal it should handle.
def on_terminal_event(signal_name):
    def decorator(func):
        setattr(func, '_is_terminal_event_handler', True)
        setattr(func, '_signal_name', signal_name)
        return func
    return decorator

# Plugin name for Terminator to find
AVAILABLE = ['DecoratorTestPlugin']

class DecoratorTestPlugin(plugin.Plugin):
    capabilities = ['terminal_menu'] # Must be a plugin type

    def __init__(self):
        super(DecoratorTestPlugin, self).__init__()
        dbg("DecoratorTestPlugin: Initializing...")
        terminator = Terminator()

        # Connect to the 'new-window' signal on the top-level Terminator object
        terminator.connect('new-window', se 

        # For any windows that already exist, manually trigger the setup.
        for window in terminator.windows:
            self._on_new_window(terminator, window)

        dbg("DecoratorTestPlugin: Ready.")

    def _on_new_window(self, terminator, window):
        """Called when a new window is created."""
        dbg(f"DecoratorTestPlugin: New window {window}, connecting its 'new-terminal' signal.")
        # Connect to the 'new-terminal' signal for this specific window
        window.connect('new-terminal', self._on_new_terminal)
        # Also connect to any terminals that might already be in the new window
        for term in window.terminals:
            self._connect_handlers(term)

    def _on_new_terminal(self, window, terminal):
        """Called when a new terminal is created within a window."""
        dbg(f"DecoratorTestPlugin: New terminal {terminal} in {window}, connecting handlers...")
        self._connect_handlers(terminal)

    def _connect_handlers(self, terminal):
        """
        Inspects the class for any methods tagged by our decorator
        and connects them to the terminal's VTE widget.
        """
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, '_is_terminal_event_handler', False):
                signal = getattr(method, '_signal_name')
                # This is where the actual connection happens
                terminal.vte.connect(signal, method)
                dbg(f"SUCCESS: Connected '{signal}' on {terminal} to method '{name}'")

    # --- Decorated Event Handlers ---

    @on_terminal_event('button-press-event')
    def handle_mouse_click(self, vte, event):
        """This handler is for mouse clicks."""
        # We only care about right-click for this test (button 3)
        if event.button == 3:
            dbg("DecoratorTest: Right-click detected!")
        return False # Allow the event to continue

    @on_terminal_event('key-press-event')
    def handle_key_press(self, vte, event):
        """This handler is for key presses."""
        if event.keyval == Gdk.KEY_F12:
            dbg("DecoratorTest: F12 key press detected!")
            return True # Stop the event from being processed further
        return False
