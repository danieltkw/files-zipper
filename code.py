




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

# // ------------------------------------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def log_message(log_path, message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_path, 'a', encoding='utf-8') as logf:
        logf.write(f"[{timestamp}] {message}\n")
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def get_all_files(base_folder, exclude_filename, max_depth=None, extensions=None):
    file_paths = []
    for root, dirs, files in os.walk(base_folder):
        if max_depth is not None:
            depth = root[len(base_folder):].count(os.sep)
            if depth >= max_depth:
                dirs[:] = []
        for file in files:
            full_path = os.path.join(root, file)
            if extensions and not any(file.endswith(ext) for ext in extensions):
                continue
            if os.path.abspath(full_path) != os.path.abspath(exclude_filename):
                file_paths.append(full_path)
    return file_paths
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def find_7z_executable():
    common_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe"
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path
    return "7z"
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def archive_already_exists(file_path):
    dir_ = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    archive_exts = [".zip", ".7z", ".rar", ".gz", ".xz", ".bz2", ".tar", ".tar.gz", ".tar.xz"]

    for fname in os.listdir(dir_):
        if not fname.startswith(base_name):
            continue
        suffix = fname[len(base_name):].lower()
        if any(
            suffix == ext or suffix == (ext + ext)
            for ext in archive_exts
        ):
            return True
    return False
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def create_encrypted_7z(original_file_path, password, seven_zip_path):
    temp_dir = tempfile.mkdtemp()
    basename = os.path.basename(original_file_path)
    temp_input = os.path.join(temp_dir, basename)

    if not os.path.isfile(original_file_path):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"File not found: {original_file_path}"

    try:
        shutil.copy2(original_file_path, temp_input)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"Copy error: {e}"

    random_hash = str(uuid.uuid4())
    temp_7z_path = os.path.join(temp_dir, random_hash + ".7z")

    try:
        subprocess.run([
            seven_zip_path, "a", "-t7z",
            "-mx=9", "-mhe=on", "-m0=lzma2", "-md=256m", "-ms=16g", "-mmt=on",
            f"-p{password}", temp_7z_path, basename
        ], cwd=temp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"7z error: {e.stderr.strip()}"

    final_path = os.path.join(os.path.dirname(original_file_path), random_hash)
    try:
        shutil.move(temp_7z_path, final_path)
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None, f"Move error: {e}"

    shutil.rmtree(temp_dir, ignore_errors=True)
    return final_path, None
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def wrap_in_zip(formatless_path, destination_folder, original_name):
    zip_path = os.path.join(destination_folder, original_name + ".zip")
    try:
        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
            arcname = os.path.basename(formatless_path)
            zipf.write(formatless_path, arcname)
        try:
            os.remove(formatless_path)
        except Exception as e:
            return False, f"Failed to remove formatless file: {e}"
        return True, None
    except Exception as e:
        return False, str(e)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def main():
    clear_screen()
    folder = os.path.dirname(os.path.realpath(sys.argv[0]))
    print(f"Script running in directory: {folder}")
    log_path = os.path.join(folder, "log.txt")
    script_path = os.path.realpath(sys.argv[0])
    seven_zip_path = find_7z_executable()

    if not os.path.isfile(seven_zip_path) or not os.access(seven_zip_path, os.X_OK):
        print("Error: 7-Zip executable not found or inaccessible. Please install 7-Zip or add it to your PATH.")
        sys.exit(1)

    # insert password for the file
    password = "pass"

    all_files = [
        f for f in get_all_files(folder, exclude_filename=script_path, max_depth=2, extensions=None)
        if not os.path.splitext(f)[1].lower() in {'.zip', '.7z', '.rar', '.gz', '.xz', '.bz2', '.tar'}
    ]

    print(f"Total files found: {len(all_files)}\n")

    errors = 0

    for file_path in tqdm(all_files, desc="Processing", unit="file"):
        print(f"\nProcessing: {file_path}")

        if archive_already_exists(file_path):
            msg = f"Skipped (already archived): {file_path}"
            log_message(log_path, msg)
            print(msg)
            continue

        formatless_path, err = create_encrypted_7z(file_path, password, seven_zip_path)
        if formatless_path is None:
            msg = f"Failed 7z: {file_path} -> {err}"
            log_message(log_path, msg)
            print(f"[ERROR] {msg}")
            errors += 1
            continue

        ok, err = wrap_in_zip(formatless_path, os.path.dirname(file_path), os.path.basename(file_path))
        if not ok:
            msg = f"Failed zip: {file_path} -> {err}"
            log_message(log_path, msg)
            print(f"[ERROR] {msg}")
            errors += 1
        else:
            msg = f"Success: {file_path}"
            log_message(log_path, msg)
            print(msg)

    print(f"\nCompleted. Total files: {len(all_files)} | Errors: {errors}")
# // ------------------------------------------------------------

if __name__ == "__main__":
    main()





