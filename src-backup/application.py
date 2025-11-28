import os
import PySide6
qt_path= os.path.dirname(PySide6.__file__)
os.environ['QT_PLUGIN_PATH'] = os.path.join(qt_path, "Qt/plugins")
from PySide6.QtWidgets import QApplication
import locale, sys, logging
from functions import messageBox
import loading
import audio
import video
import browser
import bookmarks
import gui
import hotkeys
import prefs
import error_loging
from stylesheet import stylesheet

def release():
    if browser.instance != 0: browser.player.free(browser.instance)
    browser.mediaPlayer.close()
    browser.videoInstance.close()
    if window.mediaTabs.count()>=1: window.closeAll()
    audio.mediaPlayer.close()
    if video.player is not None: video.player.close()
    prefs.prefs["lastPath"] = browser.currentDir
    prefs.save()

def onLoading():
    prefs.initialize()
    bookmarks.initialize()
    audio.initialize()
    video.initialize()

def create_window():
    global window
    window = gui.Window()

    locale.setlocale(locale.LC_NUMERIC, 'C')
    browser.initialize(window)
    window.browser_dock.setWidget(browser.window)
    hotkeys.initialize(window.global_functions)
    window.shortcuts()
    browser.window.browserList.hotkeys()
    browser.window.hide()
    browser.window.win_handle = browser.window
    window.refreshDevices()
    window.show()
    if len(sys.argv)>1:
        window.open(sys.argv[-1])
        window.isPlayerActive = True if window.mediaTabs.count()>0 else False

def main():
    global window
    app = QApplication(sys.argv)
    loading_dialog = loading.loadingDialog(onLoading)
    app.setStyleSheet(stylesheet)
    app.aboutToQuit.connect(release)
    loading_dialog.onLoadFinished.connect(create_window)
    loading_dialog.begin()
    logging.basicConfig(filename='errors.log', level=logging.ERROR, format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
#    sys.excepthook = error_loging.exception_handler
    sys.exit(app.exec())

if __name__ == "__main__":
    main()