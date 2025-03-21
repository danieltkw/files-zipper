




# // Daniel T. K. W. - github.com/danieltkw - danielkopolo95@gmail.com
import os
import subprocess
from tqdm import tqdm

# // ------------------------------------------------------------
# Recursively collect all files in folder and subfolders
def get_all_files(base_folder):
    file_paths = []
    for root, _, files in os.walk(base_folder):
        for file in files:
            file_paths.append(os.path.join(root, file))
    return file_paths
# // ------------------------------------------------------------

# // ------------------------------------------------------------
# Compress file using 7-Zip CLI with password and ultra compression
def compress_file(file_path, password):
    archive_path = file_path + ".7z"
    # define the level of zipping - and where is the 7zip
    try:
        subprocess.run([
            r"C:\\Program Files\\7-Zip\\7z.exe", "a", "-t7z", "-mx=9", f"-p{password}", archive_path, file_path
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, str(e)
# // ------------------------------------------------------------

# // ------------------------------------------------------------
# Main execution block
def main():
    # folder of files
    folder = r"C:\\Users\\Administrator\\Desktop\\books"
    # password
    password = "pass"

    all_files = get_all_files(folder)
    total_files = len(all_files)

    print(f"Total files found: {total_files}")
    errors = []

    for file_path in tqdm(all_files, desc="Compressing files", unit="file"):
        success, error = compress_file(file_path, password)
        if not success:
            errors.append((file_path, error))

    if errors:
        print("\nErrors occurred:")
        for file_path, msg in errors:
            print(f"{file_path} -> {msg}")
    else:
        print("\nAll files compressed successfully.")
# // ------------------------------------------------------------

if __name__ == "__main__":
    main()
