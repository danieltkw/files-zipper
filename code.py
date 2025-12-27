



# // Daniel T. K. W. - github.com/danieltkw - danielkopolo95@gmail.com

"""
Recursively processes files in the script's directory:
- Encrypts each file into a 7z archive with a user-provided password (headers encrypted).
- Renames the resulting .7z to a file without extension.
- Wraps that payload in a standard ZIP archive stored alongside the original.
- Does NOT log or print the password (except auto-generated password is printed once).
- Avoids overwriting existing output ZIPs by generating unique names.
- Includes an optional self-test mode: --self-test
- Password entry shows '*' while typing (best-effort; falls back to hidden input where masking isn't possible).
- Console shows current file being processed in the progress bar postfix (name + %).
"""

import os
import sys
import shutil
import uuid
import datetime
import getpass
import secrets
import string
import subprocess
import zipfile
import tempfile
import argparse
from tqdm import tqdm


# // ------------------------------------------------------------
def clear_screen() -> None:
    # Clear terminal for cleaner UX (Windows/Linux/macOS)
    os.system("cls" if os.name == "nt" else "clear")
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def _safe_open_append_text(log_path: str):
    # Open log file for appending; attempt restrictive permissions on POSIX.
    if os.name != "nt":
        fd = os.open(log_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        return os.fdopen(fd, "a", encoding="utf-8")
    return open(log_path, "a", encoding="utf-8")
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def log_message(log_path: str, message: str) -> None:
    # Append timestamped log line to log file (no secrets should be logged)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _safe_open_append_text(log_path) as logf:
        logf.write(f"[{timestamp}] {message}\n")
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def generate_strong_password(length: int = 24) -> str:
    # Generate a strong random password suitable for file encryption
    alphabet = string.ascii_letters + string.digits + string.punctuation
    alphabet = alphabet.replace(" ", "").replace("\t", "").replace("\n", "").replace("\r", "")
    return "".join(secrets.choice(alphabet) for _ in range(length))
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def validate_password_policy(pw: str) -> tuple[bool, str]:
    # Enforce: >= 8 chars, >=1 uppercase, >=4 letters, >=4 digits, and no char repeats > 2 times
    if len(pw) < 8:
        return False, "Password must be at least 8 characters."

    letters = sum(1 for c in pw if c.isalpha())
    digits = sum(1 for c in pw if c.isdigit())
    uppers = sum(1 for c in pw if c.isupper())

    if uppers < 1:
        return False, "Password must include at least 1 uppercase letter."
    if letters < 4:
        return False, "Password must include at least 4 letters (A-Z/a-z)."
    if digits < 4:
        return False, "Password must include at least 4 digits (0-9)."

    # No character repeated more than twice
    counts: dict[str, int] = {}
    for c in pw:
        counts[c] = counts.get(c, 0) + 1
        if counts[c] > 2:
            return False, f"Character '{c}' repeats more than twice."

    return True, "OK"
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def get_password_masked(prompt: str) -> str:
    # Read password with masking (prints '*' for each character). Works on Windows (msvcrt) and POSIX (termios/tty).
    # Falls back to getpass (no echo) if masking isn't possible.
    try:
        if os.name == "nt":
            import msvcrt  # type: ignore

            buf: list[str] = []
            sys.stdout.write(prompt)
            sys.stdout.flush()

            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                if ch == "\x03":
                    raise KeyboardInterrupt
                if ch in ("\b", "\x7f"):
                    if buf:
                        buf.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                if ch == "\x00" or ch == "\xe0":
                    _ = msvcrt.getwch()
                    continue
                buf.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()

            return "".join(buf).strip()

        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        buf2: list[str] = []

        sys.stdout.write(prompt)
        sys.stdout.flush()
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"):
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    break
                if ch == "\x03":
                    raise KeyboardInterrupt
                if ch in ("\x7f", "\b"):
                    if buf2:
                        buf2.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                buf2.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

        return "".join(buf2).strip()

    except Exception:
        # Fallback: hidden input, no masking
        try:
            return getpass.getpass(prompt).strip()
        except Exception:
            try:
                return input(prompt).strip()
            except Exception:
                return ""
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def get_password_from_user() -> str:
    # Read password securely with masking; if empty, generate strong password and print it once.
    # If user provides one, enforce policy (re-prompt on failure).
    while True:
        pw = get_password_masked("Password (ENTER = auto-generate strong): ").strip()

        if not pw:
            pw = generate_strong_password()
            print("\n[INFO] Auto-generated password (store it safely; it will NOT be logged):")
            print(pw)
            print("")
            return pw

        ok, reason = validate_password_policy(pw)
        if ok:
            return pw

        print(f"[WARN] Password rejected: {reason}")
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def get_all_files(
    base_folder: str,
    exclude_filename: str,
    max_depth: int | None = None,
    extensions: list[str] | None = None,
) -> list[str]:
    # Collect files recursively from base_folder, excluding exclude_filename
    file_paths: list[str] = []
    ext_filter = {e.lower() for e in extensions} if extensions is not None else None

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
            if ext_filter is not None:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in ext_filter:
                    continue

            file_paths.append(full_path)

    return file_paths
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def random_name_no_ext() -> str:
    # Generate a random UUID-based filename without extension
    return uuid.uuid4().hex
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def find_7z_executable() -> str | None:
    """
    Locate 7z executable.
    Works for:
    - normal Python execution
    - PyInstaller --onefile bundled exe (if 7z.exe is bundled)
    """
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path:
            bundled_7z = os.path.join(base_path, "7z.exe")
            if os.path.isfile(bundled_7z):
                return bundled_7z

    which = shutil.which("7z") or shutil.which("7za")
    if which:
        return which

    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c

    return None
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def ensure_unique_path(desired_path: str) -> str:
    # If desired_path exists, create a unique path by appending a numeric suffix. Never deletes existing files.
    if not os.path.exists(desired_path):
        return desired_path

    base, ext = os.path.splitext(desired_path)
    i = 1
    while True:
        candidate = f"{base}.{i}{ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def encrypt_with_7z(seven_zip_path: str, in_file: str, out_7z_no_ext_path: str, password: str) -> None:
    """
    Encrypt a file using 7-Zip into a 7z archive (then rename to no-extension).
    Creates a temporary .7z first, then moves to final no-extension filename.

    Note: -pPASSWORD is passed as a command-line argument (may be visible via process listing on some systems).
    """
    tmp_7z_path = out_7z_no_ext_path + ".7z"

    cmd = [
        seven_zip_path,
        "a",
        "-t7z",
        f"-p{password}",
        "-mhe=on",
        tmp_7z_path,
        in_file,
    ]

    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"7z failed (code {proc.returncode}): {proc.stderr.strip()[:2000]}")

    if os.path.exists(out_7z_no_ext_path):
        if os.path.islink(out_7z_no_ext_path) or not os.path.isfile(out_7z_no_ext_path):
            raise RuntimeError(f"Refusing to overwrite non-regular file: {out_7z_no_ext_path}")
        os.remove(out_7z_no_ext_path)

    os.replace(tmp_7z_path, out_7z_no_ext_path)
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def wrap_in_zip(no_ext_7z_path: str, final_zip_path: str) -> None:
    # Wrap the extension-less encrypted file into a standard ZIP archive.
    if os.path.islink(no_ext_7z_path) or not os.path.isfile(no_ext_7z_path):
        raise RuntimeError(f"Refusing to zip non-regular file: {no_ext_7z_path}")

    arcname = os.path.basename(no_ext_7z_path)
    with zipfile.ZipFile(final_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(no_ext_7z_path, arcname=arcname)
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def extract_single_member_zip(zip_path: str, out_dir: str) -> str:
    # Extract a ZIP expected to have a single member; return extracted file path.
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if len(names) != 1:
            raise RuntimeError(f"Self-test expected 1 zip member, got {len(names)}")
        member = names[0]
        zf.extract(member, path=out_dir)
        return os.path.join(out_dir, member)
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def decrypt_7z_payload(seven_zip_path: str, payload_path: str, out_dir: str, password: str) -> None:
    # Decrypt/extract 7z payload (even without extension) into out_dir.
    cmd = [
        seven_zip_path,
        "x",
        "-y",
        "-t7z",
        f"-p{password}",
        f"-o{out_dir}",
        payload_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"7z decrypt failed (code {proc.returncode}): {proc.stderr.strip()[:2000]}")
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def self_test(seven_zip_path: str) -> int:
    """
    Self-test:
    1) Create temp file with known content
    2) Encrypt to 7z payload (no ext)
    3) Wrap into ZIP
    4) Extract ZIP to get payload
    5) Decrypt payload and verify content matches
    6) Attempt decrypt with wrong password and expect failure
    """
    test_password = generate_strong_password(20)
    wrong_password = generate_strong_password(20)

    with tempfile.TemporaryDirectory() as td:
        src_dir = os.path.join(td, "src")
        mid_dir = os.path.join(td, "mid")
        out_dir = os.path.join(td, "out")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(mid_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        sample_path = os.path.join(src_dir, "sample.txt")
        sample_content = b"self-test: content\nline2\n"
        with open(sample_path, "wb") as f:
            f.write(sample_content)

        payload_no_ext = os.path.join(mid_dir, "payload_no_ext")
        encrypt_with_7z(seven_zip_path, sample_path, payload_no_ext, test_password)

        zip_path = os.path.join(mid_dir, "wrapped.zip")
        wrap_in_zip(payload_no_ext, zip_path)

        extracted_payload = extract_single_member_zip(zip_path, out_dir)

        dec_dir = os.path.join(out_dir, "dec")
        os.makedirs(dec_dir, exist_ok=True)
        decrypt_7z_payload(seven_zip_path, extracted_payload, dec_dir, test_password)

        decrypted_sample = os.path.join(dec_dir, "sample.txt")
        if not os.path.isfile(decrypted_sample):
            raise RuntimeError("Self-test failed: decrypted file not found (sample.txt)")
        with open(decrypted_sample, "rb") as f:
            got = f.read()
        if got != sample_content:
            raise RuntimeError("Self-test failed: decrypted content mismatch")

        try:
            wrong_dir = os.path.join(out_dir, "wrong")
            os.makedirs(wrong_dir, exist_ok=True)
            decrypt_7z_payload(seven_zip_path, extracted_payload, wrong_dir, wrong_password)
            raise RuntimeError("Self-test failed: wrong password unexpectedly succeeded")
        except RuntimeError:
            pass

    return 0
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def parse_args(argv: list[str]) -> argparse.Namespace:
    # Parse command-line arguments
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--self-test", action="store_true", help="Run built-in self-test and exit")
    p.add_argument("--depth", type=int, default=2, help="Max recursion depth (default: 2)")
    p.add_argument("--no-clear", action="store_true", help="Do not clear screen on start")
    return p.parse_args(argv)
# // ------------------------------------------------------------


# // ------------------------------------------------------------
def main() -> int:
    # Entry point
    args = parse_args(sys.argv[1:])

    if not args.no_clear:
        clear_screen()

    folder = os.path.dirname(os.path.realpath(sys.argv[0]))
    print(f"Script running in directory: {folder}")

    log_path = os.path.join(folder, "log.txt")
    script_path = os.path.realpath(sys.argv[0])

    seven_zip_path = find_7z_executable()
    if not seven_zip_path or not os.path.isfile(seven_zip_path) or not os.access(seven_zip_path, os.X_OK):
        print("Error: 7-Zip executable not found or inaccessible. Install 7-Zip or add it to your PATH.")
        return 1

    if args.self_test:
        try:
            rc = self_test(seven_zip_path)
            print("Self-test: OK")
            return rc
        except Exception as e:
            print(f"Self-test: FAIL | {repr(e)}")
            return 2

    password = get_password_from_user()
    log_message(log_path, "Run started (password not logged).")

    excluded_exts = {
        ".zip", ".7z", ".rar", ".gz", ".xz", ".bz2", ".tar", ".tgz", ".zst",
    }

    candidates = get_all_files(folder, exclude_filename=script_path, max_depth=args.depth, extensions=None)
    all_files = [f for f in candidates if os.path.splitext(f)[1].lower() not in excluded_exts]

    print(f"Total files found: {len(all_files)}\n")

    errors = 0
    successes = 0

    try:
        pbar = tqdm(all_files, desc="Encrypting", unit="file")
        for file_path in pbar:
            pbar.set_postfix_str(os.path.basename(file_path), refresh=True)

            if os.path.realpath(file_path) == os.path.realpath(log_path):
                continue

            try:
                parent_dir = os.path.dirname(file_path)

                rnd_name = random_name_no_ext()
                out_no_ext_path = os.path.join(parent_dir, rnd_name)

                desired_zip = os.path.join(parent_dir, os.path.basename(file_path) + ".zip")
                final_zip_path = ensure_unique_path(desired_zip)

                encrypt_with_7z(seven_zip_path, file_path, out_no_ext_path, password)
                wrap_in_zip(out_no_ext_path, final_zip_path)

                if os.path.exists(out_no_ext_path):
                    if os.path.islink(out_no_ext_path) or not os.path.isfile(out_no_ext_path):
                        raise RuntimeError(f"Refusing to delete non-regular file: {out_no_ext_path}")
                    os.remove(out_no_ext_path)

                successes += 1
                log_message(log_path, f"Success: {file_path} -> {final_zip_path}")

            except Exception as e:
                errors += 1
                log_message(log_path, f"Error: {file_path} | {repr(e)}")

    except KeyboardInterrupt:
        log_message(log_path, "Run interrupted by user (KeyboardInterrupt).")
        print("\nInterrupted.")
        return 130

    log_message(log_path, f"Completed. Total candidates: {len(all_files)} | Successes: {successes} | Errors: {errors}")
    print(f"\nCompleted. Total files: {len(all_files)} | Successes: {successes} | Errors: {errors}")
    return 0
# // ------------------------------------------------------------


if __name__ == "__main__":
    raise SystemExit(main())






