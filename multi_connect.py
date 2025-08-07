# -*- coding: utf-8 -*-
import os
import re
import pandas as pd
from gi.repository import Gtk, GObject
from terminatorlib import plugin
from terminatorlib.util import dbg
from terminatorlib import config

AVAILABLE = ['MultiConnect']

class MultiConnect(plugin.MenuItem):
    """A Terminator plugin to manage and automate SSH and Telnet connections."""
    capabilities = ['terminal_menu']

    def __init__(self):
        plugin.MenuItem.__init__(self)
        self.hosts_data = []
        self.current_terminal = None
        self.search_text = ""

    def _get_vte(self, terminal):
        """Get the VTE in a version-independent way."""
        return terminal.get_vte() if hasattr(terminal, 'get_vte') else terminal.vte

    def callback(self, menuitems, menu, terminal):
        """Add our menu item to the Terminator menu."""
        self.current_terminal = terminal
        item = Gtk.MenuItem.new_with_label("Multi-Connect Login")
        item.connect('activate', self._show_host_selection_window)
        menuitems.append(item)

    def _read_hosts_from_excel(self):
        """Read host connection data from the hosts.xlsx file using pandas."""
        hosts = []
        plugin_dir = os.path.dirname(__file__)
        excel_path = os.path.join(plugin_dir, "hosts.xlsx")

        if not os.path.exists(excel_path):
            dbg("MultiConnect: hosts.xlsx not found at {}. Please create it.".format(excel_path))
            return hosts

        try:
            df = pd.read_excel(excel_path).fillna('')
            for _, row in df.iterrows():
                host_info = dict(row)
                host_info['prompts'] = []
                for i in range(1, 4): # Check for up to 3 prompt/response pairs
                    prompt_key = 'prompt_{}'.format(i)
                    response_key = 'response_{}'.format(i)
                    if host_info.get(prompt_key):
                        host_info['prompts'].append({
                            'prompt': host_info[prompt_key],
                            'response': host_info[response_key]
                        })
                hosts.append(host_info)
        except Exception as e:
            dbg("MultiConnect: Unexpected error reading hosts.xlsx: {}".format(e))
        return hosts

    def _show_host_selection_window(self, menu_item, *args):
        """Display the host selection window with a searchable list."""
        self.hosts_data = self._read_hosts_from_excel()

        if not self.hosts_data:
            dbg("MultiConnect: No hosts found. Window not shown.")
            return

        window = Gtk.Window(title="Multi-Connect Host Selection")
        window.set_default_size(500, 400)
        window.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        # The store now includes a protocol column
        store = Gtk.ListStore(str, str, str, object)
        for host in self.hosts_data:
            store.append([host.get('hostname', ''), host.get('ip_address', ''), host.get('protocol', ''), host])

        tree_model = store
        search_entry = None
        self.search_text = "" # Initialize the search attribute
        try:
            search_entry = Gtk.SearchEntry()
            search_entry.set_placeholder_text("Filter by host or IP...")
            model_filter = store.filter_new()
            model_filter.set_visible_func(self._filter_visible_func) # No data argument needed
            search_entry.connect("search-changed", self._on_search_changed, model_filter)
            vbox.pack_start(search_entry, False, False, 0)
            tree_model = model_filter
        except (AttributeError, TypeError):
            dbg("MultiConnect: Gtk.SearchEntry not available. Disabling search.")

        treeview = Gtk.TreeView(model=tree_model)
        treeview.set_headers_visible(True)
        for i, col_title in enumerate(["Hostname", "IP Address", "Protocol"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            treeview.append_column(column)

        treeview.connect("row-activated", self._on_row_activated, window, search_entry)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(treeview)
        vbox.pack_start(scrolled_window, True, True, 0)

        login_button = Gtk.Button(label="Login to Selected Host")
        login_button.connect("clicked", self._on_login_button_clicked, treeview, window, search_entry)
        vbox.pack_start(login_button, False, False, 0)

        jump_server_button = Gtk.Button(label="Login to Jump Server")
        jump_server_button.connect("clicked", self._on_default_login_button_clicked, window, search_entry)
        vbox.pack_start(jump_server_button, False, False, 0)

        window.show_all()

    def _on_row_activated(self, treeview, path, column, window, search_entry):
        model = treeview.get_model()
        treeiter = model.get_iter(path)
        if treeiter:
            host_info = None
            if isinstance(model, Gtk.TreeModelFilter):
                child_iter = model.convert_iter_to_child_iter(treeiter)
                host_info = model.get_model().get_value(child_iter, 3)
            else:
                host_info = model.get_value(treeiter, 3)
            
            if host_info and self.current_terminal:
                self._login_to_host(self.current_terminal, host_info, window, search_entry)
            else:
                dbg("MultiConnect: Cannot start session, terminal not found.")

    def _on_login_button_clicked(self, button, treeview, window, search_entry):
        """Handle the login button click event."""
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            host_info = None
            if isinstance(model, Gtk.TreeModelFilter):
                child_iter = model.convert_iter_to_child_iter(treeiter)
                host_info = model.get_model().get_value(child_iter, 3) # Column 3 is the host_info object
            else:
                host_info = model.get_value(treeiter, 3)
            
            if host_info and self.current_terminal:
                self._login_to_host(self.current_terminal, host_info, window, search_entry)
            else:
                dbg("MultiConnect: Cannot start session, terminal not found.")
        else:
            dbg("MultiConnect: No host selected.")

    def _on_default_login_button_clicked(self, button, window, search_entry):
        """Handle the jump server login button click event."""
        default_host_info = self._get_default_host_from_terminator_config()
        if self.current_terminal:
            self._login_to_host(self.current_terminal, default_host_info, window, search_entry)
        else:
            dbg("MultiConnect: Cannot start session, terminal not found.")

    def _get_default_host_from_terminator_config(self):
        """Get the dedicated jump server details from Terminator's main config."""
        conf = config.Config()
        plugin_name = self.__class__.__name__
        plugin_config = conf.plugin_get_config(plugin_name) or {}
        
        defaults = plugin_config.get("default_host", {})
        if not isinstance(defaults, dict): defaults = {}

        # Define default values for the jump server
        hostname = defaults.get('hostname', 'Jump-Server')
        ip_address = defaults.get('ip_address', '192.168.1.1')
        username = defaults.get('username', 'jumpuser')
        prompt = defaults.get('prompt', 'assword:')
        response = defaults.get('response', 'jumppass')

        # This part is a placeholder for a future feature to prompt for credentials
        # if they are not set, but for now we will use the defaults.

        prompts = [{'prompt': prompt, 'response': response}] if prompt and response else []

        return {
            'hostname': hostname,
            'ip_address': ip_address,
            'protocol': 'ssh', # Jump servers are almost always SSH
            'username': username,
            'prompts': prompts
        }

    def _login_to_host(self, terminal, host_info, window, search_entry):
        """Initiate the connection based on the selected protocol."""
        if hasattr(terminal, 'multi_connect_timeout_id') and terminal.multi_connect_timeout_id:
            GObject.source_remove(terminal.multi_connect_timeout_id)
            dbg("MultiConnect: Stopped previous login process on terminal {}.".format(terminal.uuid))

        protocol = host_info.get('protocol', 'ssh').lower()
        ip = host_info.get('ip_address')
        user = host_info.get('username')
        port = host_info.get('port', 23 if protocol == 'telnet' else 22) # Default port

        command = ""
        if protocol == 'ssh':
            command = "ssh {}@{}".format(user, ip)
        elif protocol == 'telnet':
            command = "telnet {} {}".format(ip, port)
        else:
            dbg("MultiConnect: Unsupported protocol '{}'.".format(protocol))
            if search_entry: search_entry.set_text("Error: Unknown protocol '{}'".format(protocol))
            return

        vte = self._get_vte(terminal)
        vte.feed_child("{}\n".format(command).encode('utf-8'))
        dbg("MultiConnect: Issued command to {}: {}".format(ip, command))

        if host_info.get('prompts'):
            start_time = GObject.get_current_time()
            prompt_state = {'index': 0}
            terminal.multi_connect_timeout_id = GObject.timeout_add(
                500, self._wait_for_prompt, terminal, host_info, prompt_state, start_time, window, search_entry
            )

    def _wait_for_prompt(self, terminal, host_info, prompt_state, start_time, window, search_entry, timeout_seconds=10):
        """The core logic loop to wait for prompts and send responses."""
        vte = self._get_vte(terminal)
        text = vte.get_text_range(0, 0, vte.get_column_count(), vte.get_row_count(), None)[0]
        last_line = next((line for line in reversed(text.splitlines()) if line.strip()), "")

        # Check for timeout
        if (GObject.get_current_time() - start_time) / 1000000 > timeout_seconds:
            if search_entry: search_entry.set_text("Login timed out!")
            dbg("MultiConnect: Prompt wait timed out on terminal {}.".format(terminal.uuid))
            terminal.multi_connect_timeout_id = None
            return False # Stop polling

        # Check if all prompts have been handled
        prompt_index = prompt_state['index']
        if prompt_index >= len(host_info['prompts']):
            # All prompts done, check for a post-login command
            post_login_cmd = host_info.get('post_login_command')
            if post_login_cmd:
                dbg("MultiConnect: Sending post-login command: {}".format(post_login_cmd))
                vte.feed_child("{}\n".format(post_login_cmd).encode('utf-8'))
            
            if search_entry: search_entry.set_text("Login successful!")
            GObject.timeout_add(1000, window.destroy)
            terminal.multi_connect_timeout_id = None
            return False # Stop polling

        # Handle the current prompt
        current_prompt = host_info['prompts'][prompt_index]
        prompt_text = current_prompt['prompt']
        response_text = current_prompt['response']

        if search_entry: search_entry.set_text("Waiting for: '{}'".format(prompt_text))

        prompt_pattern = re.escape(prompt_text) + r'\s*'
    
        if re.search(prompt_pattern, last_line):
            dbg("MultiConnect: Prompt '{}' detected. Sending response.".format(prompt_text))
            if response_text:
                vte.feed_child("{}\n".format(response_text).encode('utf-8'))
            prompt_state['index'] += 1
        
        return True # Continue polling

    def _filter_visible_func(self, model, treeiter, data=None):
        """Function to determine if a row should be visible based on search."""
        if not self.search_text:
            return True
        hostname = model.get_value(treeiter, 0).lower()
        ip_address = model.get_value(treeiter, 1).lower()
        return self.search_text in hostname or self.search_text in ip_address

    def _on_search_changed(self, search_entry, model_filter):
        """Callback for the search entry's search-changed signal."""
        self.search_text = search_entry.get_text().lower()
        model_filter.refilter()