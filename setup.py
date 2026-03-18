from setuptools import setup
from setuptools.command.install import install
import os
import subprocess
from pathlib import Path


class CustomInstall(install):
    """Custom install command that registers the icon system-wide."""
    
    def run(self):
        super().run()
        
        # Install icon to system icon directory
        icon_src = Path(__file__).resolve().parent / "openrc_manager" / "data" / "openrc-manager.svg"
        icon_dst = Path("/usr/share/icons/hicolor/scalable/apps/openrc-manager.svg")
        
        if icon_src.exists():
            # Create directory if doesn't exist
            icon_dst.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                # Copy icon file
                with open(icon_src, 'rb') as src:
                    with open(icon_dst, 'wb') as dst:
                        dst.write(src.read())
                print(f"Installed icon to {icon_dst}")
                
                # Update icon cache
                try:
                    subprocess.run(["gtk-update-icon-cache", "-f", "-t", "/usr/share/icons/hicolor"],
                                 capture_output=True)
                    print("Updated GTK icon cache")
                except FileNotFoundError:
                    print("Warning: gtk-update-icon-cache not found, icon cache not updated")
            except (OSError, PermissionError) as e:
                print(f"Warning: Could not install icon to {icon_dst}: {e}")
                print("Icon will only be available when run from source tree")


setup(
    cmdclass={'install': CustomInstall}
)
