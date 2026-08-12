import os
import bleach

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QTextBrowser,
    QMenu, QMessageBox, QInputDialog, QProgressDialog, QHeaderView, QApplication
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices

from urllib.parse import urlparse
from datetime import datetime
from time import mktime

from utilities.functions import get_app_path
from media_core.podcasts.feed_manager import FeedManager
from media_providers.podcasts.entry_detail_dialog import EntryDetailDialog


class FeedWidget(QWidget):
    play_requested = Signal(str)
    
    COMMON_FIELDS = ['title', 'published', 'link']
    LONG_TEXT_FIELDS = ['summary', 'description', 'content']
    BLACKLIST = ['published_parsed', 'updated_parsed', 'guidislink', 
                 'title_detail', 'summary_detail', 'author_detail', 
                 'links', 'content']
    
    @staticmethod
    def _migrate_legacy_cache_dir(legacy_cache_dir, cache_dir):
        if not os.path.isdir(legacy_cache_dir) or os.path.abspath(legacy_cache_dir) == os.path.abspath(cache_dir):
            return
        try:
            os.makedirs(cache_dir, exist_ok=True)
            for name in os.listdir(legacy_cache_dir):
                src = os.path.join(legacy_cache_dir, name)
                dst = os.path.join(cache_dir, name)
                try:
                    os.replace(src, dst)
                except Exception:
                    pass
            try:
                os.rmdir(legacy_cache_dir)
            except Exception:
                pass
        except Exception:
            pass

    def __init__(self, parent=None):
        super().__init__(parent)
        # Lives under data/cache/ alongside the radio cache -- a single
        # shared cache root under data/ instead of a top-level-of-data
        # podcast_cache/ directory.
        cache_dir = os.path.join(get_app_path(), 'data', 'cache', 'podcasts')
        legacy_cache_dir = os.path.join(get_app_path(), 'data', 'podcast_cache')
        self._migrate_legacy_cache_dir(legacy_cache_dir, cache_dir)
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
        search_label = QLabel(_("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(_("Type and press Enter to search entries..."))
        self.search_box.returnPressed.connect(self.perform_search)
        search_btn = QPushButton(_("Search"))
        search_btn.clicked.connect(self.perform_search)
        clear_btn = QPushButton(_("Clear"))
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
        feed_label = QLabel(_("<b>Feeds</b>"))
        feed_layout.addWidget(feed_label)
        
        self.feed_list = QListWidget()
        self.feed_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.feed_list.customContextMenuRequested.connect(self.show_feed_context_menu)
        self.feed_list.setAlternatingRowColors(True)
        self.feed_list.currentItemChanged.connect(self.on_feed_changed)
        self.feed_list.setAccessibleName(_("Feed List"))
        self.feed_list.setAccessibleDescription(_("List of RSS feeds. Right-click for options."))
        feed_layout.addWidget(self.feed_list)
        
        splitter.addWidget(feed_container)
        
        entry_container = QWidget()
        entry_layout = QVBoxLayout(entry_container)
        entry_layout.setContentsMargins(0, 0, 0, 0)
        entry_label = QLabel(_("<b>Entries</b>"))
        entry_layout.addWidget(entry_label)
        
        self.entry_tree = QTreeWidget()
        self.entry_tree.setColumnCount(3)
        self.entry_tree.setHeaderLabels([_("Title"), _("Published"), _("Link")])
        self.entry_tree.setAlternatingRowColors(True)
        self.entry_tree.setRootIsDecorated(False)
        self.entry_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.entry_tree.customContextMenuRequested.connect(self.show_entry_context_menu)
        self.entry_tree.currentItemChanged.connect(self.on_entry_changed)
        self.entry_tree.itemDoubleClicked.connect(lambda item, _column: self.play_entry(item))
        self.entry_tree.setAccessibleName(_("Entry Tree"))
        self.entry_tree.setAccessibleDescription(_("Tree of feed entries with title, date, and link. Right-click for options."))
        self.entry_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.entry_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.entry_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        entry_layout.addWidget(self.entry_tree, 2)
        
        detail_label = QLabel(_("<b>Summary/Description</b>"))
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
        self.detail_text.setAccessibleName(_("Entry Detail Text"))
        self.detail_text.setAccessibleDescription(_("Summary and description of selected entry"))
        entry_layout.addWidget(self.detail_text, 1)
        
        splitter.addWidget(entry_container)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)

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
                return False, str(exception) if exception else _("Invalid feed format")
            return False, _("Failed to parse feed")
        except Exception as e:
            return False, str(e)

    def show_feed_context_menu(self, pos):
        menu = QMenu(self)
        
        add_action = QAction(_("Add Feed"), self)
        add_action.triggered.connect(self.add_feed)
        menu.addAction(add_action)
        
        item = self.feed_list.itemAt(pos)
        if item:
            menu.addSeparator()
            
            refresh_action = QAction(_("Refresh Feed"), self)
            refresh_action.triggered.connect(self.refresh_current_feed)
            menu.addAction(refresh_action)
            
            update_url_action = QAction(_("Update Feed URL"), self)
            update_url_action.triggered.connect(self.update_feed_url)
            menu.addAction(update_url_action)
            
            remove_action = QAction(_("Remove Feed"), self)
            remove_action.triggered.connect(self.remove_feed)
            menu.addAction(remove_action)
        
        if self.feed_list.count() > 0:
            menu.addSeparator()
            
            refresh_all_action = QAction(_("Refresh All Feeds"), self)
            refresh_all_action.triggered.connect(self.refresh_all_feeds)
            menu.addAction(refresh_all_action)
            
            clear_action = QAction(_("Clear All Feeds"), self)
            clear_action.triggered.connect(self.clear_all_feeds)
            menu.addAction(clear_action)
        
        menu.exec(self.feed_list.viewport().mapToGlobal(pos))

    def show_entry_context_menu(self, pos):
        item = self.entry_tree.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        sort_menu = menu.addMenu(_("Sort By"))
        
        sort_title_asc = QAction(_("Title (Ascending A-Z)"), self)
        sort_title_asc.triggered.connect(lambda: self.sort_entries('title', False))
        sort_menu.addAction(sort_title_asc)
        
        sort_title_desc = QAction(_("Title (Descending Z-A)"), self)
        sort_title_desc.triggered.connect(lambda: self.sort_entries('title', True))
        sort_menu.addAction(sort_title_desc)
        
        sort_menu.addSeparator()
        
        sort_date_newest = QAction(_("Date (Newest First)"), self)
        sort_date_newest.triggered.connect(lambda: self.sort_entries('published_parsed', True))
        sort_menu.addAction(sort_date_newest)
        
        sort_date_oldest = QAction(_("Date (Oldest First)"), self)
        sort_date_oldest.triggered.connect(lambda: self.sort_entries('published_parsed', False))
        sort_menu.addAction(sort_date_oldest)
        
        menu.addSeparator()
        
        copy_menu = menu.addMenu(_("Copy"))
        
        copy_title = QAction(_("Title"), self)
        copy_title.triggered.connect(lambda: self.copy_entry_field(item, 'title'))
        copy_menu.addAction(copy_title)
        
        copy_link = QAction(_("Page Link"), self)
        copy_link.triggered.connect(lambda: self.copy_entry_field(item, 'link'))
        copy_menu.addAction(copy_link)
        
        copy_media = QAction(_("Direct Media Link"), self)
        copy_media.triggered.connect(lambda: self.copy_direct_media_link(item))
        copy_menu.addAction(copy_media)
        
        menu.addSeparator()

        play_entry_action = QAction(_("Play Entry"), self)
        play_entry_action.triggered.connect(lambda: self.play_entry(item))
        menu.addAction(play_entry_action)

        full_entry_action = QAction(_("View Full Entry Dump"), self)
        full_entry_action.triggered.connect(lambda: self.show_full_entry(item))
        menu.addAction(full_entry_action)
        
        open_link_action = QAction(_("Open Link in Browser"), self)
        open_link_action.triggered.connect(lambda: self.open_entry_link(item))
        menu.addAction(open_link_action)
        
        menu.exec(self.entry_tree.viewport().mapToGlobal(pos))

    def add_feed(self):
        url, ok = QInputDialog.getText(self, _("Add Feed"), _("Enter feed URL:"))
        if not ok or not url:
            return
        
        if not self.validate_url(url):
            QMessageBox.warning(self, _("Invalid URL"), _("Please enter a valid HTTP/HTTPS URL"))
            return
        
        if url in self.feed_mgr.get_feed_list():
            QMessageBox.warning(self, _("Duplicate"), _("Feed already exists"))
            return
        
        progress = QProgressDialog(_("Validating feed..."), _("Cancel"), 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        valid, error = self.validate_feed(url)
        progress.close()
        
        if not valid:
            QMessageBox.critical(
                self,
                _("Invalid Feed"),
                _("Feed validation failed:\n{error}").format(error=error),
            )
            self.feed_mgr.remove_feed(url)
            return
        
        self.feed_mgr.add_feed(url)
        QMessageBox.information(self, _("Success"), _("Feed added successfully"))
        self.load_feeds()

    def remove_feed(self):
        item = self.feed_list.currentItem()
        if not item:
            return
        
        url = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            _("Confirm Removal"),
            _("Remove feed:\n{url}?").format(url=url),
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
        progress = QProgressDialog(_("Refreshing feed..."), _("Cancel"), 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        try:
            result = self.feed_mgr.refresh_feed(url, force=True)
            progress.close()
            if result:
                QMessageBox.information(self, _("Success"), _("Feed refreshed successfully"))
                self.load_feed_entries(url)
            else:
                QMessageBox.warning(self, _("Error"), _("Failed to refresh feed"))
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                _("Error"),
                _("Refresh failed:\n{error}").format(error=str(e)),
            )

    def refresh_all_feeds(self):
        feeds = self.feed_mgr.get_feed_list()
        if not feeds:
            return
        
        progress = QProgressDialog(_("Refreshing feeds..."), _("Cancel"), 0, len(feeds), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        
        for i, url in enumerate(feeds):
            if progress.wasCanceled():
                break
            progress.setValue(i)
            progress.setLabelText(_("Refreshing:\n{url}...").format(url=url[:60]))
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
        new_url, ok = QInputDialog.getText(self, _("Update Feed URL"), _("Enter new URL:"), text=old_url)
        
        if not ok or not new_url or new_url == old_url:
            return
        
        if not self.validate_url(new_url):
            QMessageBox.warning(self, _("Invalid URL"), _("Please enter a valid HTTP/HTTPS URL"))
            return
        
        progress = QProgressDialog(_("Validating new feed URL..."), _("Cancel"), 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        valid, error = self.validate_feed(new_url)
        progress.close()
        
        if not valid:
            QMessageBox.critical(
                self,
                _("Invalid Feed"),
                _("Feed validation failed:\n{error}").format(error=error),
            )
            self.feed_mgr.remove_feed(new_url)
            return
        
        self.feed_mgr.update_feed_url(old_url, new_url)
        QMessageBox.information(self, _("Success"), _("Feed URL updated successfully"))
        self.load_feeds()

    def clear_all_feeds(self):
        reply = QMessageBox.question(
            self,
            _("Confirm Clear All"),
            _("Delete all feeds and cache?"),
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
            self.detail_text.setPlainText(_("No entries found for this feed."))

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
        
            return str(date_val) if date_val else _("N/A")

    def update_entry_tree(self):
        self.entry_tree.clear()
        
        for entry in self.filtered_entries:
            title = self.get_entry_value(entry, 'title') or _("Untitled")
            published = self.format_date(entry)
            link = self.get_entry_value(entry, 'link') or ""
            
            title_display = title[:100] + "..." if len(title) > 100 else title
            link_display = link[:50] + "..." if len(link) > 50 else link
            
            item = QTreeWidgetItem([title_display, published, link_display])
            item.setData(0, Qt.ItemDataRole.UserRole, entry)
            
            desc = _("Entry: {title}, Published: {published}, Link: {link}").format(
                title=title,
                published=published,
                link=link,
            )
            item.setData(0, Qt.ItemDataRole.AccessibleDescriptionRole, desc)
            
            self.entry_tree.addTopLevelItem(item)
        
        if self.entry_tree.topLevelItemCount() > 0:
            item = self.entry_tree.topLevelItem(0)
            if item:
                self.entry_tree.setCurrentItem(item)
        else:
            self.detail_text.setPlainText(_("No entries match your search."))

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
            self.detail_text.setHtml(_("<p><em>No summary or description available.</em></p>"))

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
            QMessageBox.information(
                self,
                _("Copied"),
                _("Direct media link copied to clipboard:\n{media_url}").format(
                    media_url=media_url
                ),
            )
        else:
            QMessageBox.warning(self, _("Not Found"), _("No direct media link found for this entry."))
    
    def play_entry(self, item):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        media_url = self.feed_mgr.get_direct_media_url(entry)
        if media_url:
            self.play_requested.emit(media_url)
        else:
            QMessageBox.warning(self, _("No Media"), _("No direct media link found for this entry."))

    def copy_entry_field(self, item, field):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        
        value = self.get_entry_value(entry, field)
        if value:
            if isinstance(value, list) and value:
                value = value[0].get('name', str(value[0])) if isinstance(value[0], dict) else str(value[0])
            QApplication.clipboard().setText(str(value))
