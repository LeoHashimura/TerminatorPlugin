# -*- coding: utf-8 -*
"""
A Terminator plugin to test the behavior of the configuration system.
This plugin adds a menu item that, when clicked, saves a sample data structure
to the Terminator configuration, reads it back, and verifies if the read data
matches the original data.
"""

import copy
from gi.repository import Gtk
from terminatorlib import plugin
from terminatorlib.util import dbg
from terminatorlib import config

AVAILABLE = ['ConfigTestPlugin']

class ConfigTestPlugin(plugin.MenuItem):
    """
    A plugin to test saving and loading configuration data in Terminator.
    """
    capabilities = ['terminal_menu']
    plugin_name = 'ConfigTestPlugin'

    def __init__(self):
        plugin.MenuItem.__init__(self)
        dbg(f"[{self.plugin_name}] Initialized.")

    def callback(self, menuitems, menu, terminal):
        """Adds the menu item to the terminal context menu."""
        item = Gtk.MenuItem.new_with_label("Test Config Read/Write")
        item.connect('activate', self.run_test)
        menuitems.append(item)

    def run_test(self, menu_item):
        """
        The core logic of the test. Saves, reads, and compares config data.
        """
        dbg(f"[{self.plugin_name}] Running configuration test.")

        # 1. Define sample data, similar to multi_ssh's recent_hosts
        test_data = [
            {'hostname': 'test-host-1', 'ip_address': '192.168.1.1', 'username': 'user1'},
            {'hostname': 'test-host-2', 'ip_address': '192.168.1.2', 'username': 'user2'},
            {'hostname': 'test-host-3', 'ip_address': '192.168.1.3', 'username': 'user3'}
        ]
        
        # Use a deep copy for a reliable comparison after the save/read cycle
        original_data = copy.deepcopy(test_data)
        config_key = 'test_data_list'

        # 2. Save the data to the Terminator config
        conf = config.Config()
        conf.plugin_set(self.plugin_name, config_key, test_data)
        conf.save()
        dbg(f"[{self.plugin_name}] Saved data to config key '{config_key}': {test_data}")

        # 3. Read the data back from the config
        # We instantiate a new Config object to ensure we are reading from the file
        # on disk, not from a cached version in the current object.
        conf_read = config.Config()
        plugin_config = conf_read.plugin_get_config(self.plugin_name)
        
        read_data = []
        if isinstance(plugin_config, dict):
            read_data = plugin_config.get(config_key, [])
        
        dbg(f"[{self.plugin_name}] Read data from config key '{config_key}': {read_data}")

        # 4. Compare the original data with the read data and report the result
        if original_data == read_data:
            dbg(f"[{self.plugin_name}] SUCCESS: Read data matches original data.")
            self.show_result_dialog(
                "Config Test: SUCCESS",
                "The data read from the configuration file is identical to the data that was saved."
            )
        else:
            dbg(f"[{self.plugin_name}] FAILURE: Read data does not match original data.")
            dbg(f"[{self.plugin_name}] Original data: {original_data}")
            dbg(f"[{self.plugin_name}] Read data: {read_data}")
            self.show_result_dialog(
                "Config Test: FAILURE",
                "The data read from the configuration file does NOT match the original data.\n\n" \
                f"Original:\n{original_data}\n\n" \
                f"Read:\n{read_data}\n\n" \
                "Check the debugging output for more details."
            )

    def show_result_dialog(self, title, message):
        """Displays a simple GTK dialog to show the test result."""
        dialog = Gtk.MessageDialog(
            None,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()