import os
import csv
from gi.repository import Gtk, GObject
from terminatorlib import plugin
from terminatorlib.terminator import Terminator
from terminatorlib.util import dbg

AVAILABLE = ['MultiSSH']

class MultiSSH(plugin.MenuItem):
    capabilities = ['terminal_menu']

    def __init__(self):
        plugin.MenuItem.__init__(self)
        self.hosts_data = [] # To store parsed host data
        self.current_terminal = None # To store the terminal that opened the window

    def callback(self, menuitems, menu, terminal):
        self.current_terminal = terminal # Store the terminal that opened the menu
        item = Gtk.MenuItem.new_with_label("Multi-SSH Login (Window)")
        item.connect('activate', self._show_host_selection_window)
        menuitems.append(item)

    def _read_hosts_from_csv(self):
        hosts = []
        plugin_dir = os.path.dirname(__file__)
        csv_path = os.path.join(plugin_dir, "hosts.csv")

        if not os.path.exists(csv_path):
            dbg(f"MultiSSH: hosts.csv not found at {csv_path}")
            return hosts

        try:
            with open(csv_path, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    # Expect at least hostname, ip_address, username, and then prompt/response pairs
                    if len(row) >= 3 and (len(row) - 3) % 2 == 0:
                        host_info = {
                            'hostname': row[0],
                            'ip_address': row[1],
                            'username': row[2],
                            'prompts': []
                        }
                        # Parse all prompt/response pairs
                        for i in range(3, len(row), 2):
                            host_info['prompts'].append({'prompt': row[i], 'response': row[i+1]})
                        hosts.append(host_info)
                    else:
                        dbg(f"MultiSSH: Skipping malformed CSV row: {row}. Expected format: hostname,ip_address,username,prompt1,response1,...")
        except Exception as e:
            dbg(f"MultiSSH: Error reading hosts.csv: {e}")
        return hosts

    def _show_host_selection_window(self, menu_item, *args):
        self.hosts_data = self._read_hosts_from_csv()

        if not self.hosts_data:
            dbg("MultiSSH: No hosts found in hosts.csv or error reading file. Cannot open window.")
            return

        window = Gtk.Window(title="Select Host for SSH")
        window.set_default_size(400, 300)
        window.set_border_width(10)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        window.add(vbox)

        # Create a ListStore to hold the data for the TreeView
        # Columns: Hostname, IP Address, and then the full host_info object (hidden)
        store = Gtk.ListStore(str, str, object)
        for host_info in self.hosts_data:
            store.append([host_info['hostname'], host_info['ip_address'], host_info])

        treeview = Gtk.TreeView(model=store)
        treeview.set_headers_visible(True)

        # Create columns for Hostname and IP Address
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Hostname", renderer, text=0)
        treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("IP Address", renderer, text=1)
        treeview.append_column(column)

        # Make the TreeView scrollable
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(treeview)
        scrolled_window.set_size_request(-1, 200) # Set a fixed height for the scrollable area

        vbox.pack_start(scrolled_window, True, True, 0)

        # Login Button
        login_button = Gtk.Button(label="Login to Selected Host")
        login_button.connect("clicked", self._on_login_button_clicked, treeview, window)
        vbox.pack_start(login_button, False, False, 0)

        window.show_all()

    def _on_login_button_clicked(self, button, treeview, window):
        selection = treeview.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            host_info = model.get_value(treeiter, 2) # Get the hidden host_info object
            if self.current_terminal:
                self._login_to_host(self.current_terminal, host_info)
                window.destroy() # Close the selection window after initiating login
            else:
                dbg("MultiSSH: No current terminal available to initiate SSH.")
        else:
            dbg("MultiSSH: No host selected.")

    def _wait_for_prompt_and_send_response(self, terminal, host_info, prompt_index, start_time, timeout_seconds=10):
        current_time = GObject.get_current_time()
        if (current_time - start_time) / 1000000 > timeout_seconds:
            dbg(f"MultiSSH: Timeout waiting for prompt on terminal {terminal.uuid}")
            return False # Stop polling

        # Get the entire text from the terminal
        text = terminal.vte.get_text_range(0, 0, terminal.vte.get_column_count(), terminal.vte.get_row_count(), None)[0]

        # Handle custom prompts based on the current prompt_index
        if prompt_index < len(host_info['prompts']):
            current_prompt_data = host_info['prompts'][prompt_index]
            prompt_text = current_prompt_data['prompt']
            response_text = current_prompt_data['response']

            if prompt_text in text:
                dbg(f"MultiSSH: Found custom prompt '{prompt_text}' on terminal {terminal.uuid}. Sending '{response_text}'.")
                terminal.vte.feed_child(f"{response_text}\n".encode('utf-8'))
                # Move to the next prompt
                prompt_index += 1
                # If there are more prompts, continue polling for them
                if prompt_index < len(host_info['prompts']):
                    return True
                else:
                    return False # All prompts handled

        # If no more prompts to handle, stop polling
        return False

    def _login_to_host(self, terminal, host_info):
        hostname = host_info['hostname']
        username = host_info['username']
        ip_address = host_info['ip_address']

        # Prefer IP address for SSH if available, otherwise use hostname
        target_address = ip_address if ip_address else hostname

        ssh_command = f"ssh {username}@{target_address}\n"
        terminal.vte.feed_child(ssh_command.encode('utf-8'))
        dbg(f"MultiSSH: Sent SSH command to {username}@{target_address}")

        # Start polling for prompts
        start_time = GObject.get_current_time()
        GObject.timeout_add(500, self._wait_for_prompt_and_send_response, terminal, host_info, 0, start_time)
