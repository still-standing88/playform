import vlc
import time

def get_all_audio_devices():
    """
    Get all available audio output devices for all audio output modules.
    Returns a dictionary mapping module names to their device lists.
    """
    print("=" * 70)
    print("GETTING ALL AUDIO DEVICES")
    print("=" * 70)
    
    instance = vlc.Instance('--no-video')
    player = instance.media_player_new()
    
    all_devices = {}
    
    # Get all audio output modules
    audio_outputs = instance.audio_output_list_get()
    
    if audio_outputs:
        current_output = audio_outputs
        while current_output:
            module_name = current_output.contents.name.decode('utf-8')
            module_desc = current_output.contents.description.decode('utf-8')
            
            print(f"\n[Module: {module_name}] - {module_desc}")
            print("-" * 70)
            
            # Get devices for this module
            devices = player.audio_output_device_enum()
            device_list = []
            
            if devices:
                current_device = devices
                device_count = 0
                while current_device:
                    device_count += 1
                    device_id = current_device.contents.device.decode('utf-8', errors='ignore')
                    device_desc = current_device.contents.description.decode('utf-8', errors='ignore')
                    
                    device_list.append({
                        'id': device_id,
                        'description': device_desc
                    })
                    
                    print(f"  [{device_count}] {device_desc}")
                    print(f"      ID: {device_id}")
                    
                    current_device = current_device.contents.next
                
                # Free the device list
                vlc.libvlc_audio_output_device_list_release(devices)
            else:
                print("  No devices available for this module")
            
            all_devices[module_name] = device_list
            current_output = current_output.contents.next
        
        # Free the audio output list
        vlc.libvlc_audio_output_list_release(audio_outputs)
    
    player.release()
    instance.release()
    return all_devices


def get_current_audio_device(player):
    """
    Get the current audio output device.
    """
    try:
        device_id = player.audio_output_device_get()
        if device_id:
            device_id = device_id.decode('utf-8', errors='ignore')
            return device_id
        return "Default/Not Set"
    except:
        return "Unable to retrieve"


def set_audio_device(player, module_name, device_id):
    """
    Set the audio output device.
    Must be called BEFORE playing media.
    CRITICAL: Must set the output module first, then the device!
    """
    print(f"\nSetting audio output:")
    print(f"  Module: {module_name}")
    print(f"  Device: {device_id}")
    
    # Step 1: Set the audio output module (REQUIRED!)
    result1 = player.audio_output_set(module_name.encode('utf-8'))
    print(f"  Module set result: {result1} (0 = success)")
    
    # Step 2: Set the specific device
    result2 = player.audio_output_device_set(None, device_id)
    print(f"  Device set result: {result2} (0 = success)")
    
    return result1 == 0 and result2 == 0


def play_test_audio(player, media_path, module_name, device_id=None):
    """
    Play audio on the specified device.
    """
    print("\n" + "=" * 70)
    print("PLAYING TEST AUDIO")
    print("=" * 70)
    
    # Set device BEFORE loading media
    if device_id:
        set_audio_device(player, module_name, device_id)
    
    # Load and play media
    media = player.get_instance().media_new(media_path)
    player.set_media(media)
    player.play()
    
    # Wait for playback to start
    time.sleep(0.5)
    
    # Show current device
    current = get_current_audio_device(player)
    print(f"Current device: {current}")
    print(f"Playing: {media_path}")
    print(f"State: {player.get_state()}")
    
    return media


def interactive_mode(all_devices):
    """
    Interactive mode to test device switching with actual audio playback.
    """
    print("\n" + "=" * 70)
    print("INTERACTIVE DEVICE TESTING")
    print("=" * 70)
    
    # Get media path from user
    media_path = input("\nEnter path to audio/video file (or press Enter to skip): ").strip()
    
    if not media_path:
        print("Skipping playback test.")
        return
    
    # Create player
    instance = vlc.Instance()
    player = instance.media_player_new()
    
    # Build device menu
    print("\nAvailable devices:")
    device_menu = []
    idx = 1
    for module_name, devices in all_devices.items():
        for device in devices:
            if device['id']:  # Skip empty IDs (default)
                print(f"  [{idx}] {device['description']} (Module: {module_name})")
                device_menu.append({'module': module_name, 'id': device['id'], 'desc': device['description']})
                idx += 1
    
    while True:
        print("\n" + "-" * 70)
        choice = input("Select device number (or 'q' to quit): ").strip()
        
        if choice.lower() == 'q':
            break
        
        try:
            device_idx = int(choice) - 1
            if 0 <= device_idx < len(device_menu):
                selected = device_menu[device_idx]
                
                # Stop current playback
                player.stop()
                time.sleep(0.2)
                
                # Play on new device
                media = play_test_audio(player, media_path, selected['module'], selected['id'])
                
                print("\nPress Enter when done listening...")
                input()
                
                # Cleanup media
                media.release()
            else:
                print("Invalid selection!")
        except ValueError:
            print("Invalid input!")
    
    # Cleanup
    player.stop()
    player.release()
    instance.release()


def main():
    # Get all devices
    all_devices = get_all_audio_devices()
    
    # Simple non-interactive test
    print("\n" + "=" * 70)
    print("SIMPLE DEVICE SETTING TEST")
    print("=" * 70)
    
    instance = vlc.Instance()
    player = instance.media_player_new()
    
    # Find first available device with an ID
    test_device = None
    test_module = None
    for module_name, devices in all_devices.items():
        for device in devices:
            if device['id']:  # Skip default (empty ID)
                test_device = device
                test_module = module_name
                break
        if test_device:
            break
    count = 0
    for module in all_devices:
        if count == 0:
            test_module = module
            break
        count +=1

    if test_device and test_module:
        print(f"\nTest: Setting device to '{test_device['description']}' (Module: {test_module})")
        success = set_audio_device(player, test_module, test_device['id'])
        
        if success:
            print("✓ Device set successfully")
            print(f"Current device: {get_current_audio_device(player)}")
        else:
            print("✗ Failed to set device")
    
    player.release()
    instance.release()
    
    # Ask if user wants interactive mode
    print("\n" + "=" * 70)
    response = input("\nWant to test with actual audio playback? (y/n): ").strip().lower()
    if response == 'y':
        interactive_mode(all_devices)


if __name__ == "__main__":
    main()