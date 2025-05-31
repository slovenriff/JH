import os
import sys
import subprocess
import platform
from pathlib import Path

def create_virtualenv():
    print("🔧 Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)

def install_requirements():
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print("⚠️  No requirements.txt found. Skipping dependency installation.")
        return
    pip_exec = (
        "venv\\Scripts\\pip.exe" if platform.system() == "Windows" else "venv/bin/pip"
    )
    subprocess.run([pip_exec, "install", "-r", str(req_file)], check=True)

def main():
    print("👋 Welcome to your Jyotisha Project Setup")

    if Path(".setup_done").exists():
        print("✅ Setup already completed. Delete `.setup_done` to rerun.")
        return

    choice = input("❓ Do you want to create a virtual environment and install requirements? [y/n]: ").strip().lower()
    if choice == 'y':
        create_virtualenv()
        install_requirements()
        Path(".setup_done").write_text("setup complete")
        print("🎉 Done! Activate your environment with:")
        if platform.system() == "Windows":
            print("    venv\\Scripts\\activate")
        else:
            print("    source venv/bin/activate")
    else:
        print("⚠️ Skipping setup. You’ll need to manage it manually.")

if __name__ == "__main__":
    main()
