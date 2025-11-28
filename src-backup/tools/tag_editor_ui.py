import os
import music_tag
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QFileDialog, QListWidget, QGridLayout, QMessageBox, QTextEdit
)

class TagEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.opened_files = {}
        self.current_file = None

        self.main_layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.currentItemChanged.connect(self.display_tags)
        left_panel.addWidget(self.file_list)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Files")
        self.add_button.clicked.connect(self.add_files)
        self.remove_button = QPushButton("Remove File")
        self.remove_button.clicked.connect(self.remove_file)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        left_panel.addLayout(button_layout)

        self.save_button = QPushButton("Save Current File")
        self.save_button.clicked.connect(self.save_current)
        self.save_all_button = QPushButton("Save All Files")
        self.save_all_button.clicked.connect(self.save_all)
        left_panel.addWidget(self.save_button)
        left_panel.addWidget(self.save_all_button)

        right_panel = QVBoxLayout()
        self.grid_layout = QGridLayout()
        self.tag_widgets = {}
        
        tags_to_display = [
            'tracktitle', 'artist', 'album', 'albumartist', 'composer',
            'tracknumber', 'totaltracks', 'discnumber', 'totaldiscs',
            'genre', 'year', 'comment'
        ]

        row = 0
        for tag in tags_to_display:
            label = QLabel(tag.replace('_', ' ').title() + ":")
            edit = QLineEdit()
            edit.setAccessibleName(f"{tag.replace('_', ' ').title()} tag editor")
            self.grid_layout.addWidget(label, row, 0)
            self.grid_layout.addWidget(edit, row, 1)
            self.tag_widgets[tag] = edit
            edit.textChanged.connect(self.update_tag_data)
            row += 1

        self.lyrics_edit = QTextEdit()
        self.lyrics_edit.setAccessibleName("Lyrics tag editor")
        self.grid_layout.addWidget(QLabel("Lyrics:"), row, 0)
        self.grid_layout.addWidget(self.lyrics_edit, row, 1)
        self.tag_widgets['lyrics'] = self.lyrics_edit
        self.lyrics_edit.textChanged.connect(self.update_tag_data)

        right_panel.addLayout(self.grid_layout)

        self.main_layout.addLayout(left_panel, 1)
        self.main_layout.addLayout(right_panel, 2)

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio Files",
            filter="Audio Files (*.mp3 *.flac *.m4a *.aac *.aiff *.dsf *.ogg *.opus *.wav *.wv)")
        for file_path in files:
            if file_path not in self.opened_files:
                try:
                    self.opened_files[file_path] = music_tag.load_file(file_path)
                    self.file_list.addItem(os.path.basename(file_path))
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not load {file_path}: {e}")

    def remove_file(self):
        current_item = self.file_list.currentItem()
        if current_item:
            file_path_to_remove = self.get_path_from_item(current_item)
            if file_path_to_remove in self.opened_files:
                del self.opened_files[file_path_to_remove]
            self.file_list.takeItem(self.file_list.row(current_item))
            self.clear_display()

    def get_path_from_item(self, item):
        if not item:
            return None
        filename = item.text()
        for path, file_obj in self.opened_files.items():
            if os.path.basename(path) == filename:
                # This is a fallback, but a more robust way is needed if filenames are not unique
                # For this app, we assume they are unique in the list
                return path
        return None

    def display_tags(self, current_item, previous_item):
        if not current_item:
            self.clear_display()
            return
            
        file_path = self.get_path_from_item(current_item)
        if file_path:
            self.current_file = self.opened_files[file_path]
            for tag, widget in self.tag_widgets.items():
                if self.current_file.get(tag):
                    value = self.current_file[tag].value
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(str(value))
                else:
                    if isinstance(widget, QLineEdit):
                        widget.clear()
                    elif isinstance(widget, QTextEdit):
                        widget.clear()

    def clear_display(self):
        self.current_file = None
        for widget in self.tag_widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
    
    def update_tag_data(self):
        if not self.current_file:
            return

        sender = self.sender()
        for tag, widget in self.tag_widgets.items():
            if widget is sender:
                if isinstance(widget, QLineEdit):
                    self.current_file[tag] = widget.text()
                elif isinstance(widget, QTextEdit):
                    self.current_file[tag] = widget.toPlainText()
                break

    def save_current(self):
        if self.current_file:
            try:
                self.current_file.save()
                QMessageBox.information(self, "Success", "Tags saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save tags: {e}")

    def save_all(self):
        try:
            for f in self.opened_files.values():
                f.save()
            QMessageBox.information(self, "Success", "All files saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while saving all files: {e}")