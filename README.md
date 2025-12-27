

# File Archival with 7-Zip and ZIP

Python script that processes files in the execution directory and generates encrypted archives using a two-layer container (7-Zip inside ZIP).

Behavior:
- Creates a 7z archive with encrypted headers (-mhe=on)
- Renames the archive to a random name without extension
- Wraps it into <original_filename>.zip
- Deletes intermediate files
- Never overwrites existing ZIPs (numeric suffix applied)

Passwords:
- User may enter a password or press ENTER
- If ENTER is pressed, a random password is generated and shown once
- User-provided passwords must satisfy:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 4 letters
  - At least 4 digits
  - No character repeated more than twice
- Input is masked with '*'
- Passwords are never logged

Output:
file.txt → file.txt.zip  
file.txt.zip contains one file: <random_uuid> (encrypted 7z archive)

Self-test:
python script.py --self-test

Requirements:
- Python 3.10+
- 7-Zip (7z or 7za) available in PATH
  
- Install Python dependencies:

pip install tqdm

