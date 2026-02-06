import os
import bleach

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QTextBrowser,
    QMenu, QMessageBox, QInputDialog, QProgressDialog, QHeaderView, QApplication
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QShortcut, QKeySequence, QDesktopServices

from urllib.parse import urlparse
from datetime import datetime
from time import mktime

from utilities.functions import get_app_path
from media_providers.podcasts.feed_manager import FeedManager
from media_providers.podcasts.entry_detail_dialog import EntryDetailDialog


class FeedWidget(QWidget):
    play_requested = Signal(str)
    
    COMMON_FIELDS = ['title', 'published', 'link']
    LONG_TEXT_FIELDS = ['summary', 'description', 'content']
    BLACKLIST = ['published_parsed', 'updated_parsed', 'guidislink', 
                 'title_detail', 'summary_detail', 'author_detail', 
                 'links', 'content']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        cache_dir = os.path.join(get_app_path(), 'data', 'podcast_cache')
        self.feed_mgr = FeedManager(cache_dir=cache_dir)
        self.current_feed_url = None
        self.all_entries = []
        self.filtered_entries = []
        self.sort_key = 'published_parsed'
        self.sort_reverse = True
        self.setup_ui()
        self.load_feeds()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type and press Enter to search entries...")
        self.search_box.returnPressed.connect(self.perform_search)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box, 1)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_btn)
        main_layout.addLayout(search_layout)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        feed_container = QWidget()
        feed_layout = QVBoxLayout(feed_container)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        feed_label = QLabel("<b>Feeds</b>")
        feed_layout.addWidget(feed_label)
        
        self.feed_list = QListWidget()
        self.feed_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.feed_list.customContextMenuRequested.connect(self.show_feed_context_menu)
        self.feed_list.setAlternatingRowColors(True)
        self.feed_list.currentItemChanged.connect(self.on_feed_changed)
        self.feed_list.setAccessibleName("Feed List")
        self.feed_list.setAccessibleDescription("List of RSS feeds. Right-click for options.")
        feed_layout.addWidget(self.feed_list)
        
        splitter.addWidget(feed_container)
        
        entry_container = QWidget()
        entry_layout = QVBoxLayout(entry_container)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_label = QLabel("<b>Entries</b>")
        entry_layout.addWidget(entry_label)
        
        self.entry_tree = QTreeWidget()
        self.entry_tree.setColumnCount(3)
        self.entry_tree.setHeaderLabels(["Title", "Published", "Link"])
        self.entry_tree.setAlternatingRowColors(True)
        self.entry_tree.setRootIsDecorated(False)
        self.entry_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_tree.customContextMenuRequested.connect(self.show_entry_context_menu)
        self.entry_tree.currentItemChanged.connect(self.on_entry_changed)
        self.entry_tree.setAccessibleName("Entry Tree")
        self.entry_tree.setAccessibleDescription("Tree of feed entries with title, date, and link. Right-click for options.")
        self.entry_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.entry_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.entry_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        entry_layout.addWidget(self.entry_tree, 2)
        
        detail_label = QLabel("<b>Summary/Description</b>")
        entry_layout.addWidget(detail_label)
        
        self.detail_text = QTextBrowser()
        self.detail_text.setOpenExternalLinks(True)
        self.detail_text.setTabChangesFocus(True)
        self.detail_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard |
            Qt.TextInteractionFlag.LinksAccessibleByMouse |
            Qt.TextInteractionFlag.LinksAccessibleByKeyboard
        )
        self.detail_text.setAccessibleName("Entry Detail Text")
        self.detail_text.setAccessibleDescription("Summary and description of selected entry")
        entry_layout.addWidget(self.detail_text, 1)
        
        splitter.addWidget(entry_container)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        self._shortcuts = []
        shortcuts = [
            (Qt.Key.Key_Up, self.select_prev_entry),
            (Qt.Key.Key_Down, self.select_next_entry),
            (Qt.Key.Key_PageUp, self.select_page_up),
            (Qt.Key.Key_PageDown, self.select_page_down),
            (Qt.Key.Key_Home, self.select_first_entry),
            (Qt.Key.Key_End, self.select_last_entry),
        ]
        for key, handler in shortcuts:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(handler)
            self._shortcuts.append(sc)

    def validate_url(self, url):
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except:
            return False

    def validate_feed(self, url):
        try:
            parsed = self.feed_mgr.refresh_feed(url, force=True)
            if parsed and not parsed.get('bozo', 0):
                return True, None
            elif parsed and parsed.get('bozo', 0):
                exception = parsed.get('bozo_exception')
                return False, str(exception) if exception else "Invalid feed format"
            return False, "Failed to parse feed"
        except Exception as e:
            return False, str(e)

    def show_feed_context_menu(self, pos):
        menu = QMenu(self)
        
        add_action = QAction("Add Feed", self)
        add_action.triggered.connect(self.add_feed)
        menu.addAction(add_action)
        
        item = self.feed_list.itemAt(pos)
        if item:
            menu.addSeparator()
            
            refresh_action = QAction("Refresh Feed", self)
            refresh_action.triggered.connect(self.refresh_current_feed)
            menu.addAction(refresh_action)
            
            update_url_action = QAction("Update Feed URL", self)
            update_url_action.triggered.connect(self.update_feed_url)
            menu.addAction(update_url_action)
            
            remove_action = QAction("Remove Feed", self)
            remove_action.triggered.connect(self.remove_feed)
            menu.addAction(remove_action)
        
        if self.feed_list.count() > 0:
            menu.addSeparator()
            
            refresh_all_action = QAction("Refresh All Feeds", self)
            refresh_all_action.triggered.connect(self.refresh_all_feeds)
            menu.addAction(refresh_all_action)
            
            clear_action = QAction("Clear All Feeds", self)
            clear_action.triggered.connect(self.clear_all_feeds)
            menu.addAction(clear_action)
        
        menu.exec(self.feed_list.viewport().mapToGlobal(pos))

    def show_entry_context_menu(self, pos):
        item = self.entry_tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        sort_menu = menu.addMenu("Sort By")
        
        sort_title_asc = QAction("Title (Ascending A-Z)", self)
        sort_title_asc.triggered.connect(lambda: self.sort_entries('title', False))
        sort_menu.addAction(sort_title_asc)
        
        sort_title_desc = QAction("Title (Descending Z-A)", self)
        sort_title_desc.triggered.connect(lambda: self.sort_entries('title', True))
        sort_menu.addAction(sort_title_desc)
        
        sort_menu.addSeparator()
        
        sort_date_newest = QAction("Date (Newest First)", self)
        sort_date_newest.triggered.connect(lambda: self.sort_entries('published_parsed', True))
        sort_menu.addAction(sort_date_newest)
        
        sort_date_oldest = QAction("Date (Oldest First)", self)
        sort_date_oldest.triggered.connect(lambda: self.sort_entries('published_parsed', False))
        sort_menu.addAction(sort_date_oldest)
        
        menu.addSeparator()
        
        copy_menu = menu.addMenu("Copy")
        
        copy_title = QAction("Title", self)
        copy_title.triggered.connect(lambda: self.copy_entry_field(item, 'title'))
        copy_menu.addAction(copy_title)
        
        copy_link = QAction("Page Link", self)
        copy_link.triggered.connect(lambda: self.copy_entry_field(item, 'link'))
        copy_menu.addAction(copy_link)
        
        copy_media = QAction("Direct Media Link", self)
        copy_media.triggered.connect(lambda: self.copy_direct_media_link(item))
        copy_menu.addAction(copy_media)
        
        menu.addSeparator()
        
        full_entry_action = QAction("View Full Entry Dump", self)
        full_entry_action.triggered.connect(lambda: self.show_full_entry(item))
        menu.addAction(full_entry_action)
        
        open_link_action = QAction("Open Link in Browser", self)
        open_link_action.triggered.connect(lambda: self.open_entry_link(item))
        menu.addAction(open_link_action)
        
        menu.exec(self.entry_tree.viewport().mapToGlobal(pos))

    def add_feed(self):
        url, ok = QInputDialog.getText(self, "Add Feed", "Enter feed URL:")
        if not ok or not url:
            return
        
        if not self.validate_url(url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid HTTP/HTTPS URL")
            return
        
        if url in self.feed_mgr.get_feed_list():
            QMessageBox.warning(self, "Duplicate", "Feed already exists")
            return
        
        progress = QProgressDialog("Validating feed...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        valid, error = self.validate_feed(url)
        progress.close()
        
        if not valid:
            QMessageBox.critical(self, "Invalid Feed", f"Feed validation failed:\n{error}")
            self.feed_mgr.remove_feed(url)
            return
        
        self.feed_mgr.add_feed(url)
        QMessageBox.information(self, "Success", "Feed added successfully")
        self.load_feeds()

    def remove_feed(self):
        item = self.feed_list.currentItem()
        if not item:
            return
        
        url = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove feed:\n{url}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.feed_mgr.remove_feed(url)
            self.load_feeds()

    def refresh_current_feed(self):
        item = self.feed_list.currentItem()
        if not item:
            return
        
        url = item.data(Qt.ItemDataRole.UserRole)
        progress = QProgressDialog("Refreshing feed...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        try:
            result = self.feed_mgr.refresh_feed(url, force=True)
            progress.close()
            if result:
                QMessageBox.information(self, "Success", "Feed refreshed successfully")
                self.load_feed_entries(url)
            else:
                QMessageBox.warning(self, "Error", "Failed to refresh feed")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Refresh failed:\n{str(e)}")

    def refresh_all_feeds(self):
        feeds = self.feed_mgr.get_feed_list()
        if not feeds:
            return
        
        progress = QProgressDialog("Refreshing feeds...", "Cancel", 0, len(feeds), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        for i, url in enumerate(feeds):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(f"Refreshing:\n{url[:60]}...")
            try:
                self.feed_mgr.refresh_feed(url, force=True)
            except:
                pass
        
        progress.setValue(len(feeds))
        if self.current_feed_url:
            self.load_feed_entries(self.current_feed_url)

    def update_feed_url(self):
        item = self.feed_list.currentItem()
        if not item:
            return
        
        old_url = item.data(Qt.ItemDataRole.UserRole)
        new_url, ok = QInputDialog.getText(self, "Update Feed URL", "Enter new URL:", text=old_url)
        
        if not ok or not new_url or new_url == old_url:
            return
        
        if not self.validate_url(new_url):
            QMessageBox.warning(self, "Invalid URL", "Please enter a valid HTTP/HTTPS URL")
            return
        
        progress = QProgressDialog("Validating new feed URL...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        valid, error = self.validate_feed(new_url)
        progress.close()
        
        if not valid:
            QMessageBox.critical(self, "Invalid Feed", f"Feed validation failed:\n{error}")
            self.feed_mgr.remove_feed(new_url)
            return
        
        self.feed_mgr.update_feed_url(old_url, new_url)
        QMessageBox.information(self, "Success", "Feed URL updated successfully")
        self.load_feeds()

    def clear_all_feeds(self):
        reply = QMessageBox.question(
            self,
            "Confirm Clear All",
            "Delete all feeds and cache?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.feed_mgr.delete_all_feeds()
            self.current_feed_url = None
            self.load_feeds()

    def load_feeds(self):
        self.feed_list.clear()
        feeds = self.feed_mgr.get_feed_list()
        
        for url in feeds:
            data = self.feed_mgr.get_feed_data(url)
            if data and hasattr(data, 'feed'):
                title = getattr(data.feed, 'title', url)
            else:
                title = url
            
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, url)
            self.feed_list.addItem(item)
        
        self.entry_tree.clear()
        self.all_entries = []
        self.filtered_entries = []
        self.detail_text.clear()
        
        if self.feed_list.count() > 0:
            self.feed_list.setCurrentRow(0)

    def on_feed_changed(self, current, previous):
        if not current:
            return
        
        url = current.data(Qt.ItemDataRole.UserRole)
        self.current_feed_url = url
        self.load_feed_entries(url)

    def load_feed_entries(self, url):
        data = self.feed_mgr.get_feed_data(url)
        
        if not data or not hasattr(data, 'entries') or not data.entries:
            progress = QProgressDialog("Fetching feed...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            try:
                data = self.feed_mgr.refresh_feed(url, force=True)
            except:
                data = None
            finally:
                progress.close()
        
        if data and hasattr(data, 'entries'):
            self.all_entries = list(data.entries)
            self.filtered_entries = self.all_entries[:]
            self.sort_entries(self.sort_key, self.sort_reverse)
        else:
            self.all_entries = []
            self.filtered_entries = []
            self.update_entry_tree()
            self.detail_text.setPlainText("No entries found for this feed.")

    def perform_search(self):
        query = self.search_box.text().strip()
        if not query:
            self.filtered_entries = self.all_entries[:]
        else:
            self.filtered_entries = self.feed_mgr.search_entries(
                query, 
                fields=['title', 'summary', 'description', 'author'],
                entries=self.all_entries
            )
        self.sort_entries(self.sort_key, self.sort_reverse)

    def clear_search(self):
        self.search_box.clear()
        self.perform_search()

    def sort_entries(self, key='published_parsed', reverse=True):
        self.sort_key = key
        self.sort_reverse = reverse
        self.filtered_entries = self.feed_mgr.sort_entries(
            self.filtered_entries, 
            key=key, 
            reverse=reverse
        )
        self.update_entry_tree()

    def get_entry_value(self, entry, field):
        val = None
        if isinstance(entry, dict):
            val = entry.get(field)
        elif hasattr(entry, field):
            val = getattr(entry, field, None)
        
        if val is None and hasattr(entry, 'keys') and callable(entry.keys):
            try:
                val = entry[field]
            except:
                pass
        
        return val

    def format_date(self, entry):
        date_val = self.get_entry_value(entry, 'published')
        if not date_val:
            date_val = self.get_entry_value(entry, 'updated')
        
        parsed = self.get_entry_value(entry, 'published_parsed')
        if not parsed:
            parsed = self.get_entry_value(entry, 'updated_parsed')
        
        if parsed:
            try:
                dt = datetime.fromtimestamp(mktime(parsed))
                return dt.strftime("%Y-%m-%d %H:%M")
            except:
                pass
        
        return str(date_val) if date_val else "N/A"

    def update_entry_tree(self):
        self.entry_tree.clear()
        
        for entry in self.filtered_entries:
            title = self.get_entry_value(entry, 'title') or "Untitled"
            published = self.format_date(entry)
            link = self.get_entry_value(entry, 'link') or ""
            
            title_display = title[:100] + "..." if len(title) > 100 else title
            link_display = link[:50] + "..." if len(link) > 50 else link
            
            item = QTreeWidgetItem([title_display, published, link_display])
            item.setData(0, Qt.ItemDataRole.UserRole, entry)
            
            desc = f"Entry: {title}, Published: {published}, Link: {link}"
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            
            self.entry_tree.addTopLevelItem(item)
        
        if self.entry_tree.topLevelItemCount() > 0:
            item = self.entry_tree.topLevelItem(0)
            if item:
                self.entry_tree.setCurrentItem(item)
        else:
            self.detail_text.setPlainText("No entries match your search.")

    def on_entry_changed(self, current, previous):
        if not current:
            return
        
        entry = current.data(0, Qt.ItemDataRole.UserRole)
        if entry:
            self.display_entry_detail(entry)

    def display_entry_detail(self, entry):
        html_parts = []
        html_parts.append("<div style='font-family: Arial, sans-serif; padding: 10px; line-height: 1.6;'>")
        
        for field in self.LONG_TEXT_FIELDS:
            val = self.get_entry_value(entry, field)
            if val:
                field_title = field.replace('_', ' ').title()
                html_parts.append(f"<h3 style='color: #2c3e50; border-bottom: 1px solid #ccc; margin-top: 15px;'>{field_title}</h3>")
                
                content_html = ""
                if isinstance(val, list) and val:
                    for item in val:
                        if isinstance(item, dict) and 'value' in item:
                            content_html += item['value']
                        else:
                            content_html += str(item)
                elif isinstance(val, dict) and 'value' in val:
                    content_html = val['value']
                elif isinstance(val, str):
                    content_html = val
                
                allowed_tags = [
                    'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code',
                    'pre', 'div', 'span', 'img', 'table', 'thead', 'tbody',
                    'tr', 'th', 'td', 'hr'
                ]
                allowed_attrs = {
                    '*': ['class', 'id', 'style'],
                    'a': ['href', 'title', 'target'],
                    'img': ['src', 'alt', 'title', 'width', 'height']
                }
                sanitized = bleach.clean(
                    content_html,
                    tags=allowed_tags,
                    attributes=allowed_attrs,
                    strip=True
                )
                html_parts.append(f"<div style='margin-left: 10px;'>{sanitized}</div>")
        
        html_parts.append("</div>")
        
        if len(html_parts) > 2:
            self.detail_text.setHtml(''.join(html_parts))
        else:
            self.detail_text.setHtml("<p><em>No summary or description available.</em></p>")

    def show_full_entry(self, item):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if entry:
            dialog = EntryDetailDialog(entry, self)
            dialog.exec()

    def open_entry_link(self, item):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if entry:
            link = self.get_entry_value(entry, 'link')
            if link:
                QDesktopServices.openUrl(QUrl(link))

    def copy_direct_media_link(self, item):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        media_url = self.feed_mgr.get_direct_media_url(entry)
        if media_url:
            clipboard = QApplication.clipboard()
            clipboard.setText(media_url)
            QMessageBox.information(self, "Copied", f"Direct media link copied to clipboard:\n{media_url}")
        else:
            QMessageBox.warning(self, "Not Found", "No direct media link found for this entry.")
    
    def play_entry(self, item):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        media_url = self.feed_mgr.get_direct_media_url(entry)
        if media_url:
            self.play_requested.emit(media_url)
        else:
            QMessageBox.warning(self, "No Media", "No direct media link found for this entry.")

    def copy_entry_field(self, item, field):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        value = self.get_entry_value(entry, field)
        if value:
            if isinstance(value, list) and value:
                value = value[0].get('name', str(value[0])) if isinstance(value[0], dict) else str(value[0])
            QApplication.clipboard().setText(str(value))

    def select_next_entry(self):
        current = self.entry_tree.currentItem()
        if current:
            index = self.entry_tree.indexOfTopLevelItem(current)
            if index < self.entry_tree.topLevelItemCount() - 1:
                item = self.entry_tree.topLevelItem(index + 1)
                if item:
                    self.entry_tree.setCurrentItem(item)

    def select_prev_entry(self):
        current = self.entry_tree.currentItem()
        if current:
            index = self.entry_tree.indexOfTopLevelItem(current)
            if index > 0:
                item = self.entry_tree.topLevelItem(index - 1)
                if item:
                    self.entry_tree.setCurrentItem(item)

    def select_page_down(self):
        current = self.entry_tree.currentItem()
        if current:
            index = self.entry_tree.indexOfTopLevelItem(current)
            viewport_height = self.entry_tree.viewport().height()
            row_height = self.entry_tree.sizeHintForRow(0) if self.entry_tree.topLevelItemCount() > 0 else 20
            visible_rows = max(1, viewport_height // max(1, row_height))
            new_index = min(index + visible_rows, self.entry_tree.topLevelItemCount() - 1)
            item = self.entry_tree.topLevelItem(new_index)
            if item:
                self.entry_tree.setCurrentItem(item)

    def select_page_up(self):
        current = self.entry_tree.currentItem()
        if current:
            index = self.entry_tree.indexOfTopLevelItem(current)
            viewport_height = self.entry_tree.viewport().height()
            row_height = self.entry_tree.sizeHintForRow(0) if self.entry_tree.topLevelItemCount() > 0 else 20
            visible_rows = max(1, viewport_height // max(1, row_height))
            new_index = max(index - visible_rows, 0)
            item = self.entry_tree.topLevelItem(new_index)
            if item:
                self.entry_tree.setCurrentItem(item)

    def select_first_entry(self):
        if self.entry_tree.topLevelItemCount() > 0:
            item = self.entry_tree.topLevelItem(0)
            if item:
                self.entry_tree.setCurrentItem(item)

    def select_last_entry(self):
        count = self.entry_tree.topLevelItemCount()
        if count > 0:
            item = self.entry_tree.topLevelItem(count - 1)
            if item:
                self.entry_tree.setCurrentItem(item)
