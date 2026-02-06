import os
import sys
from pathlib import Path

def get_parent_dir():
    return Path(__file__).parent.parent

def create_qrc_file():
    parent_dir = get_parent_dir()
    assets_dir = os.path.join(parent_dir, "assets", "icons")
    
    if not os.path.isdir(assets_dir):
        print(f"Assets directory not found: {assets_dir}")
        return False
    
    qrc_content = ['<RCC>', '  <qresource prefix="icons">']
    
    icon_files = [f for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f))]
    
    for icon_file in icon_files:
        rel_path = os.path.join("assets", "icons", icon_file).replace('\\', '/')
        qrc_content.append(f'    <file>../../{rel_path}</file>')
    
    qrc_content.extend(['  </qresource>', '</RCC>'])
    
    qrc_file_path = os.path.join(parent_dir, "src", "assets.qrc")
    with open(qrc_file_path, 'w') as f:
        f.write('\n'.join(qrc_content))
    
    print(f"Created {qrc_file_path}")
    return True

def compile_qrc():
    parent_dir = get_parent_dir()
    qrc_file = os.path.join(parent_dir, "src", "assets.qrc")
    output_file = os.path.join(parent_dir, "src", "assets_rc.py")
    
    if not os.path.exists(qrc_file):
        print(f"QRC file not found: {qrc_file}")
        return False
    
    try:
        import subprocess
        result = subprocess.run(['pyside6-rcc', qrc_file, '-o', output_file], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Compiled assets to {output_file}")
            return True
        else:
            print(f"Error compiling QRC: {result.stderr}")
            return False
    except FileNotFoundError:
        print("pyside6-rcc not found. Install PySide6 tools.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Creating QRC file...")
    if create_qrc_file():
        print("Compiling QRC to Python resource module...")
        compile_qrc()
    else:
        print("Failed to create QRC file")
        sys.exit(1)
