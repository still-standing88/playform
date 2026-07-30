from PySide6.QtWidgets import QToolBox, QWidget, QVBoxLayout, QLabel

toolbox = QToolBox()

# Create content containers
library_widget = QWidget()
podcast_widget = QWidget()

# Add items to the toolbox (Widget, "Header Text")
toolbox.addItem(library_widget, "My Library")
toolbox.addItem(podcast_widget, "Podcasts")

# To change pages programmatically:
toolbox.setCurrentIndex(1)