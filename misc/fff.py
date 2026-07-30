# test_appguard.py
import time
import sys
import os

# Make sure the app_guard package (containing the .pyd) is in the Python path.
# If you ran `python setup.py build_ext --inplace`, the .pyd is in ./app_guard/
# This adds the current directory to sys.path to find the 'app_guard' package.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    import app_guard
except ImportError as e:
    print(f"Failed to import app_guard: {e}")
    print("Ensure the AppGuard extension is built and in the app_guard/ directory (e.g., app_guard.cpXYZ-win_amd64.pyd).")
    print("You might need to run: scons build_python=1")
    sys.exit(1)

APP_UNIQUE_HANDLE = "MyUniqueTestApp_AppGuard"
IPC_MSG_HANDLE_GREETING = "GreetingFromSecondary"

# --- Callback Functions ---
def on_app_quit_callback():
    pid = app_guard.AG_get_process_id()
    print(f"[PID {pid}] AppGuard 'on_quit_callback' triggered. Application instance is exiting.")

def ipc_message_handler(msg_data):
    """
    Handles incoming IPC messages.
    msg_data is expected to be a dictionary:
    {
        "msg_handle": "handle_string",
        "msg_data": "data_string_or_None"
    }
    """
    pid = app_guard.AG_get_process_id()
    print(f"[PID {pid}] Received IPC Message:")
    print(f"  Handle: {msg_data.get('msg_handle')}")
    print(f"  Data:   {msg_data.get('msg_data')}")
    print("-" * 30)

    # Example: if primary receives a greeting, it could try to focus the secondary
    # (This is just an example, focus_window might not always work depending on OS/window state)
    # if msg_data.get('msg_handle') == IPC_MSG_HANDLE_GREETING and msg_data.get('msg_data'):
    #     try:
    #         secondary_pid_str = msg_data.get('msg_data')
    #         # This is a placeholder - you'd need a way to get the window name from PID
    #         # window_name_to_focus = f"Window Of App PID {secondary_pid_str}"
    #         # print(f"[PID {pid}] Attempting to focus window: {window_name_to_focus}")
    #         # app_guard.AG_focus_window(window_name_to_focus) # Needs a valid window name
    #     except Exception as e:
    #         print(f"[PID {pid}] Error processing focus for secondary: {e}")


def main():
    print("--- AppGuard Python Test Program ---")

    # 1. Initialize AppGuard
    # quit_immediate = False means the secondary instance won't quit immediately
    # if another instance is already primary.
    try:
        app_guard.AG_init(APP_UNIQUE_HANDLE, on_app_quit_callback, quit_immediate=False)
    except Exception as e:
        print(f"Error during AG_init: {e}")
        return

    if not app_guard.AG_is_loaded():
        print("AppGuard failed to load properly.")
        return

    current_pid = app_guard.AG_get_process_id()
    print(f"[PID {current_pid}] AppGuard Initialized.")

    # 2. Check if this is the primary instance
    is_primary = app_guard.AG_is_primary_instance()

    if is_primary:
        print(f"[PID {current_pid}] This is the PRIMARY instance.")

        # 3a. Primary: Register an IPC message handler
        try:
            # Create an IPCMsg object (Python side representation)
            ipc_msg_obj = app_guard.IPCMsg() 
            app_guard.AG_create_IPCMsg(ipc_msg_obj, IPC_MSG_HANDLE_GREETING, ipc_message_handler)
            
            print(f"[PID {current_pid}] Created IPCMsg object: ID={ipc_msg_obj.msg_id}, Handle='{ipc_msg_obj.msg_handle}'")
            
            app_guard.AG_register_msg(ipc_msg_obj)
            print(f"[PID {current_pid}] Registered IPC message handler for '{IPC_MSG_HANDLE_GREETING}'.")
        except Exception as e:
            print(f"[PID {current_pid}] Error setting up IPC message for primary: {e}")
            app_guard.AG_release()
            return

        print(f"[PID {current_pid}] Primary instance running. Waiting for messages or other instances...")
        print("Try running another instance of this script.")
        
        try:
            # Keep primary alive to receive messages
            # The C++ library likely has its own thread for IPC, so Python just needs to stay alive.
            # AG_is_primary_instance() might become false if something external kills the primary's mechanism.
            count = 0
            while app_guard.AG_is_loaded() and app_guard.AG_is_primary_instance() and count < 1200: # Run for max 60 seconds
                time.sleep(0.05) # Small sleep to reduce CPU usage
                count +=1
                if count % 200 == 0 : # Print a heartbeat every 10 seconds
                    print(f"[PID {current_pid}] Primary still alive...")
            print(f"[PID {current_pid}] Primary instance loop finished or AppGuard no longer primary/loaded.")

        except KeyboardInterrupt:
            print(f"\n[PID {current_pid}] Primary instance interrupted by user.")
        finally:
            # Unregister the message (optional, AG_release should clean up)
            try:
                if 'ipc_msg_obj' in locals() and ipc_msg_obj.msg_id != 0: # Check if ipc_msg_obj was created
                    print(f"[PID {current_pid}] Unregistering IPC message ID: {ipc_msg_obj.msg_id}")
                    app_guard.AG_unregister_msg(ipc_msg_obj.msg_id)
            except Exception as e:
                 print(f"[PID {current_pid}] Error during AG_unregister_msg: {e}")


    else: # This is a secondary instance
        print(f"[PID {current_pid}] This is a SECONDARY instance.")
        
        # 3b. Secondary: Send an IPC message
        print(f"[PID {current_pid}] Sending greeting message to primary instance.")
        message_content = f"Hello from secondary instance, PID {current_pid}"
        try:
            app_guard.AG_send_msg_request(IPC_MSG_HANDLE_GREETING, message_content)
            print(f"[PID {current_pid}] Message sent.")
        except Exception as e:
            print(f"[PID {current_pid}] Error sending IPC message: {e}")
        
        # Secondary instance might exit or do other work.
        # If quit_immediate was true in AG_init and this was secondary,
        # the C library might have already queued an exit.
        # If quit_immediate is false, it continues.
        print(f"[PID {current_pid}] Secondary instance will now exit after a short delay.")
        time.sleep(2) # Keep it alive for a moment to see messages

    # 4. Release AppGuard resources
    print(f"[PID {current_pid}] Releasing AppGuard...")
    try:
        app_guard.AG_release()
        print(f"[PID {current_pid}] AppGuard Released.")
    except Exception as e:
        print(f"[PID {current_pid}] Error during AG_release: {e}")
    
    print("--- Test Program Finished ---")

if __name__ == "__main__":
    main()