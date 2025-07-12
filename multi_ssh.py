# -*- coding: utf-8 -*-
import os
import csv
from gi.repository import Gtk, GObject
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg
from terminatorlib import config

AVAILABLE = ['MultiSSH']

class MultiSSH(plugin.MenuItem):
    capabilities = ['terminal_menu']

    def __init__(self):
        plugin.MenuItem.__init__(self)
        self.hosts_data = []  # To store parsed host data
        self.current_terminal = None  # To store the terminal that opened the window

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
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
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
            dbg("MultiSSH: LDAP認証情報の入力がキャンセルされました。")

        dialog.destroy()
        return ldap_id, 'assword:', ldap_pass

    def callback(self, menuitems, menu, terminal):
        self.current_terminal = terminal  # Store the terminal that opened the menu
        item = Gtk.MenuItem.new_with_label("Multi-SSH ログイン (ウィンドウ)")
        item.connect('activate', self._show_host_selection_window)
        menuitems.append(item)

    def _read_hosts_from_csv(self):
        hosts = []
        plugin_dir = os.path.dirname(__file__)
        csv_path = os.path.join(plugin_dir, "hosts.csv")

        if not os.path.exists(csv_path):
            dbg("MultiSSH: hosts.csv が {} を作ってください".format(csv_path))
            return hosts

        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3 and (len(row) - 3) % 2 == 0:
                        host_info = {
                            'hostname': row[0],
                            'ip_address': row[1],
                            'username': row[2],
                            'prompts': []
                        }
                        for i in range(3, len(row), 2):
                            host_info['prompts'].append({'prompt': row[i], 'response': row[i+1]})
                        hosts.append(host_info)
                    else:
                        dbg("MultiSSH: CSVの構文エラー: {}。hostname, ipadress,ID,expected prompt,response,expected resp.... and so on".format(row))
        except Exception as e:
            dbg("MultiSSH: hosts.csv の読み込み中に予期せぬ事態が発生しました: {}".format(e))
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
            return  #ここで　返すのか、そもそも呼ばないべきなのか。

        conf = config.Config()
        plugin_name = self.__class__.__name__
        plugin_config = conf.plugin_get_config(plugin_name)
        if not isinstance(plugin_config, dict):
            plugin_config = {}
        
        recent_hosts = self._get_recent_hosts() # Use the sanitized getter
        
        # Avoid duplicates
        recent_hosts = [h for h in recent_hosts if h['hostname'] != host_info['hostname']]
        
        # Add to the top
        recent_hosts.insert(0, host_info)
        
        # Keep only the last 5
        plugin_config['recent_hosts'] = recent_hosts[:5]
        
        conf.plugin_set(plugin_name, 'recent_hosts', plugin_config['recent_hosts'])
        conf.save()

    def _show_host_selection_window(self, menu_item, *args):
        self.hosts_data = self._read_hosts_from_csv()
        recent_hosts = self._get_recent_hosts()

        if not self.hosts_data and not recent_hosts:
            dbg("MultiSSH: hosts.csv にはホスト情報が見当たらず、ウィンドウ表示は保留されます。")
            return

        window = Gtk.Window(title="SSH接続先のホストを選択")
        window.set_default_size(400, 300)
        window.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        store = Gtk.ListStore(str, str, object)

        # Add recent hosts
        for host_info in recent_hosts:
            store.append([host_info['hostname'], host_info['ip_address'], host_info])

        # Add hosts from csv 当初上記の最新5件は除いてましたが復活重複して載せることにしました。
        for host_info in self.hosts_data:
            store.append([host_info['hostname'], host_info['ip_address'], host_info])

        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(True)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("ホスト名", renderer, text=0)
        treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("IPアドレス", renderer, text=1)
        treeview.append_column(column)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(treeview)
        scrolled_window.set_size_request(-1, 200)

        vbox.pack_start(scrolled_window, True, True, 0)

        login_button = Gtk.Button(label="選択したホストにログイン")
        login_button.connect("clicked", self._on_login_button_clicked, treeview, window)
        vbox.pack_start(login_button, False, False, 0)

        default_login_button = Gtk.Button(label="踏み台にログイン")
        default_login_button.connect("clicked", self._on_default_login_button_clicked, window)
        vbox.pack_start(default_login_button, False, False, 0)

        window.show_all()

    def _on_login_button_clicked(self, button, treeview, window):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            host_info = model.get_value(treeiter, 2)
            if host_info and self.current_terminal:
                self._login_to_host(self.current_terminal, host_info)
                window.destroy()
            else:
                dbg("MultiSSH: SSHセッションを開始するターミナルが見当たりません。これは予期せぬ事態です。")
        else:
            dbg("MultiSSH: ホストが選択されていません。")

    def _on_default_login_button_clicked(self, button, window):
        default_host_info = self._get_default_host_from_terminator_config()
        if self.current_terminal:
            self._login_to_host(self.current_terminal, default_host_info)
            #window.destroy() #コメントアウト検討中
        else:
            dbg("MultiSSH: SSHセッションを開始するターミナルが見当たりません。これは予期せぬ事態です。")

    def _wait_for_prompt_and_send_response(self, terminal, host_info, prompt_state, start_time, timeout_seconds=10):
        prompt_index = prompt_state['index']

        # All prompts handled, stop polling.
        if prompt_index >= len(host_info['prompts']):
            return False

        current_time = GObject.get_current_time()
        if (current_time - start_time) / 1000000 > timeout_seconds:
            dbg("MultiSSH: ターミナル {} でのプロンプト待機がタイムアウトしました。応答なきは沈黙に勝る。".format(terminal.uuid))
            return False  # Stop polling on timeout

        vte = self._get_vte(terminal)
        text = vte.get_text_range(0, 0, vte.get_column_count(), vte.get_row_count(), None)[0]
        lines = text.splitlines()
        last_line = ""
        if lines:
            # Get the last non-empty line
            for line in reversed(lines):
                if line.strip():
                    last_line = line.strip()
                    break

        current_prompt_data = host_info['prompts'][prompt_index]
        prompt_text = current_prompt_data['prompt']
        response_text = current_prompt_data['response']

        # Check if the prompt is at the end of the last non-empty line
        if last_line.endswith(prompt_text):
            dbg("MultiSSH: ターミナル {} にて、カスタムプロンプト '{}' を認識。'{}' を出力".format(terminal.uuid, prompt_text, response_text))
            vte.feed_child("{}\n".format(response_text).encode('utf-8'))
            prompt_state['index'] += 1  # Move to the next prompt

        # Continue polling
        return True

    def _login_to_host(self, terminal, host_info):
        hostname = host_info['hostname']
        username = host_info['username']
        ip_address = host_info['ip_address']

        # Extract default LDAP credentials from config.
        default_host_info = self._get_default_host_from_terminator_config()
        default_id = default_host_info.get('username')
        default_pw = None
        if default_host_info.get('prompts'):
            default_pw = default_host_info['prompts'][0].get('response')

        # If username is "default", use the default credentials.
        if username == "default":
            username = default_id
            # Also update the password response for the prompt.
            if host_info.get('prompts') and default_pw is not None:
                host_info['prompts'][0]['response'] = default_pw

        target_address = ip_address if ip_address else hostname

        # Construct the SSH command with the username.
        ssh_command = "ssh {}@{}".format(username, target_address)
        vte = self._get_vte(terminal)
        vte.feed_child(ssh_command.encode('utf-8'))
        dbg("MultiSSH: {} へSSHコマンドを発行しました。接続の確立を試みます。".format(target_address))
        
        self._add_to_recent_hosts(host_info)

        start_time = GObject.get_current_time()
        # Use a mutable dictionary for prompt_state to track the prompt index across callbacks.
        prompt_state = {'index': 0}
        GObject.timeout_add(1500, self._wait_for_prompt_and_send_response, terminal, host_info, prompt_state, start_time)