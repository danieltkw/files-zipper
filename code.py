



# // Daniel T. K. W. - github.com/danieltkw - danielkopolo95@gmail.com

"""
This script recursively processes all files in the script's directory, encrypts each file using 7-Zip with a given password,
removes the file extension from the resulting archive, and then wraps the encrypted file in a standard ZIP archive
(stored in the same folder as the original file).
"""

import os
import subprocess
import shutil
import tempfile
import uuid
from tqdm import tqdm
import zipfile
import sys
import datetime
import getpass

# // ------------------------------------------------------------
def clear_screen():
    # Clear terminal for cleaner UX (Windows/Linux/macOS)
    os.system('cls' if os.name == 'nt' else 'clear')
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def log_message(log_path, message):
    # Append timestamped log line to log file
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as logf:
        logf.write(f"[{timestamp}] {message}\n")
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def ask_password_or_default(default_password):
    """
    Ask for an encryption password at runtime.

    - If the user presses ENTER (empty input), the default password is kept.
    - Input is hidden when possible (getpass).

    Returns:
        (password: str, used_default: bool)
    """
    # Try to read a hidden password from console. If not possible, fallback to visible input.
    try:
        user_input = getpass.getpass("Password (ENTER = keep default): ").strip()
    except (Exception, KeyboardInterrupt):
        # Fallback: visible input (e.g., when stdin is not a TTY).
        try:
            user_input = input("Password (ENTER = keep default): ").strip()
        except Exception:
            user_input = ""

    # Keep default password when user did not type anything.
    if user_input == "":
        return default_password, True

    return user_input, False
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def get_all_files(base_folder, exclude_filename, max_depth=None, extensions=None):
    # Collect files recursively from base_folder, excluding exclude_filename
    file_paths = []
    for root, dirs, files in os.walk(base_folder):
        # Optionally limit recursion depth
        if max_depth is not None:
            rel_path = os.path.relpath(root, base_folder)
            if rel_path != ".":
                depth = rel_path.count(os.sep) + 1
                if depth > max_depth:
                    dirs[:] = []
                    continue

        for fname in files:
            full_path = os.path.join(root, fname)

            # Exclude this script itself (by full path match)
            if os.path.realpath(full_path) == os.path.realpath(exclude_filename):
                continue

            # Optionally filter by file extension list
            if extensions is not None:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in {e.lower() for e in extensions}:
                    continue

            file_paths.append(full_path)

    return file_paths
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def random_name_no_ext():
    # Generate a random UUID-based filename without extension
    return uuid.uuid4().hex
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def find_7z_executable():
    """
    Locate 7z.exe.
    Works for:
    - normal Python execution
    - PyInstaller --onefile bundled exe
    """
    # If running as PyInstaller bundle (7z.exe was added via --add-binary "...;.")
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
        bundled_7z = os.path.join(base_path, "7z.exe")
        if os.path.isfile(bundled_7z):
            return bundled_7z

    # Try PATH
    which = shutil.which("7z")
    if which:
        return which

    # Common Windows install paths
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    # Not found
    return None
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def encrypt_with_7z(seven_zip_path, in_file, out_7z_no_ext_path, password):
    """
    Encrypt a file using 7-Zip into a 7z archive (then rename to no-extension).

    Creates a temporary .7z first, then renames/moves to final no-extension filename.
    """
    # Build temp .7z path
    tmp_7z_path = out_7z_no_ext_path + ".7z"

    # 7z command:
    # a = add
    # -t7z = 7z format
    # -pPASSWORD = set password
    # -mhe=on = encrypt headers (file names)
    cmd = [
        seven_zip_path,
        "a",
        "-t7z",
        f"-p{password}",
        "-mhe=on",
        tmp_7z_path,
        in_file,
    ]

    # Run command and raise on errors
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Remove extension by moving/renaming
    if os.path.exists(out_7z_no_ext_path):
        os.remove(out_7z_no_ext_path)
    os.replace(tmp_7z_path, out_7z_no_ext_path)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def wrap_in_zip(no_ext_7z_path, final_zip_path):
    """
    Wrap the extension-less encrypted file into a standard ZIP archive.
    """
    # Ensure destination doesn't already exist
    if os.path.exists(final_zip_path):
        os.remove(final_zip_path)

    # Write the no-extension file as a member inside the zip
    arcname = os.path.basename(no_ext_7z_path)
    with zipfile.ZipFile(final_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(no_ext_7z_path, arcname=arcname)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def main():
    # Clear terminal at start
    clear_screen()

    # Base folder = folder of the running script/exe
    folder = os.path.dirname(os.path.realpath(sys.argv[0]))
    print(f"Script running in directory: {folder}")

    # Log file in the same folder
    log_path = os.path.join(folder, "log.txt")

    # Full path to this script/executable (used to exclude itself)
    script_path = os.path.realpath(sys.argv[0])

    # Locate 7-Zip executable
    seven_zip_path = find_7z_executable()

    # Basic validation for 7z
    if not seven_zip_path or not os.path.isfile(seven_zip_path) or not os.access(seven_zip_path, os.X_OK):
        print("Error: 7-Zip executable not found or inaccessible. Please install 7-Zip or add it to your PATH.")
        sys.exit(1)

    # Default password (used when user presses ENTER)
    default_password = "pass"

    # Ask for a password at runtime; ENTER keeps the default password
    password, used_default = ask_password_or_default(default_password)

    # Show chosen password on screen
    print(f"Chosen password: {password} (default_used={used_default})")

    # Store chosen password in the log
    log_message(log_path, f"Chosen password: {password} (default_used={used_default})")

    # Collect all candidate files (max depth 2, no extension filter)
    # Exclude archives and common compressed formats
    all_files = [
        f for f in get_all_files(folder, exclude_filename=script_path, max_depth=2, extensions=None)
        if not os.path.splitext(f)[1].lower() in {'.zip', '.7z', '.rar', '.gz', '.xz', '.bz2', '.tar'}
    ]

    print(f"Total files found: {len(all_files)}\n")

    errors = 0

    # Process each file with progress bar
    for file_path in tqdm(all_files, desc="Encrypting", unit="file"):
        try:
            # Skip log file itself to avoid self-modifying behavior
            if os.path.realpath(file_path) == os.path.realpath(log_path):
                continue

            # Generate random no-extension output name in the same directory as the original
            parent_dir = os.path.dirname(file_path)
            rnd_name = random_name_no_ext()
            out_no_ext_path = os.path.join(parent_dir, rnd_name)

            # Final zip name = original filename + ".zip" in same folder
            final_zip_path = os.path.join(parent_dir, os.path.basename(file_path) + ".zip")

            # Encrypt with 7z (produces an extension-less file)
            encrypt_with_7z(
                seven_zip_path=seven_zip_path,
                in_file=file_path,
                out_7z_no_ext_path=out_no_ext_path,
                password=password
            )

            # Wrap the encrypted file into a standard zip named after original file
            wrap_in_zip(out_no_ext_path, final_zip_path)

            # Cleanup: remove the extension-less encrypted payload after wrapping
            if os.path.exists(out_no_ext_path):
                os.remove(out_no_ext_path)

            msg = f"Success: {file_path}"
            log_message(log_path, msg)
            print(msg)

        except Exception as e:
            errors += 1
            msg = f"Error: {file_path} | {repr(e)}"
            log_message(log_path, msg)
            print(msg)

    print(f"\nCompleted. Total files: {len(all_files)} | Errors: {errors}")
# // ------------------------------------------------------------

if __name__ == "__main__":
    main()






