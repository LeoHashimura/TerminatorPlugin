#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GdkPixbuf, GLib

import os
import shutil
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- 定数定義 ---
APP_NAME = "XFCEメニューエディタ"
USER_MENUS_DIR = os.path.expanduser("~/.config/menus/")
USER_MENU_FILE = os.path.join(USER_MENUS_DIR, "xfce-applications.menu")
SYSTEM_MENU_FILE = "/etc/xdg/menus/xfce-applications.menu"
DESKTOP_FILES_DIR = os.path.expanduser("~/.local/share/applications/")

DESKTOP_FILE_TEMPLATE = """[Desktop Entry]
Version=1.0
Type=Application
Name={name}
Comment=
Exec={exec}
Icon={icon}
Categories=
Terminal=false
"""

# --- メインのGUIクラス ---
class MenuEditorWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        self.set_default_size(600, 700)
        self.connect("destroy", Gtk.main_quit)

        self._initial_setup()

        # TreeStoreモデルの作成
        # (type, name, icon_name, command, desktop_file_path, icon_pixbuf)
        self.treestore = Gtk.TreeStore(str, str, str, str, str, GdkPixbuf.Pixbuf)
        
        self._create_ui()
        self._load_menu_data()

    def _initial_setup(self):
        """起動時にディレクトリの存在確認やメニューファイルの準備を行う"""
        if not os.path.exists(USER_MENUS_DIR):
            os.makedirs(USER_MENUS_DIR)
        if not os.path.exists(DESKTOP_FILES_DIR):
            os.makedirs(DESKTOP_FILES_DIR)

        if not os.path.exists(USER_MENU_FILE):
            if os.path.exists(SYSTEM_MENU_FILE):
                shutil.copy(SYSTEM_MENU_FILE, USER_MENU_FILE)
            else:
                # フォールバック用の空のメニューファイルを作成
                root = ET.Element("Menu")
                ET.SubElement(root, "Name").text = "Main Menu"
                tree = ET.ElementTree(root)
                tree.write(USER_MENU_FILE, encoding="utf-8", xml_declaration=True)


    def _create_ui(self):
        """UIウィジェットの作成と配置"""
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(main_vbox)

        # --- TreeView ---
        self.treeview = Gtk.TreeView(model=self.treestore)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(self.treeview)
        main_vbox.pack_start(scrolled_window, True, True, 0)

        # TreeViewの列を設定
        renderer_pixbuf = Gtk.CellRendererPixbuf()
        column_pixbuf = Gtk.TreeViewColumn("Icon", renderer_pixbuf, pixbuf=5)
        self.treeview.append_column(column_pixbuf)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("名前", renderer_text, text=1)
        self.treeview.append_column(column_text)

        # --- ボタン ---
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_vbox.pack_start(button_box, False, False, 5)
        
        btn_reload = Gtk.Button(label="再読み込み")
        btn_reload.connect("clicked", self._on_reload_clicked)
        button_box.pack_start(btn_reload, False, False, 0)

        btn_new_menu = Gtk.Button(label="新規メニュー")
        btn_new_menu.connect("clicked", self._on_new_menu_clicked)
        button_box.pack_start(btn_new_menu, False, False, 0)

        btn_new_item = Gtk.Button(label="新規アイテム")
        btn_new_item.connect("clicked", self._on_new_item_clicked)
        button_box.pack_start(btn_new_item, False, False, 0)

        btn_edit = Gtk.Button(label="編集")
        btn_edit.connect("clicked", self._on_edit_clicked)
        button_box.pack_start(btn_edit, False, False, 0)

        btn_delete = Gtk.Button(label="削除")
        btn_delete.connect("clicked", self._on_delete_clicked)
        button_box.pack_start(btn_delete, False, False, 0)
        
        control_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_vbox.pack_start(control_button_box, False, False, 5)

        btn_up = Gtk.Button(label="上へ")
        btn_up.connect("clicked", self._on_move_up_clicked)
        control_button_box.pack_start(btn_up, False, False, 0)

        btn_down = Gtk.Button(label="下へ")
        btn_down.connect("clicked", self._on_move_down_clicked)
        control_button_box.pack_start(btn_down, False, False, 0)

        btn_save = Gtk.Button(label="保存して終了")
        btn_save.connect("clicked", self._on_save_and_quit_clicked)
        control_button_box.pack_end(btn_save, False, False, 0)


    def _get_icon_pixbuf(self, icon_name, size=Gtk.IconSize.LARGE_TOOLBAR):
        """アイコン名からGdkPixbufを取得する"""
        try:
            theme = Gtk.IconTheme.get_default()
            return theme.load_icon(icon_name, size, 0)
        except GLib.Error:
            return theme.load_icon("application-x-executable", size, 0) # Fallback

    def _load_menu_data(self):
        """XMLファイルからメニューデータを読み込み、TreeViewを構築する"""
        self.treestore.clear()
        try:
            self.xml_tree = ET.parse(USER_MENU_FILE)
            xml_root = self.xml_tree.getroot()
            self._populate_tree_recursive(xml_root, None)
        except (ET.ParseError, FileNotFoundError) as e:
            self._show_error_dialog("メニューファイルの読み込みエラー", str(e))

    def _populate_tree_recursive(self, xml_element, parent_iter):
        """XML要素を再帰的に解析してTreeStoreに追加する"""
        for child in xml_element:
            if child.tag == "Menu":
                name = child.find("Name").text if child.find("Name") is not None else "無名のメニュー"
                pixbuf = self._get_icon_pixbuf("folder")
                current_iter = self.treestore.append(parent_iter, ["menu", name, "", "", "", pixbuf])
                self._populate_tree_recursive(child, current_iter)
            elif child.tag == "Include":
                filename_tag = child.find("Filename")
                if filename_tag is not None:
                    desktop_file = filename_tag.text
                    self._add_item_from_desktop_file(desktop_file, parent_iter)

    def _add_item_from_desktop_file(self, desktop_file, parent_iter):
        """ .desktop ファイルから情報を読み取りアイテムをTreeStoreに追加 """
        name, icon, command = "不明なアイテム", "application-x-executable", ""
        full_path = os.path.join(DESKTOP_FILES_DIR, desktop_file)
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r') as f:
                    for line in f:
                        if line.startswith("Name="):
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Icon="):
                            icon = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec="):
                            command = line.split("=", 1)[1].strip()
            except Exception:
                pass # ファイルが読めなくても気にしない
        
        pixbuf = self._get_icon_pixbuf(icon)
        self.treestore.append(parent_iter, ["item", name, icon, command, desktop_file, pixbuf])

    def _on_reload_clicked(self, widget):
        self._load_menu_data()

    def _on_new_menu_clicked(self, widget):
        dialog = Gtk.Dialog(title="新規メニュー作成", transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_placeholder_text("メニュー名")
        content_area.add(entry)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = entry.get_text()
            if name:
                selection = self.treeview.get_selection()
                model, selected_iter = selection.get_selected()
                parent_iter = model.iter_parent(selected_iter) if selected_iter else None
                pixbuf = self._get_icon_pixbuf("folder")
                self.treestore.append(parent_iter, ["menu", name, "", "", "", pixbuf])
        dialog.destroy()

    def _on_new_item_clicked(self, widget):
        self._show_item_dialog(is_new=True)

    def _on_edit_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, selected_iter = selection.get_selected()
        if not selected_iter:
            self._show_error_dialog("エラー", "項目が選択されていません。")
            return
        
        item_type = model.get_value(selected_iter, 0)
        if item_type == "menu":
            self._show_menu_edit_dialog(model, selected_iter)
        elif item_type == "item":
            self._show_item_dialog(is_new=False, model=model, selected_iter=selected_iter)

    def _show_menu_edit_dialog(self, model, selected_iter):
        """メニュー編集ダイアログ"""
        original_name = model.get_value(selected_iter, 1)
        dialog = Gtk.Dialog(title="メニュー編集", transient_for=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        
        content_area = dialog.get_content_area()
        entry = Gtk.Entry()
        entry.set_text(original_name)
        content_area.add(entry)
        dialog.show_all()

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_name = entry.get_text()
            if new_name:
                model.set_value(selected_iter, 1, new_name)
        dialog.destroy()

    def _show_item_dialog(self, is_new, model=None, selected_iter=None):
        """アイテムの新規作成・編集ダイアログ"""
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

        if not is_new:
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
                        item_type = model.get_value(current_iter, 0)
                        if item_type == "menu":
                            parent_iter = current_iter
                        else:
                            parent_iter = model.iter_parent(current_iter)

                    desktop_file_name = f"{name.lower().replace(' ', '_')}.desktop"
                    pixbuf = self._get_icon_pixbuf(icon)
                    self.treestore.append(parent_iter, ["item", name, icon, command, desktop_file_name, pixbuf])
                else:
                    model.set_value(selected_iter, 1, name)
                    model.set_value(selected_iter, 2, icon)
                    model.set_value(selected_iter, 3, command)
                    model.set_value(selected_iter, 5, self._get_icon_pixbuf(icon))
        
        dialog.destroy()

    def _on_delete_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, selected_iter = selection.get_selected()
        if not selected_iter:
            self._show_error_dialog("エラー", "削除する項目が選択されていません。")
            return

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="本当に削除しますか？",
        )
        dialog.format_secondary_text(
            "メニューを削除すると、中に含まれるすべての項目も削除されます。この操作は元に戻せません。"
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            model.remove(selected_iter)
        dialog.destroy()

    def _on_move_up_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, selected_iter = selection.get_selected()
        if not selected_iter: return
        
        prev_sibling = model.iter_previous(selected_iter)
        if prev_sibling:
            model.move_before(selected_iter, prev_sibling)

    def _on_move_down_clicked(self, widget):
        selection = self.treeview.get_selection()
        model, selected_iter = selection.get_selected()
        if not selected_iter: return

        next_sibling = model.iter_next(selected_iter)
        if next_sibling:
            model.move_after(selected_iter, next_sibling)

    def _on_save_and_quit_clicked(self, widget):
        self._save_menu_data()
        Gtk.main_quit()

    def _save_menu_data(self):
        """TreeStoreの内容をXMLファイルに保存する"""
        new_root = ET.Element("Menu")
        ET.SubElement(new_root, "Name").text = "XFCE" # Root menu name
        
        self._build_xml_recursive(new_root, None)
        
        # Pretty print
        xml_str = ET.tostring(new_root, 'utf-8')
        reparsed = minidom.parseString(xml_str)
        pretty_xml_str = reparsed.toprettyxml(indent="  ", newl="\n", encoding="utf-8")

        try:
            with open(USER_MENU_FILE, 'wb') as f:
                f.write(pretty_xml_str)
        except IOError as e:
            self._show_error_dialog("保存エラー", f"メニューファイルの保存に失敗しました。\n{e}")

    def _build_xml_recursive(self, xml_parent, parent_iter):
        """TreeStoreを再帰的に走査してXMLを構築する"""
        child_iter = self.treestore.iter_children(parent_iter)
        while child_iter:
            item_type = self.treestore.get_value(child_iter, 0)
            name = self.treestore.get_value(child_iter, 1)

            if item_type == "menu":
                menu_element = ET.SubElement(xml_parent, "Menu")
                ET.SubElement(menu_element, "Name").text = name
                self._build_xml_recursive(menu_element, child_iter)
            elif item_type == "item":
                icon = self.treestore.get_value(child_iter, 2)
                command = self.treestore.get_value(child_iter, 3)
                desktop_file = self.treestore.get_value(child_iter, 4)
                
                # .desktop ファイルを作成/更新
                desktop_content = DESKTOP_FILE_TEMPLATE.format(name=name, exec=command, icon=icon)
                try:
                    with open(os.path.join(DESKTOP_FILES_DIR, desktop_file), 'w') as f:
                        f.write(desktop_content)
                except IOError as e:
                    self._show_error_dialog("デスクトップファイル保存エラー", str(e))
                    continue # 保存に失敗したらスキップ

                include_element = ET.SubElement(xml_parent, "Include")
                ET.SubElement(include_element, "Filename").text = desktop_file

            child_iter = self.treestore.iter_next(child_iter)

    def _show_error_dialog(self, title, text):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CANCEL,
            text=title,
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = MenuEditorWindow()
    win.show_all()
    Gtk.main()
