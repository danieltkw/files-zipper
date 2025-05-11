


🔐 Secure File Obfuscation & Archival with 7-Zip + ZIP
This script automates a multi-layer file packaging process designed for privacy, auditability, and obfuscation.

🧰 What it does:
Recursively scans a target folder for all files.

For each file:

Saves the original filename inside a name.txt alongside the file.

Encrypts both contents and filenames using 7-Zip (AES-256 + Ultra Compression).

Renames the resulting .7z archive to a UUID with no extension (formatless).

Wraps that formatless file into a .zip archive using store mode (no compression), with the original filename as the .zip name.

Deletes the intermediate .7z file after the .zip is created.

🔐 Inside each .zip:
A single extensionless file (really a 7z archive with full encryption)

Only users with the password and 7-Zip can extract the original content

Inside the 7z archive:

The original file

A name.txt containing the real filename

✅ Features:
Strong encryption (AES-256) with hidden filenames

Zero-leakage of original filenames externally

Zip wrapping provides casual concealment and standard delivery

Uses tqdm progress bar for visibility
