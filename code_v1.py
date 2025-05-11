




# // Daniel T. K. W. - github.com/danieltkw - danielkopolo95@gmail.com
import os
import subprocess
import shutil
import tempfile
import uuid
from tqdm import tqdm
import zipfile

# // ------------------------------------------------------------
def get_all_files(base_folder):
    file_paths = []
    for root, _, files in os.walk(base_folder):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def create_encrypted_7z(original_file_path, password):
    temp_dir = tempfile.mkdtemp()
    try:
        shutil.copy2(original_file_path, temp_dir)
        with open(os.path.join(temp_dir, "name.txt"), "w", encoding="utf-8") as f:
            f.write(os.path.basename(original_file_path))

        uuid_name = str(uuid.uuid4())
        temp_7z_path = os.path.join(os.path.dirname(original_file_path), uuid_name + ".7z")

        subprocess.run([
            r"C:\\Program Files\\7-Zip\\7z.exe", "a", "-t7z",
            "-mx=9", "-mhe=on", "-m0=lzma2", "-md=256m", "-ms=16g", "-mmt=on",
            f"-p{password}", temp_7z_path, "*"
        ], cwd=temp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Rename to remove extension
        final_formatless_path = os.path.join(os.path.dirname(original_file_path), uuid_name)
        os.rename(temp_7z_path, final_formatless_path)

        return final_formatless_path, None
    except subprocess.CalledProcessError as e:
        return None, str(e)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def wrap_in_zip(formatless_path, original_file_path):
    final_zip_path = original_file_path + ".zip"
    try:
        with zipfile.ZipFile(final_zip_path, 'w', compression=zipfile.ZIP_STORED) as zipf:
            arcname = os.path.basename(formatless_path)  # no extension
            zipf.write(formatless_path, arcname)
        os.remove(formatless_path)
        return True, None
    except Exception as e:
        return False, str(e)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
def main():
    folder = r"C:\\Users\\Administrator\\Desktop\\aaa"
    password = "pass"

    all_files = get_all_files(folder)
    total_files = len(all_files)

    print(f"Total files found: {total_files}")
    errors = []

    for file_path in tqdm(all_files, desc="Processing files", unit="file"):
        formatless_path, err = create_encrypted_7z(file_path, password)
        if formatless_path is None:
            errors.append((file_path, f"7z error: {err}"))
            continue

        success, err = wrap_in_zip(formatless_path, file_path)
        if not success:
            errors.append((file_path, f"zip error: {err}"))

    if errors:
        print("\nErrors occurred:")
        for file_path, msg in errors:
            print(f"{file_path} -> {msg}")
    else:
        print("\nAll files processed successfully.")
# // ------------------------------------------------------------

if __name__ == "__main__":
    main()


