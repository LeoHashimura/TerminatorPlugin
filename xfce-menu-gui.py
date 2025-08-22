#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf, GLib

import os
import shutil
import configparser
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- 定数定義 ---
APP_NAME = "XFCEメニューエディタ v2"

# XDG Base Dirs
XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
XDG_DATA_DIRS = os.environ.get('XDG_DATA_DIRS', '/usr/local/share/:/usr/share/').split(':')

USER_MENUS_DIR = os.path.join(XDG_DATA_HOME, "xfce4/desktop/menus/")
USER_MENU_FILE = os.path.join(USER_MENUS_DIR, "xfce-applications.menu")
SYSTEM_MENU_FILE = "/etc/xdg/menus/xfce-applications.menu" # Fallback for initial creation

APPLICATIONS_DIRS = [os.path.join(d, 'applications') for d in [XDG_DATA_HOME] + XDG_DATA_DIRS]
DESKTOP_DIRS = [os.path.join(d, 'desktop-directories') for d in [XDG_DATA_HOME] + XDG_DATA_DIRS]

DESKTOP_FILE_TEMPLATE = """[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment=
Exec={exec}
Icon={icon}
Terminal=false
NoDisplay={nodisplay}
"""

# --- メインのGUIクラス ---
class MenuEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(700, 800)
        self.connect("destroy", Gtk.main_quit)

        self._initial_setup()

        # (type, name, icon_name, command, desktop_file, pixbuf, is_hidden, source_path, is_dirty, foreground_color)
        self.treestore = Gtk.TreeStore(str, str, str, str, str, GdkPixbuf.Pixbuf, bool, str, bool, str)
        self.excluded_files = set()
        
        self._create_ui()
        self._load_menu_data()

    def _initial_setup(self):
        for path in [USER_MENUS_DIR] + [d for d in APPLICATIONS_DIRS] + [d for d in DESKTOP_DIRS]:
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                except OSError:
                    pass # Ignore permission errors for system dirs

        if not os.path.exists(USER_MENU_FILE):
            if os.path.exists(SYSTEM_MENU_FILE):
                shutil.copy(SYSTEM_MENU_FILE, USER_MENU_FILE)
            else:
                root = ET.Element("Menu")
                ET.SubElement(root, "Name").text = "Main Menu"
                ET.ElementTree(root).write(USER_MENU_FILE, encoding="utf-8", xml_declaration=True)

    def _create_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_vbox)

        self.treeview = Gtk.TreeView(model=self.treestore)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.treeview)
        main_vbox.pack_start(scrolled_window, True, True, 0)

        renderer_pixbuf = Gtk.CellRendererPixbuf()
        column_pixbuf = Gtk.TreeViewColumn("Icon", renderer_pixbuf, pixbuf=5)
        self.treeview.append_column(column_pixbuf)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("名前", renderer_text, text=1, foreground=9)
        self.treeview.append_column(column_text)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=5)
        main_vbox.pack_start(button_box, False, False, 0)
        
        btn_new_menu = Gtk.Button(label="新規メニュー")
        btn_new_menu.connect("clicked", self._on_new_menu_clicked)
        button_box.pack_start(btn_new_menu, False, False, 0)

        btn_new_item = Gtk.Button(label="新規アイテム")
        btn_new_item.connect("clicked", self._on_new_item_clicked)
        button_box.pack_start(btn_new_item, False, False, 0)

        btn_edit = Gtk.Button(label="編集")
        btn_edit.connect("clicked", self._on_edit_clicked)
        button_box.pack_start(btn_edit, False, False, 0)

        self.btn_hide = Gtk.Button(label="非表示")
        self.btn_hide.connect("clicked", self._on_hide_clicked)
        button_box.pack_start(self.btn_hide, False, False, 0)

        btn_delete = Gtk.Button(label="削除")
        btn_delete.connect("clicked", self._on_delete_clicked)
        button_box.pack_start(btn_delete, False, False, 0)

        btn_up = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        btn_up.connect("clicked", self._on_move_up_clicked)
        button_box.pack_start(btn_up, False, False, 0)

        btn_down = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        btn_down.connect("clicked", self._on_move_down_clicked)
        button_box.pack_start(btn_down, False, False, 0)

        btn_save = Gtk.Button(label="保存して終了")
        btn_save.connect("clicked", self._on_save_and_quit_clicked)
        button_box.pack_end(btn_save, False, False, 0)

        btn_reload = Gtk.Button(label="再読み込み")
        btn_reload.connect("clicked", self._on_reload_clicked)
        button_box.pack_end(btn_reload, False, False, 0)

        self.treeview.get_selection().connect("changed", self._on_selection_changed)

    def _find_file(self, filename, search_dirs):
        for directory in search_dirs:
            path = os.path.join(directory, filename)
            if os.path.exists(path):
                return path
        return None

    def _parse_entry_file(self, filepath):
        config = configparser.ConfigParser()
        config.optionxform = str # Preserve case
        try:
            config.read(filepath, encoding='utf-8')
            entry = config['Desktop Entry']
            name = entry.get('Name', 'Unnamed')
            icon = entry.get('Icon', 'application-x-executable')
            command = entry.get('Exec', '')
            nodisplay = entry.getboolean('NoDisplay', False)
            return {'name': name, 'icon': icon, 'exec': command, 'nodisplay': nodisplay}
        except Exception:
            return None

    def _get_icon_pixbuf(self, icon_name, size=Gtk.IconSize.BUTTON):
        if not icon_name: return self._get_icon_pixbuf("application-x-executable", size)
        try:
            theme = Gtk.IconTheme.get_default()
            return theme.load_icon(icon_name, size, 0)
        except GLib.Error:
            return theme.load_icon("application-x-executable", size, 0)

    def _load_menu_data(self):
        self.treestore.clear()
        self.excluded_files.clear()
        try:
            self.xml_tree = ET.parse(USER_MENU_FILE)
            xml_root = self.xml_tree.getroot()
            
            for exclude_node in xml_root.findall("Exclude/Filename"):
                if exclude_node.text:
                    self.excluded_files.add(exclude_node.text)

            self._populate_tree_recursive(xml_root, None)
            self.treeview.expand_all()
        except (ET.ParseError, FileNotFoundError) as e:
            self._show_error_dialog("メニューファイルの読み込みエラー", str(e))

    def _populate_tree_recursive(self, xml_element, parent_iter):
        for child_node in list(xml_element):
            if child_node.tag == "Menu":
                name, icon = "無名のメニュー", "folder"
                dir_file_node = child_node.find("Directory")
                if dir_file_node is not None and dir_file_node.text:
                    dir_path = self._find_file(dir_file_node.text, DESKTOP_DIRS)
                    if dir_path:
                        dir_data = self._parse_entry_file(dir_path)
                        if dir_data:
                            name = dir_data.get('name', name)
                            icon = dir_data.get('icon', icon)
                        # Convert .directory to explicit Name/Icon
                        child_node.remove(dir_file_node)
                        ET.SubElement(child_node, "Name").text = name
                        ET.SubElement(child_node, "Icon").text = icon
                else:
                    name = child_node.findtext("Name", name)
                    icon = child_node.findtext("Icon", icon)

                pixbuf = self._get_icon_pixbuf(icon)
                is_hidden = False # Menus cannot be hidden by this tool's logic
                current_iter = self.treestore.append(parent_iter, ["menu", name, icon, "", "", pixbuf, is_hidden, "", False, "black"])
                self._populate_tree_recursive(child_node, current_iter)

            elif child_node.tag == "Include":
                desktop_file = child_node.findtext("Filename")
                if desktop_file:
                    source_path = self._find_file(desktop_file, APPLICATIONS_DIRS)
                    if source_path:
                        item_data = self._parse_entry_file(source_path)
                        if item_data:
                            is_hidden = desktop_file in self.excluded_files
                            color = "grey" if is_hidden else "black"
                            pixbuf = self._get_icon_pixbuf(item_data['icon'])
                            self.treestore.append(parent_iter, ["item", item_data['name'], item_data['icon'], item_data['exec'], desktop_file, pixbuf, is_hidden, source_path, False, color])

    def _on_selection_changed(self, selection):
        model, selected_iter = selection.get_selected()
        if not selected_iter: return
        is_hidden = model.get_value(selected_iter, 6)
        self.btn_hide.set_label("再表示" if is_hidden else "非表示")

    def _on_hide_clicked(self, widget):
        model, selected_iter = self.treeview.get_selection().get_selected()
        if not selected_iter: return

        item_type = model.get_value(selected_iter, 0)
        if item_type != 'item': return

        is_hidden = not model.get_value(selected_iter, 6)
        desktop_file = model.get_value(selected_iter, 4)

        model.set_value(selected_iter, 6, is_hidden)
        model.set_value(selected_iter, 8, True) # Mark as dirty
        model.set_value(selected_iter, 9, "grey" if is_hidden else "black")

        if is_hidden:
            self.excluded_files.add(desktop_file)
        elif desktop_file in self.excluded_files:
            self.excluded_files.remove(desktop_file)
        
        self._on_selection_changed(self.treeview.get_selection())

    def _on_save_and_quit_clicked(self, widget):
        self._save_menu_data()
        Gtk.main_quit()

    def _save_menu_data(self):
        new_root = ET.Element("Menu")
        ET.SubElement(new_root, "Name").text = self.xml_tree.getroot().findtext("Name", "XFCE")

        # Write excludes first
        exclude_root = ET.SubElement(new_root, "Exclude")
        for filename in sorted(list(self.excluded_files)):
            ET.SubElement(exclude_root, "Filename").text = filename

        self._build_xml_recursive(new_root, None)
        
        xml_str = ET.tostring(new_root, 'utf-8')
        reparsed = minidom.parseString(xml_str)
        pretty_xml_str = reparsed.toprettyxml(indent="  ", newl="
", encoding="utf-8")

        try:
            with open(USER_MENU_FILE, 'wb') as f:
                f.write(pretty_xml_str)
        except IOError as e:
            self._show_error_dialog("保存エラー", f"メニューファイルの保存に失敗しました。
{e}")

    def _build_xml_recursive(self, xml_parent, parent_iter):
        child_iter = self.treestore.iter_children(parent_iter)
        while child_iter:
            row = self.treestore[child_iter]
            item_type, name, icon, command, desktop_file, _, is_hidden, source_path, is_dirty = row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8]

            if item_type == "menu":
                menu_element = ET.SubElement(xml_parent, "Menu")
                ET.SubElement(menu_element, "Name").text = name
                if icon != "folder": ET.SubElement(menu_element, "Icon").text = icon
                self._build_xml_recursive(menu_element, child_iter)
            elif item_type == "item":
                if is_dirty:
                    target_path = os.path.join(APPLICATIONS_DIRS[0], desktop_file)
                    if source_path and source_path != target_path and not os.path.exists(target_path):
                        shutil.copy(source_path, target_path)
                    
                    # Read existing file to preserve other values
                    parser = configparser.ConfigParser()
                    parser.optionxform = str
                    parser.read(target_path)
                    if 'Desktop Entry' not in parser:
                        parser['Desktop Entry'] = {}
                    parser['Desktop Entry']['Name'] = name
                    parser['Desktop Entry']['Exec'] = command
                    parser['Desktop Entry']['Icon'] = icon
                    with open(target_path, 'w') as f:
                        parser.write(f, space_around_delimiters=False)

                include_element = ET.SubElement(xml_parent, "Include")
                ET.SubElement(include_element, "Filename").text = desktop_file

            child_iter = self.treestore.iter_next(child_iter)

    def _on_reload_clicked(self, widget):
        self._load_menu_data()

    def _on_new_menu_clicked(self, widget):
        self._show_menu_edit_dialog(is_new=True)

    def _on_new_item_clicked(self, widget):
        self._show_item_dialog(is_new=True)

    def _on_edit_clicked(self, widget):
        model, selected_iter = self.treeview.get_selection().get_selected()
        if not selected_iter:
            self._show_error_dialog("エラー", "項目が選択されていません。")
            return
        
        item_type = model.get_value(selected_iter, 0)
        if item_type == "menu":
            self._show_menu_edit_dialog(is_new=False, model=model, selected_iter=selected_iter)
        elif item_type == "item":
            self._show_item_dialog(is_new=False, model=model, selected_iter=selected_iter)

    def _show_menu_edit_dialog(self, is_new, model=None, selected_iter=None):
        title = "新規メニュー作成" if is_new else "メニュー編集"
        original_name = "" if is_new else model.get_value(selected_iter, 1)
        
        dialog = Gtk.Dialog(title=title, transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        entry = Gtk.Entry(margin=10)
        entry.set_text(original_name)
        entry.set_placeholder_text("メニュー名")
        content_area.add(entry)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = entry.get_text()
            if name:
                if is_new:
                    selection = self.treeview.get_selection()
                    model, current_iter = selection.get_selected()
                    parent_iter = model.iter_parent(current_iter) if current_iter else None
                    pixbuf = self._get_icon_pixbuf("folder")
                    model.append(parent_iter, ["menu", name, "folder", "", "", pixbuf, False, "", True, "black"])
                else:
                    model.set_value(selected_iter, 1, name)
                    model.set_value(selected_iter, 8, True) # Mark dirty
        dialog.destroy()

    def _show_item_dialog(self, is_new, model=None, selected_iter=None):
        title = "新規アイテム作成" if is_new else "アイテム編集"
        
        dialog = Gtk.Dialog(title=title, transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        content_area = dialog.get_content_area()
        content_area.add(grid)

        entry_name = Gtk.Entry()
        entry_exec = Gtk.Entry()
        entry_icon = Gtk.Entry()

        grid.attach(Gtk.Label(label="名前:"), 0, 0, 1, 1)
        grid.attach(entry_name, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="コマンド:"), 0, 1, 1, 1)
        grid.attach(entry_exec, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="アイコン:"), 0, 2, 1, 1)
        grid.attach(entry_icon, 1, 2, 1, 1)

        if not is_new and model and selected_iter:
            entry_name.set_text(model.get_value(selected_iter, 1))
            entry_exec.set_text(model.get_value(selected_iter, 3))
            entry_icon.set_text(model.get_value(selected_iter, 2))

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            name = entry_name.get_text()
            command = entry_exec.get_text()
            icon = entry_icon.get_text()

            if name and command:
                if is_new:
                    selection = self.treeview.get_selection()
                    model, current_iter = selection.get_selected()
                    parent_iter = None
                    if current_iter:
                        parent_iter = current_iter if model.get_value(current_iter, 0) == 'menu' else model.iter_parent(current_iter)
                    
                    desktop_file_name = f"{name.lower().replace(' ', '_').replace('/', '_')}.desktop"
                    pixbuf = self._get_icon_pixbuf(icon)
                    model.append(parent_iter, ["item", name, icon, command, desktop_file_name, pixbuf, False, "", True, "black"])
                elif model and selected_iter:
                    model.set_value(selected_iter, 1, name)
                    model.set_value(selected_iter, 2, icon)
                    model.set_value(selected_iter, 3, command)
                    model.set_value(selected_iter, 5, self._get_icon_pixbuf(icon))
                    model.set_value(selected_iter, 8, True) # Mark dirty
        
        dialog.destroy()

    def _on_delete_clicked(self, widget):
        model, selected_iter = self.treeview.get_selection().get_selected()
        if not selected_iter:
            self._show_error_dialog("エラー", "削除する項目が選択されていません。")
            return

        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK_CANCEL, text="本当に削除しますか？")
        dialog.format_secondary_text("この操作は元に戻せません。")
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            model.remove(selected_iter)
        dialog.destroy()

    def _on_move_up_clicked(self, widget):
        model, selected_iter = self.treeview.get_selection().get_selected()
        if not selected_iter: return
        prev_sibling = model.iter_previous(selected_iter)
        if prev_sibling:
            model.move_before(selected_iter, prev_sibling)

    def _on_move_down_clicked(self, widget):
        model, selected_iter = self.treeview.get_selection().get_selected()
        if not selected_iter: return
        next_sibling = model.iter_next(selected_iter)
        if next_sibling:
            model.move_after(selected_iter, next_sibling)

    def _show_error_dialog(self, title, text):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CANCEL, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = MenuEditorWindow()
    win.show_all()
    Gtk.main()