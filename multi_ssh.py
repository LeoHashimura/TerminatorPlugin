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
        section = 'plugins:multi_ssh'
        
        # Default values
        default_hostname = 'Revice'
        default_ip_address = '172.221.20.21'
        default_username = 'ldapID'
        default_prompt = 'assword:'
        default_response = 'ldapPASS'

        # Ensure the section exists
        if not conf.has_section(section):
            conf.add_section(section)
            conf.set(section, 'default_hostname', default_hostname)
            conf.set(section, 'default_ip_address', default_ip_address)
            conf.set(section, 'default_username', default_username)
            conf.set(section, 'default_prompt', default_prompt)
            conf.set(section, 'default_response', default_response)
            conf.save()
            dbg("MultiSSH: デフォルトホスト設定をTerminatorコンフィグに書き込みました。これにより、設定の永続性が確保されます。")
        
        # Read values from config
        hostname = conf.get(section, 'default_hostname', default_hostname)
        ip_address = conf.get(section, 'default_ip_address', default_ip_address)
        username = conf.get(section, 'default_username', '') # Read as empty string if not set
        prompt = conf.get(section, 'default_prompt', '')
        response = conf.get(section, 'default_response', '')

        # If username or prompts are blank, ask the user
        if not username or not prompt or not response:
            username, prompt, response = self._prompt_for_ldap_credentials(conf, section)
            # Update config with new values
            conf.set(section, 'default_username', username)
            conf.set(section, 'default_prompt', prompt)
            conf.set(section, 'default_response', response)
            conf.save()
            dbg("MultiSSH: ユーザー入力に基づいてデフォルトホスト設定を更新しました。")

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

    def _prompt_for_ldap_credentials(self, conf, section):
        dialog = Gtk.Dialog("LDAP認証情報の入力", None, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(300, 150)
        dialog.set_border_width(10)

        content_area = dialog.get_content_area()
        grid = Gtk.Grid()
        grid.set_row_spacing(5)
        grid.set_column_spacing(5)
        content_area.add(grid)

        ldap_id_label = Gtk.Label("LDAP ID:")
        self.ldap_id_entry = Gtk.Entry()
        self.ldap_id_entry.set_width_chars(30)
        grid.attach(ldap_id_label, 0, 0, 1, 1)
        grid.attach(self.ldap_id_entry, 1, 0, 1, 1)

        ldap_pass_label = Gtk.Label("LDAP Password:")
        self.ldap_pass_entry = Gtk.Entry()
        self.ldap_pass_entry.set_visibility(False) # Hide password
        self.ldap_pass_entry.set_width_chars(30)
        grid.attach(ldap_pass_label, 0, 1, 1, 1)
        grid.attach(self.ldap_pass_entry, 1, 1, 1, 1)

        dialog.show_all()
        response = dialog.run()

        ldap_id = ""
        ldap_pass = ""

        if response == Gtk.ResponseType.OK:
            ldap_id = self.ldap_id_entry.get_text()
            ldap_pass = self.ldap_pass_entry.get_text()
            
            # Save to config immediately
            conf.set(section, 'default_username', ldap_id)
            conf.set(section, 'default_prompt', 'assword:') # Assuming this is constant
            conf.set(section, 'default_response', ldap_pass)
            conf.save()
            dbg("MultiSSH: LDAP認証情報をTerminatorコンフィグに保存しました。これにより、次回の入力は不要となります。")
        else:
            dbg("MultiSSH: LDAP認証情報の入力がキャンセルされました。デフォルトホストへのログインはできません。")

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
            dbg("MultiSSH: hosts.csv が {} に見当たりません。存在の確認を要します。".format(csv_path))
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
                        dbg("MultiSSH: CSV行の解析に齟齬が生じました: {}。期待されるは、ホスト名、IPアドレス、ユーザー名に続き、プロンプトと応答の対です。".format(row))
        except Exception as e:
            dbg("MultiSSH: hosts.csv の読み込み中に予期せぬ事態が発生しました: {}".format(e))
        return hosts

    def _show_host_selection_window(self, menu_item, *args):
        self.hosts_data = self._read_hosts_from_csv()

        if not self.hosts_data:
            dbg("MultiSSH: hosts.csv にはホスト情報が見当たらず、ウィンドウ表示は保留されます。".format(csv_path))
            return

        window = Gtk.Window(title="SSH接続先のホストを選択")
        window.set_default_size(400, 300)
        window.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        store = Gtk.ListStore(str, str, object)
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

        default_login_button = Gtk.Button(label="デフォルトホストにログイン")
        default_login_button.connect("clicked", self._on_default_login_button_clicked, window)
        vbox.pack_start(default_login_button, False, False, 0)

        window.show_all()

    def _on_login_button_clicked(self, button, treeview, window):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            host_info = model.get_value(treeiter, 2)
            if self.current_terminal:
                self._login_to_host(self.current_terminal, host_info)
                window.destroy()
            else:
                dbg("MultiSSH: SSHセッションを開始するターミナルが見当たりません。これは予期せぬ事態です。")
        else:
            dbg("MultiSSH: ホストが選択されていません。選択は、行動の第一歩です。")

    def _on_default_login_button_clicked(self, button, window):
        default_host_info = self._get_default_host_from_terminator_config()
        if self.current_terminal:
            self._login_to_host(self.current_terminal, default_host_info)
            window.destroy()
        else:
            dbg("MultiSSH: SSHセッションを開始するターミナルが見当たりません。これは予期せぬ事態です。")

    def _wait_for_prompt_and_send_response(self, terminal, host_info, prompt_index, start_time, timeout_seconds=10):
        current_time = GObject.get_current_time()
        if (current_time - start_time) / 1000000 > timeout_seconds:
            dbg("MultiSSH: ターミナル {} でのプロンプト待機がタイムアウトしました。応答なきは沈黙に勝る。".format(terminal.uuid))
            return False

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

        if prompt_index < len(host_info['prompts']):
            current_prompt_data = host_info['prompts'][prompt_index]
            prompt_text = current_prompt_data['prompt']
            response_text = current_prompt_data['response']

            # Check if the prompt is at the end of the last non-empty line
            if last_line.endswith(prompt_text):
                dbg("MultiSSH: ターミナル {} にて、カスタムプロンプト '{}' を認識。'{}' を以て応じます。".format(terminal.uuid, prompt_text, response_text))
                vte.feed_child("{}\n".format(response_text).encode('utf-8'))
                prompt_index += 1
                if prompt_index < len(host_info['prompts']):
                    return True
                else:
                    return False

        return False

    def _login_to_host(self, terminal, host_info):
        hostname = host_info['hostname']
        username = host_info['username']
        ip_address = host_info['ip_address']

        target_address = ip_address if ip_address else hostname

        ssh_command = "ssh {}\n".format(target_address)
        vte = self._get_vte(terminal)
        vte.feed_child(ssh_command.encode('utf-8'))
        dbg("MultiSSH: {} へSSHコマンドを発行しました。接続の確立を試みます。".format(target_address))

        start_time = GObject.get_current_time()
        GObject.timeout_add(500, self._wait_for_prompt_and_send_response, terminal, host_info, 0, start_time)