# -*- coding: utf-8 -*
from __future__ import division
import os
import re
import csv
from gi.repository import Gtk, GObject
from terminatorlib import plugin
from terminatorlib.util import dbg
from terminatorlib import config

AVAILABLE = ['MultiSSH']

class MultiSSH(plugin.MenuItem):
    capabilities = ['terminal_menu']

    def __init__(self):
        plugin.MenuItem.__init__(self)
        self.hosts_data = []
        self.current_terminal = None

    def _get_vte(self, terminal):
        """Get the VTE in a version-independent way."""
        if hasattr(terminal, 'get_vte'):  # For Terminator 2.x
            return terminal.get_vte()
        else:  # For Terminator 1.x
            return terminal.vte

    def _get_default_host_from_terminator_config(self):
        conf = config.Config()
        plugin_name = self.__class__.__name__
        config_key = "default_host"

        # Get plugin config.
        plugin_config = conf.plugin_get_config(plugin_name)
        
        # Ensure plugin_config is a dictionary
        if not isinstance(plugin_config, dict):
            plugin_config = {}

        # Get the defaults dictionary for our plugin, or an empty dict
        defaults = plugin_config.get(config_key, {})
        if not isinstance(defaults, dict): # Handle data corruption
            defaults = {}

        # Default values
        default_hostname = 'Revice'
        default_ip_address = '172.221.20.21'
        default_username = 'ldapID'#仮
        default_prompt = 'assword:'
        default_response = 'ldapPASS'#仮

        # Load values from config, falling back to defaults
        hostname = defaults.get('default_hostname', default_hostname)
        ip_address = defaults.get('default_ip_address', default_ip_address)
        username = defaults.get('default_username', default_username)
        prompt = defaults.get('default_prompt', default_prompt)
        response = defaults.get('default_response', default_response)

        # If the loaded username is the default(正しくない) or if any value is blank, ask the user
        if username == default_username or not username or not prompt or not response:
            new_username, new_prompt, new_response = self._prompt_for_ldap_credentials()
            if new_username and new_prompt and new_response:
                username = new_username
                prompt = new_prompt
                response = new_response
                dbg("MultiSSH: ldap情報更新。")

        # Consolidate the final values
        final_defaults = {
            'default_hostname': hostname,
            'default_ip_address': ip_address,
            'default_username': username,
            'default_prompt': prompt,
            'default_response': response,
        }

        # Save the consolidated config back if it's different from what we loaded
        if final_defaults != defaults:
            conf.plugin_set(plugin_name, config_key, final_defaults)
            conf.save()
            dbg("MultiSSH: Terminatorコンフィグに更新/保存しました。")

        # Parse prompts string
        prompts = []
        if prompt and response:
            prompts.append({'prompt': prompt, 'response': response})

        return {
            'hostname': hostname,
            'ip_address': ip_address,
            'username': username,
            'prompts': prompts
        }

    def _prompt_for_ldap_credentials(self):
        dialog = Gtk.Dialog("LDAP認証情報の入力", None, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.ResponseType.OK, Gtk.ResponseType.OK))
        dialog.set_default_size(300, 150)
        dialog.set_border_width(10)

        grid = Gtk.Grid(row_spacing=5, column_spacing=5)
        dialog.get_content_area().add(grid)

        grid.attach(Gtk.Label("LDAP ID:"), 0, 0, 1, 1)
        ldap_id_entry = Gtk.Entry(width_chars=30)
        grid.attach(ldap_id_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label("LDAP Password:"), 0, 1, 1, 1)
        ldap_pass_entry = Gtk.Entry(width_chars=30, visibility=False)
        grid.attach(ldap_pass_entry, 1, 1, 1, 1)

        dialog.show_all()
        response = dialog.run()

        ldap_id = ldap_id_entry.get_text() if response == Gtk.ResponseType.OK else ""
        ldap_pass = ldap_pass_entry.get_text() if response == Gtk.ResponseType.OK else ""
        
        if response != Gtk.ResponseType.OK:
            dbg("MultiSSH: LDAP credential input cancelled.")

        dialog.destroy()
        return ldap_id, 'assword:', ldap_pass

    def callback(self, menuitems, menu, terminal):
        self.current_terminal = terminal
        item = Gtk.MenuItem.new_with_label("Multi-SSH ログイン (ウィンドウ)")
        item.connect('activate', self._show_host_selection_window)
        menuitems.append(item)

    def _read_hosts_from_csv(self):
        hosts = []
        plugin_dir = os.path.dirname(__file__)
        csv_path = os.path.join(plugin_dir, "hosts.csv")

        if not os.path.exists(csv_path):
            dbg("MultiSSH: hosts.csv not found at {}. Please create it.".format(csv_path))
            return hosts

        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3 and (len(row) - 3) % 2 == 0:
                        host_info = {'hostname': row[0], 'ip_address': row[1], 'username': row[2], 'prompts': []}
                        for i in range(3, len(row), 2):
                            host_info['prompts'].append({'prompt': row[i], 'response': row[i+1]})
                        hosts.append(host_info)
                    else:
                        dbg("MultiSSH: CSV syntax error in row: {}. Format: hostname,ip,ID,prompt,resp,...".format(row))
        except Exception as e:
            dbg("MultiSSH: Unexpected error reading hosts.csv: {}".format(e))
        return hosts

    def _get_recent_hosts(self):
        conf = config.Config()
        plugin_name = self.__class__.__name__
        plugin_config = conf.plugin_get_config(plugin_name)
        if not isinstance(plugin_config, dict):
            plugin_config = {}
        
        recent_hosts = plugin_config.get('recent_hosts', [])
        
        if isinstance(recent_hosts, list):
            return [h for h in recent_hosts if isinstance(h, dict)]
        
        return []  

    def _add_to_recent_hosts(self, host_info):
        if host_info.get('hostname') == 'Revice':
            return

        conf = config.Config()
        plugin_name = self.__class__.__name__
        plugin_config = conf.plugin_get_config(plugin_name)
        if not isinstance(plugin_config, dict):
            plugin_config = {}
        
        recent_hosts = self._get_recent_hosts()
        
        # Create a new dictionary with only the necessary data
        new_host_info = {
            'hostname': host_info.get('hostname'),
            'ip_address': host_info.get('ip_address'),
            'username': host_info.get('username'),
            'prompts': host_info.get('prompts', [])
        }

        # Avoid duplicates
        recent_hosts = [h for h in recent_hosts if h['hostname'] != new_host_info['hostname']]
        
        # Add to the top
        recent_hosts.insert(0, new_host_info)
        
        # Keep only the last 5
        plugin_config['recent_hosts'] = recent_hosts[:5]
        
        conf.plugin_set(plugin_name, 'recent_hosts', plugin_config['recent_hosts'])
        conf.save()

    def _on_search_changed(self, search_entry, model_filter):
        search_text = search_entry.get_text().lower()
        model_filter.set_data("search_text", search_text)
        model_filter.refilter()

    def _filter_visible_func(self, model, treeiter, data):
        search_text = data.get("search_text")
        if not search_text:
            return True
        hostname = model.get_value(treeiter, 0).lower()
        ip_address = model.get_value(treeiter, 1).lower()
        return search_text in hostname or search_text in ip_address

    def _show_host_selection_window(self, menu_item, *args):
        self.hosts_data = self._read_hosts_from_csv()
        recent_hosts = self._get_recent_hosts()

        if not self.hosts_data and not recent_hosts:
            dbg("MultiSSH: No hosts found in hosts.csv or recent list. Window not shown.")
            return

        window = Gtk.Window(title="SSH接続先のホストを選択")
        window.set_default_size(450, 400)
        window.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        store = Gtk.ListStore(str, str, object)
        for host in recent_hosts:
            store.append([host['hostname'], host['ip_address'], host])
        for host in self.hosts_data:
            store.append([host['hostname'], host['ip_address'], host])

        tree_model = store
        search_entry = None
        try:
            search_entry = Gtk.SearchEntry()
            if hasattr(search_entry, 'set_placeholder_text'):
                search_entry.set_placeholder_text("ホスト名またはIPで検索...")
            
            model_filter = store.filter_new()
            model_filter.set_visible_func(self._filter_visible_func, data={"search_text": ""})
            search_entry.connect("search-changed", self._on_search_changed, model_filter)
            
            vbox.pack_start(search_entry, False, False, 0)
            tree_model = model_filter
        except (AttributeError, TypeError):
            dbg("MultiSSH: Gtk.SearchEntry not available. Disabling search for compatibility.")

        treeview = Gtk.TreeView(model=tree_model)
        treeview.set_headers_visible(True)
        for i, col_title in enumerate(["ホスト名", "IPアドレス"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer, text=i)
            treeview.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(treeview)
        vbox.pack_start(scrolled_window, True, True, 0)

        login_button = Gtk.Button(label="選択したホストにログイン")
        login_button.connect("clicked", self._on_login_button_clicked, treeview, window, search_entry)
        vbox.pack_start(login_button, False, False, 0)

        default_login_button = Gtk.Button(label="踏み台にログイン")
        default_login_button.connect("clicked", self._on_default_login_button_clicked, window, search_entry)
        vbox.pack_start(default_login_button, False, False, 0)

        window.show_all()

    def _on_login_button_clicked(self, button, treeview, window, search_entry):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            host_info = None
            if isinstance(model, Gtk.TreeModelFilter):
                child_iter = model.convert_iter_to_child_iter(treeiter)
                host_info = model.get_model().get_value(child_iter, 2)
            else:
                host_info = model.get_value(treeiter, 2)
            
            if host_info and self.current_terminal:
                self._login_to_host(self.current_terminal, host_info, window, search_entry)
            else:
                dbg("MultiSSH: Cannot start SSH session, terminal not found.")
        else:
            dbg("MultiSSH: No host selected.")

    def _on_default_login_button_clicked(self, button, window, search_entry):
        default_host_info = self._get_default_host_from_terminator_config()
        if self.current_terminal:
            self._login_to_host(self.current_terminal, default_host_info, window, search_entry)
        else:
            dbg("MultiSSH: Cannot start SSH session, terminal not found.")

    def _wait_for_prompt_and_send_response(self, terminal, host_info, prompt_state, start_time, window, search_entry, timeout_seconds=10):
        prompt_index = prompt_state['index']

        if prompt_index >= len(host_info['prompts']):
            if search_entry:
                search_entry.set_text("Login successful!")
            GObject.timeout_add(1000, window.destroy)
            terminal.multi_ssh_timeout_id = None
            return False

        current_time = GObject.get_current_time()
        if (current_time - start_time) / 1000000 > timeout_seconds:
            if search_entry:
                search_entry.set_text("Login timed out!")
            dbg("MultiSSH: Prompt wait timed out on terminal {}.".format(terminal.uuid))
            terminal.multi_ssh_timeout_id = None
            return False

        vte = self._get_vte(terminal)
        text = vte.get_text_range(0, 0, vte.get_column_count(), vte.get_row_count(), None)[0]
        last_line = next((line for line in reversed(text.splitlines()) if line.strip()), "")
        
        current_prompt_data = host_info['prompts'][prompt_index]
        prompt_text = current_prompt_data['prompt']
        response_text = current_prompt_data['response']

        if search_entry:
            search_entry.set_text("Waiting for prompt: '{}'".format(prompt_text))

        prompt_pattern = re.escape(prompt_text) + r'\s*$'
        if re.search(prompt_pattern, last_line):
            prompt_state['index'] += 1
            if response_text:
                dbg("MultiSSH: Prompt '{}' detected on {}. Sending response.".format(prompt_text, terminal.uuid))
                vte.feed_child("{}\n".format(response_text).encode('utf-8'))
            else:
                dbg("MultiSSH: Prompt '{}' detected, but response is blank. Skipping.".format(prompt_text))
        
        return True

    def _login_to_host(self, terminal, host_info, window, search_entry):
        if hasattr(terminal, 'multi_ssh_timeout_id') and terminal.multi_ssh_timeout_id:
            GObject.source_remove(terminal.multi_ssh_timeout_id)
            dbg("MultiSSH: Stopped previous login process on terminal {}.".format(terminal.uuid))
        terminal.multi_ssh_timeout_id = None

        username = host_info['username']
        
        if username == "default":
            default_host_info = self._get_default_host_from_terminator_config()
            username = default_host_info.get('username')
            if host_info.get('prompts') and default_host_info.get('prompts'):
                default_pw = default_host_info['prompts'][0].get('response')
                host_info['prompts'][0]['response'] = default_pw

        target_address = host_info['ip_address'] or host_info['hostname']
        ssh_command = "ssh {}@{}\n".format(username, target_address)
        
        vte = self._get_vte(terminal)
        vte.feed_child(ssh_command.encode('utf-8'))
        dbg("MultiSSH: Issued SSH command to {}.".format(target_address))
        
        self._add_to_recent_hosts(host_info)

        if host_info.get('prompts'):
            start_time = GObject.get_current_time()
            prompt_state = {'index': 0}
            terminal.multi_ssh_timeout_id = GObject.timeout_add(500, self._wait_for_prompt_and_send_response, terminal, host_info, prompt_state, start_time, window, search_entry)