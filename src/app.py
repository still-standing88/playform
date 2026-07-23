import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from utilities.i18n import install_translation
from utilities.functions import setup_mpv_binaries
from app_info import APP_NAME, APP_VERSION, APP_PUBLISHER, APP_WEBSITE, setup_env

def main():
    cli_args = sys.argv

    setup_env()
    setup_mpv_binaries()
    install_translation()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_PUBLISHER)
    app.setOrganizationDomain(APP_WEBSITE)
    
    from loading import LoadingSplash
    splash = LoadingSplash()
    splash.show()
    app.processEvents()
    
    try:
        from app_init import (
            setup_environment,
            setup_application_style,
            initialize_app_guard,
            initialize_modules,
            create_main_window,
            start_local_server,
            setup_ipc_handlers,
            setup_cleanup
        )
        
        BASE_DIR = setup_environment()
        setup_application_style(app)
        app_instance, should_exit = initialize_app_guard(cli_args)

        if should_exit:
            splash.close()

            sys.exit(0)
        app_db, key_config = initialize_modules(splash)
        window = create_main_window(splash, cli_args)
        start_local_server(window)
        setup_ipc_handlers(app_instance, window)
        key_config.initialize(window.global_hotkeys)
        key_config.apply_global_hotkeys()
        setup_cleanup(app, app_instance, app_db)
        
        splash.update_message(_("Starting application..."))
        splash.finish(window)
        window.show()
        if len(cli_args) > 1 and app_instance:
            app_instance.focus_window("PlayForm")
        
        exit_code = app.exec()
    except Exception as e:
        splash.close()
        exc_t = sys.exc_info()[2]
        raise Exception(f"Error: {e}").with_traceback(exc_t)
        exit_code = 1
    from utilities.functions import get_restart_flag, set_restart_flag, restart_app
    if get_restart_flag():
        set_restart_flag(False)
        restart_app()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
