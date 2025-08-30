#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import os
import configparser
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- 定数定義 ---
APP_NAME = "XFCEメニュービルダー"

# XDG Dirs
XDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
XDG_DATA_HOME = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
XDG_DATA_DIRS = os.environ.get('XDG_DATA_DIRS', '/usr/local/share/:/usr/share/').split(':')

# Paths
USER_MENUS_DIR = os.path.join(XDG_CONFIG_HOME, "menus/")
USER_MENU_FILE = os.path.join(USER_MENUS_DIR, "xfce-applications.menu")
APPLICATIONS_DIRS = [os.path.join(d, 'applications') for d in [XDG_DATA_HOME] + XDG_DATA_DIRS]

# --- Main Application Class ---
class MenuBuilderWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(800, 600)
        self.connect("destroy", Gtk.main_quit)

        self.is_dirty = False

        self._create_ui()
        self._populate_available_apps()

    def _create_ui(self):
        # Main Paned Layout
        hpaned = Gtk.HPaned()
        self.add(hpaned)

        # --- Right Pane (Available Apps) ---
        right_pane_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=5)
        hpaned.add2(right_pane_vbox)
        
        right_label = Gtk.Label(label="利用可能なアイテム", xalign=0)
        right_pane_vbox.pack_start(right_label, False, True, 0)

        sw_right = Gtk.ScrolledWindow()
        sw_right.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        right_pane_vbox.pack_start(sw_right, True, True, 0)

        # (name, pixbuf, path_or_type)
        self.available_apps_store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str)
        self.available_apps_view = Gtk.TreeView(model=self.available_apps_store)
        sw_right.add(self.available_apps_view)

        col_icon_right = Gtk.TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), pixbuf=1)
        self.available_apps_view.append_column(col_icon_right)
        col_name_right = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0)
        self.available_apps_view.append_column(col_name_right)

        # --- Left Pane (Menu in Progress) ---
        left_pane_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin=5)
        hpaned.add1(left_pane_vbox)

        left_label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        left_label = Gtk.Label(label="メニュー構造", xalign=0)
        left_label_box.pack_start(left_label, False, True, 0)
        
        self.dirty_indicator = Gtk.Label(label="")
        left_label_box.pack_end(self.dirty_indicator, False, False, 0)
        left_pane_vbox.pack_start(left_label_box, False, True, 0)

        sw_left = Gtk.ScrolledWindow()
        sw_left.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        left_pane_vbox.pack_start(sw_left, True, True, 0)

        # (name, pixbuf, path_or_type, type) -> type is 'menu' or 'item'
        self.menu_structure_store = Gtk.TreeStore(str, GdkPixbuf.Pixbuf, str, str)
        self.menu_structure_view = Gtk.TreeView(model=self.menu_structure_store)
        sw_left.add(self.menu_structure_view)
        
        col_icon_left = Gtk.TreeViewColumn("Icon", Gtk.CellRendererPixbuf(), pixbuf=1)
        self.menu_structure_view.append_column(col_icon_left)
        col_name_left = Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0)
        self.menu_structure_view.append_column(col_name_left)

        # Add root item to the left pane
        pixbuf_root = self._get_icon_pixbuf("folder-open")
        self.menu_structure_store.append(None, ["メインメニュー", pixbuf_root, "ROOT_MENU", "menu"])

        # --- Bottom Buttons ---
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin=5)
        left_pane_vbox.pack_start(button_box, False, False, 0)

        btn_delete = Gtk.Button(label="削除")
        btn_delete.connect("clicked", self._on_delete_clicked)
        button_box.pack_start(btn_delete, False, False, 0)

        btn_edit = Gtk.Button(label="名前の変更")
        btn_edit.connect("clicked", self._on_edit_clicked)
        button_box.pack_start(btn_edit, False, False, 0)

        btn_save = Gtk.Button(label="保存して終了")
        btn_save.connect("clicked", self._on_save_clicked)
        button_box.pack_end(btn_save, False, False, 0)

        # --- Drag and Drop Setup ---
        self.setup_dnd()

    def set_dirty(self, dirty=True):
        self.is_dirty = dirty
        self.dirty_indicator.set_markup("<span foreground='red'>*</span>" if dirty else "")

    def _get_icon_pixbuf(self, icon_name, size=Gtk.IconSize.BUTTON):
        if not icon_name: icon_name = "application-x-executable"
        try:
            return Gtk.IconTheme.get_default().load_icon(icon_name, size, 0)
        except GLib.Error:
            return Gtk.IconTheme.get_default().load_icon("application-x-executable", size, 0)

    def _populate_available_apps(self):
        self.available_apps_store.clear()
        
        # Add "New Folder"
        pixbuf_folder = self._get_icon_pixbuf("folder-new")
        self.available_apps_store.append(["新規フォルダ", pixbuf_folder, "NEW_FOLDER"])

        # Scan for apps
        seen_apps = set()
        for app_dir in APPLICATIONS_DIRS:
            if not os.path.isdir(app_dir): continue
            for filename in os.listdir(app_dir):
                if filename.endswith(".desktop") and filename not in seen_apps:
                    seen_apps.add(filename)
                    parser = configparser.ConfigParser(interpolation=None)
                    try:
                        parser.read(os.path.join(app_dir, filename), encoding='utf-8')
                        if parser.has_option('Desktop Entry', 'NoDisplay') and parser.getboolean('Desktop Entry', 'NoDisplay'):
                            continue
                        name = parser.get('Desktop Entry', 'Name', fallback=filename)
                        icon = parser.get('Desktop Entry', 'Icon', fallback='application-x-executable')
                        pixbuf = self._get_icon_pixbuf(icon)
                        self.available_apps_store.append([name, pixbuf, filename])
                    except Exception:
                        continue

    def setup_dnd(self):
        # Right pane (source)
        self.available_apps_view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.COPY)
        self.available_apps_view.drag_source_add_text_targets()

        # Left pane (destination)
        self.menu_structure_view.enable_model_drag_dest([], Gdk.DragAction.DEFAULT | Gdk.DragAction.MOVE)
        self.menu_structure_view.drag_dest_add_text_targets()
        
        # Left pane (reorder source)
        self.menu_structure_view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, [], Gdk.DragAction.MOVE)
        self.menu_structure_view.drag_source_add_text_targets()

        self.available_apps_view.connect("drag-data-get", self._on_drag_data_get_available)
        self.menu_structure_view.connect("drag-data-get", self._on_drag_data_get_structure)
        self.menu_structure_view.connect("drag-data-received", self._on_drag_data_received)

    def _on_drag_data_get_available(self, widget, context, selection, info, timestamp):
        model, it = widget.get_selection().get_selected()
        if it:
            path_or_type = model.get_value(it, 2)
            selection.set_text(f"NEW:{path_or_type}", -1)

    def _on_drag_data_get_structure(self, widget, context, selection, info, timestamp):
        model, it = widget.get_selection().get_selected()
        if it:
            path = Gtk.TreePath.new_from_iter(it)
            # Prevent dragging the root
            if path.get_depth() > 1:
                selection.set_text(f"MOVE:{path.to_string()}", -1)

    def _on_drag_data_received(self, widget, context, x, y, selection, info, timestamp):
        data = selection.get_text()
        if not data: return

        drop_info = widget.get_dest_row_at_pos(x, y)
        
        if data.startswith("NEW:"):
            path_or_type = data[4:]
            
            if path_or_type == "NEW_FOLDER":
                name = "新しいフォルダ"
                pixbuf = self._get_icon_pixbuf("folder")
                item_type = "menu"
            else:
                # Dropped an app
                parser = configparser.ConfigParser(interpolation=None)
                app_path = self._find_desktop_file(path_or_type)
                if not app_path: return
                parser.read(app_path, encoding='utf-8')
                name = parser.get('Desktop Entry', 'Name', fallback=path_or_type)
                icon = parser.get('Desktop Entry', 'Icon', fallback='application-x-executable')
                pixbuf = self._get_icon_pixbuf(icon)
                item_type = "item"

            parent_iter = None
            if drop_info:
                path, pos = drop_info
                drop_iter = self.menu_structure_store.get_iter(path)
                if self.menu_structure_store.get_value(drop_iter, 3) == 'menu':
                    parent_iter = drop_iter
                else:
                    parent_iter = self.menu_structure_store.iter_parent(drop_iter)
            
            self.menu_structure_store.append(parent_iter, [name, pixbuf, path_or_type, item_type])
            self.set_dirty()

        elif data.startswith("MOVE:"):
            path_str = data[5:]
            src_path = Gtk.TreePath.new_from_string(path_str)
            src_iter = self.menu_structure_store.get_iter(src_path)

            if drop_info:
                path, pos = drop_info
                dest_iter = self.menu_structure_store.get_iter(path)
                
                if self.menu_structure_store.get_value(dest_iter, 3) == 'menu':
                    self.menu_structure_store.move(src_iter, dest_iter)
                else:
                    parent_iter = self.menu_structure_store.iter_parent(dest_iter)
                    self.menu_structure_store.move(src_iter, parent_iter)
                self.set_dirty()

    def _find_desktop_file(self, filename):
        for app_dir in APPLICATIONS_DIRS:
            path = os.path.join(app_dir, filename)
            if os.path.exists(path):
                return path
        return None

    def _on_delete_clicked(self, widget):
        model, it = self.menu_structure_view.get_selection().get_selected()
        if not it: return
        # Prevent deleting the root
        if model.iter_parent(it) is None:
            self._show_info_dialog("エラー", "ルートメニューは削除できません。")
            return
        model.remove(it)
        self.set_dirty()

    def _on_edit_clicked(self, widget):
        model, it = self.menu_structure_view.get_selection().get_selected()
        if not it: return
        
        dialog = Gtk.Dialog(title="名前の変更", transient_for=self, flags=0,
                              buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK))
        entry = Gtk.Entry(margin=10, text=model.get_value(it, 0))
        dialog.get_content_area().add(entry)
        dialog.show_all()
        if dialog.run() == Gtk.ResponseType.OK:
            new_name = entry.get_text()
            if new_name:
                model.set_value(it, 0, new_name)
                self.set_dirty()
        dialog.destroy()

    def _on_save_clicked(self, widget):
        self._save_menu_data()
        Gtk.main_quit()

    def _save_menu_data(self):
        if not os.path.exists(USER_MENUS_DIR):
            os.makedirs(USER_MENUS_DIR, exist_ok=True)

        root_iter = self.menu_structure_store.get_iter_first()
        root_name = self.menu_structure_store.get_value(root_iter, 0)

        new_root = ET.Element("Menu")
        ET.SubElement(new_root, "Name").text = root_name
        
        self._build_xml_recursive(new_root, root_iter)
        
        xml_str = ET.tostring(new_root, 'utf-8')
        reparsed = minidom.parseString(xml_str)
        pretty_xml_str = reparsed.toprettyxml(indent="  ", newl="\n", encoding="utf-8")

        try:
            with open(USER_MENU_FILE, 'wb') as f:
                f.write(pretty_xml_str)
            self.set_dirty(False)
        except IOError as e:
            self._show_info_dialog("保存エラー", f"メニューファイルの保存に失敗しました。\n{e}")

    def _build_xml_recursive(self, xml_parent, parent_iter):
        child_iter = self.menu_structure_store.iter_children(parent_iter)
        while child_iter:
            row = self.menu_structure_store[child_iter]
            name, path_or_type, item_type = row[0], row[2], row[3]

            if item_type == "menu":
                menu_element = ET.SubElement(xml_parent, "Menu")
                ET.SubElement(menu_element, "Name").text = name
                self._build_xml_recursive(menu_element, child_iter)
            elif item_type == "item":
                include_element = ET.SubElement(xml_parent, "Include")
                ET.SubElement(include_element, "Filename").text = path_or_type
            
            child_iter = self.menu_structure_store.iter_next(child_iter)

    def _show_info_dialog(self, title, text):
        dialog = Gtk.MessageDialog(transient_for=self, flags=0, message_type=Gtk.MessageType.INFO,
                                   buttons=Gtk.ButtonsType.OK, text=title)
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":
    win = MenuBuilderWindow()
    win.show_all()
    Gtk.main()
