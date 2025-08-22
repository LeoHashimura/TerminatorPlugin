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
XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
XDG_DATA_DIRS = os.environ.get('XDG_DATA_DIRS', '/usr/local/share/:/usr/share/').split(':')

USER_MENUS_DIR = os.path.join(XDG_CONFIG_HOME, "menus/")
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
        self.connect("destroy", self._on_quit)

        self._initial_setup()

        # (type, name, icon, command, desktop_file, pixbuf, is_hidden, source_path, foreground)
        self.treestore = Gtk.TreeStore(str, str, str, str, str, GdkPixbuf.Pixbuf, bool, str, str)
        self.excluded_files = set()
        self.is_dirty = False
        
        self._create_ui()
        self._load_menu_data()

    def _set_dirty(self, dirty=True):
        self.is_dirty = dirty

    def _initial_setup(self):
        for path in [USER_MENUS_DIR] + [d for d in APPLICATIONS_DIRS] + [d for d in DESKTOP_DIRS]:
            if not os.path.exists(path):
                try: os.makedirs(path, exist_ok=True) catch OSError: pass

        if not os.path.exists(USER_MENU_FILE):
            if os.path.exists(SYSTEM_MENU_FILE):
                shutil.copy(SYSTEM_MENU_FILE, USER_MENU_FILE)
            else:
                ET.ElementTree(ET.Element("Menu", {"Name": "Main Menu"})).write(USER_MENU_FILE, encoding="utf-8", xml_declaration=True)

    def _create_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_vbox)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        main_vbox.pack_start(sw, True, True, 0)

        self.treeview = Gtk.TreeView(model=self.treestore)
        sw.add(self.treeview)

        col_icon = Gtk.TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), pixbuf=5)
        self.treeview.append_column(col_icon)
        col_name = Gtk.TreeViewColumn("名前", Gtk.CellRendererText(), text=1, foreground=8)
        self.treeview.append_column(col_name)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=5)
        main_vbox.pack_start(button_box, False, False, 0)

        for label, callback in [
            ("新規メニュー", self._on_new_menu_clicked),
            ("新規アイテム", self._on_new_item_clicked),
            ("編集", self._on_edit_clicked),
        ]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            button_box.pack_start(btn, False, False, 0)
        
        self.btn_hide = Gtk.Button(label="非表示")
        self.btn_hide.connect("clicked", self._on_hide_clicked)
        button_box.pack_start(self.btn_hide, False, False, 0)

        for label, callback in [
            ("削除", self._on_delete_clicked),
        ]:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", callback)
            button_box.pack_start(btn, False, False, 0)

        for icon, callback in [
            ("go-up-symbolic", self._on_move_up_clicked),
            ("go-down-symbolic", self._on_move_down_clicked),
        ]:
            btn = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
            btn.connect("clicked", callback)
            button_box.pack_start(btn, False, False, 0)

        btn_save = Gtk.Button(label="保存")
        btn_save.connect("clicked", self._on_save_clicked)
        button_box.pack_end(btn_save, False, False, 0)

        btn_reload = Gtk.Button(label="再読み込み")
        btn_reload.connect("clicked", self._on_reload_clicked)
        button_box.pack_end(btn_reload, False, False, 0)

        self.treeview.get_selection().connect("changed", self._on_selection_changed)

    def _find_file(self, filename, search_dirs):
        for directory in search_dirs:
            path = os.path.join(directory, filename)
            if os.path.exists(path): return path
        return None

    def _parse_entry_file(self, filepath):
        config = configparser.ConfigParser(interpolation=None)
        config.optionxform = str
        try:
            if config.read(filepath, encoding='utf-8'):
                entry = config['Desktop Entry']
                return {
                    'name': entry.get('Name', 'Unnamed'),
                    'icon': entry.get('Icon', 'application-x-executable'),
                    'exec': entry.get('Exec', ''),
                }
        except Exception: pass
        return None

    def _get_icon_pixbuf(self, icon_name, size=Gtk.IconSize.BUTTON):
        if not icon_name: icon_name = "application-x-executable"
        try:
            return Gtk.IconTheme.get_default().load_icon(icon_name, size, 0)
        except GLib.Error:
            return Gtk.IconTheme.get_default().load_icon("application-x-executable", size, 0)

    def _load_menu_data(self):
        self.treestore.clear()
        self.excluded_files.clear()
        self._set_dirty(False)
        try:
            self.xml_tree = ET.parse(USER_MENU_FILE)
            xml_root = self.xml_tree.getroot()
            for node in xml_root.findall("Exclude/Filename"): self.excluded_files.add(node.text)
            self._populate_tree_recursive(xml_root, None)
            self.treeview.expand_all()
        except (ET.ParseError, FileNotFoundError) as e:
            self._show_error_dialog("メニューファイルの読み込みエラー", str(e))

    def _populate_tree_recursive(self, xml_element, parent_iter):
        for child_node in list(xml_element):
            if child_node.tag == "Menu":
                name, icon = self._get_menu_details(child_node)
                pixbuf = self._get_icon_pixbuf(icon)
                current_iter = self.treestore.append(parent_iter, ["menu", name, icon, "", "", pixbuf, False, "", "black"])
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
                            self.treestore.append(parent_iter, ["item", item_data['name'], item_data['icon'], item_data['exec'], desktop_file, pixbuf, is_hidden, source_path, color])

    def _get_menu_details(self, menu_node):
        name, icon = "無名のメニュー", "folder"
        dir_node = menu_node.find("Directory")
        if dir_node is not None and dir_node.text:
            dir_path = self._find_file(dir_node.text, DESKTOP_DIRS)
            if dir_path:
                dir_data = self._parse_entry_file(dir_path)
                if dir_data:
                    name, icon = dir_data.get('name', name), dir_data.get('icon', icon)
                menu_node.remove(dir_node)
                ET.SubElement(menu_node, "Name").text = name
                ET.SubElement(menu_node, "Icon").text = icon
                self._set_dirty()
        else:
            name, icon = menu_node.findtext("Name", name), menu_node.findtext("Icon", icon)
        return name, icon

    def _on_selection_changed(self, selection):
        model, it = selection.get_selected()
        if it and model.get_value(it, 0) == 'item':
            self.btn_hide.set_sensitive(True)
            is_hidden = model.get_value(it, 6)
            self.btn_hide.set_label("再表示" if is_hidden else "非表示")
        else:
            self.btn_hide.set_sensitive(False)

    def _on_hide_clicked(self, widget):
        model, it = self.treeview.get_selection().get_selected()
        if not it: return
        is_hidden = not model.get_value(it, 6)
        desktop_file = model.get_value(it, 4)
        model.set(it, 6, is_hidden, 8, "grey" if is_hidden else "black")
        if is_hidden: self.excluded_files.add(desktop_file) 
        else: self.excluded_files.discard(desktop_file)
        self._set_dirty()
        self._on_selection_changed(self.treeview.get_selection())

    def _on_save_clicked(self, widget):
        if not self.is_dirty:
            self._show_info_dialog("情報", "変更点はありません。")
            return
        self._save_menu_data()
        self._set_dirty(False)
        self._show_info_dialog("成功", "メニューファイルを保存しました。")

    def _on_quit(self, widget, event=None):
        if self.is_dirty:
            dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text="未保存の変更があります。保存しますか？")
            dialog.format_secondary_text("保存せずに終了すると、変更は失われます。")
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                self._save_menu_data()
        Gtk.main_quit()

    def _save_menu_data(self):
        new_root = ET.Element("Menu")
        ET.SubElement(new_root, "Name").text = self.xml_tree.getroot().findtext("Name", "XFCE")
        if self.excluded_files:
            exclude_root = ET.SubElement(new_root, "Exclude")
            for filename in sorted(list(self.excluded_files)):
                ET.SubElement(exclude_root, "Filename").text = filename
        self._build_xml_recursive(new_root, None)
        xml_str = ET.tostring(new_root, 'utf-8')
        reparsed = minidom.parseString(xml_str)
        pretty_xml_str = reparsed.toprettyxml(indent="  ", newl="
", encoding="utf-8")
        try:
            with open(USER_MENU_FILE, 'wb') as f: f.write(pretty_xml_str)
        except IOError as e:
            self._show_error_dialog("保存エラー", f"メニューファイルの保存に失敗しました。
{e}")

    def _build_xml_recursive(self, xml_parent, parent_iter):
        child_iter = self.treestore.iter_children(parent_iter)
        while child_iter:
            row = self.treestore[child_iter]
            item_type, name, icon, command, desktop_file, source_path = row[0], row[1], row[2], row[3], row[4], row[7]
            if item_type == "menu":
                menu_element = ET.SubElement(xml_parent, "Menu")
                ET.SubElement(menu_element, "Name").text = name
                if icon != "folder": ET.SubElement(menu_element, "Icon").text = icon
                self._build_xml_recursive(menu_element, child_iter)
            elif item_type == "item":
                target_path = os.path.join(APPLICATIONS_DIRS[0], desktop_file)
                if source_path and source_path != target_path and not os.path.exists(target_path):
                    shutil.copy(source_path, target_path)
                include_element = ET.SubElement(xml_parent, "Include")
                ET.SubElement(include_element, "Filename").text = desktop_file
            child_iter = self.treestore.iter_next(child_iter)

    def _on_reload_clicked(self, widget):
        if self.is_dirty:
            dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text="未保存の変更があります。リロードしますか？")
            dialog.format_secondary_text("リロードすると、現在の変更は失われます。")
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.YES: return
        self._load_menu_data()

    def _on_new_menu_clicked(self, widget):
        self._show_menu_edit_dialog(is_new=True)

    def _on_new_item_clicked(self, widget):
        self._show_item_dialog(is_new=True)

    def _on_edit_clicked(self, widget):
        model, it = self.treeview.get_selection().get_selected()
        if not it: self._show_error_dialog("エラー", "項目が選択されていません。"); return
        item_type = model.get_value(it, 0)
        if item_type == "menu": self._show_menu_edit_dialog(is_new=False, model=model, selected_iter=it)
        elif item_type == "item": self._show_item_dialog(is_new=False, model=model, selected_iter=it)

    def _show_menu_edit_dialog(self, is_new, model=None, selected_iter=None):
        title = "新規メニュー" if is_new else "メニュー編集"
        dialog = Gtk.Dialog(title=title, transient_for=self, flags=0, buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        entry = Gtk.Entry(margin=10, text=model.get_value(selected_iter, 1) if not is_new else "", placeholder_text="メニュー名")
        dialog.get_content_area().add(entry)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            name = entry.get_text()
            if name:
                if is_new:
                    sel_model, sel_iter = self.treeview.get_selection().get_selected()
                    parent_iter = sel_model.iter_parent(sel_iter) if sel_iter else None
                    pixbuf = self._get_icon_pixbuf("folder")
                    model.append(parent_iter, ["menu", name, "folder", "", "", pixbuf, False, "", "black"])
                else: model.set(selected_iter, {1: name})
                self._set_dirty()
        dialog.destroy()

    def _show_item_dialog(self, is_new, model=None, selected_iter=None):
        title = "新規アイテム" if is_new else "アイテム編集"
        dialog = Gtk.Dialog(title=title, transient_for=self, flags=0, buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        grid = Gtk.Grid(column_spacing=10, row_spacing=10, margin=10)
        dialog.get_content_area().add(grid)
        entries = {
            'Name': Gtk.Entry(text=model.get_value(selected_iter, 1) if not is_new else ""),
            'Exec': Gtk.Entry(text=model.get_value(selected_iter, 3) if not is_new else ""),
            'Icon': Gtk.Entry(text=model.get_value(selected_iter, 2) if not is_new else ""),
        }
        for i, (label, widget) in enumerate(entries.items()):
            grid.attach(Gtk.Label(label=f"{label}:"), 0, i, 1, 1)
            grid.attach(widget, 1, i, 1, 1)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            data = {k: v.get_text() for k, v in entries.items()}
            if data['Name'] and data['Exec']:
                if is_new:
                    sel_model, sel_iter = self.treeview.get_selection().get_selected()
                    parent_iter = sel_iter if sel_iter and sel_model.get_value(sel_iter, 0) == 'menu' else (sel_model.iter_parent(sel_iter) if sel_iter else None)
                    desktop_file = f"{data['Name'].lower().replace(' ', '_')}.desktop"
                    pixbuf = self._get_icon_pixbuf(data['Icon'])
                    model.append(parent_iter, ["item", data['Name'], data['Icon'], data['Exec'], desktop_file, pixbuf, False, "", "black"])
                else: model.set(selected_iter, {1: data['Name'], 2: data['Icon'], 3: data['Exec'], 5: self._get_icon_pixbuf(data['Icon'])})
                self._set_dirty()
        dialog.destroy()

    def _on_delete_clicked(self, widget):
        model, it = self.treeview.get_selection().get_selected()
        if not it: return
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK_CANCEL, text="本当に削除しますか？")
        dialog.format_secondary_text("この操作は元に戻せません。")
        if dialog.run() == Gtk.ResponseType.OK: model.remove(it); self._set_dirty()
        dialog.destroy()

    def _on_move_up_clicked(self, widget):
        model, it = self.treeview.get_selection().get_selected()
        if it and model.iter_previous(it):
            model.move_before(it, model.iter_previous(it)); self._set_dirty()

    def _on_move_down_clicked(self, widget):
        model, it = self.treeview.get_selection().get_selected()
        if it and model.iter_next(it):
            model.move_after(it, model.iter_next(it)); self._set_dirty()

    def _show_error_dialog(self, title, text):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CANCEL, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

    def _show_info_dialog(self, title, text):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()