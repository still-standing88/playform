import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

def main():
    cli_args = sys.argv
    
    app = QApplication(sys.argv)
    app.setApplicationName("PlayForm")
    app.setApplicationVersion("1.0.0")
    
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
            setup_ipc_handlers,
            setup_cleanup
        )
        
        splash.update_message("Setting up environment...")
        BASE_DIR = setup_environment()
        
        splash.update_message("Configuring application style...")
        setup_application_style(app)
        
        splash.update_message("Checking application instance...")
        app_instance, should_exit = initialize_app_guard(cli_args)
        
        if should_exit:
            splash.close()
            sys.exit(0)
        
        app_db, key_config = initialize_modules(splash)
        
        window = create_main_window(splash, cli_args)
        
        splash.update_message("Setting up IPC handlers...")
        setup_ipc_handlers(app_instance, window)
        
        splash.update_message("Initializing hotkeys...")
        key_config.initialize(window.global_hotkeys)
        
        setup_cleanup(app, app_instance, app_db)
        
        splash.update_message("Starting application...")
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
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()