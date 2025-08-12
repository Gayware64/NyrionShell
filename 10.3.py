import os
import sys
import time
import shutil
import subprocess
import zipfile
import urllib.request
import urllib.parse
import json
import socket
import platform
import tarfile
import gzip
import hashlib
import base64
import uuid as uuidlib
import random
import getpass
import http.server
import signal
import stat as statmod
import re
import glob
import datetime
import shlex
from pathlib import Path

# Optional: colored output (works if you have colorama installed)
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    class Fore:
        RED = ''
        GREEN = ''
        CYAN = ''
        YELLOW = ''
        WHITE = ''
        RESET = ''
        BLUE = ''
        MAGENTA = ''
    class Style:
        BRIGHT = ''
        NORMAL = ''

# Optional: psutil for memory/CPU details in sysinfo
try:
    import psutil
except Exception:
    psutil = None

# Optional: clipboard helper
try:
    import pyperclip
except Exception:
    pyperclip = None

COPYRIGHT = "Copyright 2025 GayWare64"
BUILD = "10.3 v250811"
UPDATE_URL_VERSION = "https://raw.githubusercontent.com/YourUser/NyrionShell/main/version.txt"
UPDATE_URL_SCRIPT = "https://raw.githubusercontent.com/YourUser/NyrionShell/main/nyrion.py"

# Settings / state
CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".nyrion_config.json")
DEFAULT_LOG_FILE = os.path.join(os.path.expanduser("~"), "nyrion.log")
settings = {
    "echo_on": True,
    "prompt_template": "{drive}{path}> ",  # vars: {cwd} {path} {drive} {time} {date} {user} {host} {ver}
    "theme": "dark",
    "aliases": {},
    "log_enabled": False,
    "log_file": DEFAULT_LOG_FILE,
    "confirm_on": True,
    "history_limit": 1000,
}
echo_on = True
HISTORY = []

def save_config():
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        print(Fore.GREEN + f"Config saved to {CONFIG_PATH}" + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"Failed to save config: {e}" + Fore.RESET)

def load_config():
    global echo_on
    try:
        if os.path.isfile(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                settings.update(data)
                echo_on = settings.get("echo_on", True)
    except Exception as e:
        print(Fore.RED + f"Failed to load config: {e}" + Fore.RESET)

def format_prompt():
    cwd = os.getcwd()
    drive = os.path.splitdrive(cwd)[0] or ('C:' if os.name == 'nt' else '')
    path = cwd.replace(drive, '') if drive else cwd
    if not path:
        path = "\\"
    now = datetime.datetime.now()
    s = settings.get("prompt_template", "{drive}{path}> ")
    repl = {
        "cwd": cwd,
        "path": path if os.name == 'nt' else path,
        "drive": drive,
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "user": getpass.getuser(),
        "host": platform.node(),
        "ver": BUILD,
    }
    for k, v in repl.items():
        s = s.replace("{"+k+"}", str(v))
    s = s.replace("\\n", "\n")
    return Fore.YELLOW + s + Fore.RESET

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def loading_screen():
    clear_screen()
    s_art = [
         "███╗   ██╗ █████╗ ",
         "████╗  ██║██╔══██╗",
         "██╔██╗ ██║███████║",
         "██║╚██╗██║██╔══██║",
         "██║ ╚████║██║  ██║",
         "╚═╝  ╚═══╝╚═╝  ╚═╝",
    ]
    for line in s_art:
        print(Fore.WHITE + line + Fore.RESET)
    print()
    bar_length = 20
    print("Loading Nyrion Aeon 10.3...")
    for i in range(bar_length + 1):
        bar = "█" * i + "-" * (bar_length - i)
        print(Fore.GREEN + f"[{bar}]" + Fore.RESET, end='\r', flush=True)
        time.sleep(0.05)
    print()

def log_command(cmd_text):
    if settings.get("log_enabled"):
        try:
            with open(settings.get("log_file", DEFAULT_LOG_FILE), "a", encoding="utf-8") as f:
                ts = datetime.datetime.now().isoformat(timespec="seconds")
                f.write(f"[{ts}] {cmd_text}\n")
        except Exception as e:
            print(Fore.RED + f"Log write failed: {e}" + Fore.RESET)

def confirm(prompt="Are you sure? [y/N]: "):
    if not settings.get("confirm_on", True):
        return True
    try:
        ans = input(prompt).strip().lower()
        return ans in ("y", "yes")
    except KeyboardInterrupt:
        print()
        return False

# Existing commands (kept)
def show_help(args=None):
    if args:
        name = args[0].lower()
        if name in COMMANDS:
            print(Fore.CYAN + f"Help for 'lcr {name}':" + Fore.RESET)
            print("  " + COMMANDS[name]["help"])
            if COMMANDS[name].get("usage"):
                print("  Usage: lcr " + COMMANDS[name]["usage"])
            return
    print(Fore.CYAN + "Available commands:" + Fore.RESET)
    for k in sorted(COMMANDS.keys()):
        h = COMMANDS[k]["help"]
        print(f"  lcr {k:<10} - {h}")

def lcr_time():
    print(Fore.YELLOW + time.strftime("%a %b %d %H:%M:%S %Y") + Fore.RESET)

def lcr_mod(script_name):
    if not script_name.endswith(".py"):
        print("Only Python (.py) scripts are allowed.")
        return
    if not os.path.isfile(script_name):
        print(f"Script not found: {script_name}")
        return
    print(Fore.YELLOW + "\n=== Atlas Mod Environment ===\n" + Fore.RESET)
    try:
        with open(script_name, encoding="utf-8") as f:
            code = f.read()
            exec(code, {'__name__': '__main__'})
    except Exception as e:
        print(Fore.RED + f"Mod crashed: {e}" + Fore.RESET)

def lcr_date():
    print(Fore.YELLOW + time.strftime("%Y-%m-%d") + Fore.RESET)

def lcr_list():
    try:
        with os.scandir('.') as it:
            for entry in it:
                if entry.is_dir():
                    print(Fore.CYAN + entry.name + os.sep + Fore.RESET)
                else:
                    print(entry.name)
    except Exception as e:
        print(Fore.RED + "Error listing files: " + str(e) + Fore.RESET)

def lcr_directory(path):
    try:
        os.chdir(path)
    except Exception as e:
        print(Fore.RED + f"Bad command or filename: {e}" + Fore.RESET)

def lcr_type(filename):
    try:
        with open(filename, 'r', encoding="utf-8", errors="ignore") as file:
            print(file.read())
    except Exception as e:
        print(Fore.RED + f"File not found: {e}" + Fore.RESET)

def lcr_copy(src, dst):
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"        1 item(s) copied.")
    except Exception as e:
        print(Fore.RED + f"Cannot copy: {e}" + Fore.RESET)

def lcr_move(src, dst):
    try:
        shutil.move(src, dst)
        print(f"        1 item(s) moved.")
    except Exception as e:
        print(Fore.RED + f"Cannot move: {e}" + Fore.RESET)

def lcr_updater():
    print("Checking for updates...")
    try:
        with urllib.request.urlopen(UPDATE_URL_VERSION) as response:
            latest_version = response.read().decode().strip()
        current_version = BUILD.split()[0]  # e.g. "10.2"
        if latest_version == current_version:
            print(f"You already have the latest version: {current_version}")
            return
        print(f"New version available: {latest_version}. Downloading update...")
        backup_file = __file__ + ".bak"
        shutil.copy2(__file__, backup_file)
        print(f"Backup created: {backup_file}")
        with urllib.request.urlopen(UPDATE_URL_SCRIPT) as response, open(__file__, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Update successful! Please restart the program.")
    except Exception as e:
        print(Fore.RED + "Update failed: " + str(e) + Fore.RESET)

def lcr_zip(source, dest):
    if not os.path.exists(source):
        print(Fore.RED + f"Source not found: {source}" + Fore.RESET)
        return
    try:
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isdir(source):
                for root, dirs, files in os.walk(source):
                    for file in files:
                        full_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_path, start=os.path.dirname(source))
                        zipf.write(full_path, arcname)
            else:
                zipf.write(source, os.path.basename(source))
        print(f"Created zip archive: {dest}")
    except Exception as e:
        print(Fore.RED + f"Zip failed: {e}" + Fore.RESET)

def lcr_unzip(zipfile_path, extract_to='.'):
    if not os.path.isfile(zipfile_path):
        print(Fore.RED + f"Zip file not found: {zipfile_path}" + Fore.RESET)
        return
    try:
        with zipfile.ZipFile(zipfile_path, 'r') as zipf:
            zipf.extractall(path=extract_to)
        print(f"Extracted {zipfile_path} to {extract_to}")
    except Exception as e:
        print(Fore.RED + f"Unzip failed: {e}" + Fore.RESET)

def lcr_run(script_name):
    try:
        result = subprocess.run([sys.executable, script_name])
        if result.returncode != 0:
            print(Fore.RED + f"Script exited with code {result.returncode}" + Fore.RESET)
    except Exception as e:
        print(Fore.RED + f"Error running script: {e}" + Fore.RESET)

def lcr_delete(filename):
    try:
        if settings.get("confirm_on", True):
            if not confirm(f"Delete '{filename}'? [y/N]: "):
                print("Cancelled.")
                return
        os.remove(filename)
        print(f"        {filename} deleted.")
    except Exception as e:
        print(Fore.RED + f"Cannot delete: {e}" + Fore.RESET)

def lcr_rename(old, new):
    try:
        os.rename(old, new)
        print(f"        Renamed: {old} -> {new}.")
    except Exception as e:
        print(Fore.RED + f"Cannot rename: {e}" + Fore.RESET)

def lcr_make(dirname):
    try:
        os.makedirs(dirname, exist_ok=False)
        print(f"        Directory created: {dirname}")
    except Exception as e:
        print(Fore.RED + f"Cannot create directory: {e}" + Fore.RESET)

def lcr_remove(dirname):
    try:
        if settings.get("confirm_on", True):
            if not confirm(f"Remove directory '{dirname}'? [y/N]: "):
                print("Cancelled.")
                return
        os.rmdir(dirname)
        print(f"        Directory removed: {dirname}")
    except Exception as e:
        print(Fore.RED + f"Cannot remove directory: {e}" + Fore.RESET)

def lcr_echo(args):
    global echo_on
    if not args:
        print(Fore.RED + "The syntax of the command is incorrect." + Fore.RESET)
        return
    arg = args[0].lower()
    if arg == "off":
        echo_on = False
        settings["echo_on"] = False
    elif arg == "on":
        echo_on = True
        settings["echo_on"] = True
    else:
        print(' '.join(args))

def lcr_pause():
    input("Press any key to continue . . .")

# New: helpers and new commands
def cmd_pwd(args):
    print(os.getcwd())

def cmd_whoami(args):
    print(getpass.getuser())

def cmd_hostname(args):
    print(platform.node())

def cmd_sysinfo(args):
    print(Fore.CYAN + "System Info" + Fore.RESET)
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Machine: {platform.machine()} | Processor: {platform.processor() or 'N/A'}")
    print(f"Python: {platform.python_version()}")
    try:
        print(f"CPU cores: {os.cpu_count() or 'N/A'}")
    except Exception:
        pass
    if psutil:
        try:
            vm = psutil.virtual_memory()
            print(f"Memory: {vm.total//(1024**2)} MB total, {vm.available//(1024**2)} MB free")
        except Exception:
            pass

def cmd_env(args):
    if not args:
        for k, v in os.environ.items():
            print(f"{k}={v}")
        return
    sub = args[0].lower()
    if sub == "set" and len(args) >= 3:
        name = args[1]
        value = ' '.join(args[2:])
        os.environ[name] = value
        print(f"{name} set.")
    elif sub == "get" and len(args) == 2:
        print(os.environ.get(args[1], ""))
    elif sub == "unset" and len(args) == 2:
        os.environ.pop(args[1], None)
        print(f"{args[1]} unset.")
    else:
        print("Usage: env | env set NAME VALUE | env get NAME | env unset NAME")

def cmd_alias(args):
    if not args:
        if not settings["aliases"]:
            print("(no aliases)")
            return
        for k, v in settings["aliases"].items():
            print(f"{k} = {v}")
        return
    if "=" in args[0]:
        name, val = args[0].split("=", 1)
        val = val.strip('"').strip("'")
        settings["aliases"][name] = val
        print(f"Alias set: {name} = {val}")
    else:
        name = args[0]
        val = ' '.join(args[1:])
        if not val:
            print(Fore.RED + "Usage: alias NAME=VALUE or alias NAME VALUE..." + Fore.RESET)
            return
        settings["aliases"][name] = val
        print(f"Alias set: {name} = {val}")

def cmd_unalias(args):
    if not args:
        print("Usage: unalias NAME")
        return
    name = args[0]
    if name in settings["aliases"]:
        del settings["aliases"][name]
        print(f"Alias removed: {name}")
    else:
        print(f"No such alias: {name}")

def cmd_history(args):
    for i, h in enumerate(HISTORY, start=1):
        print(f"{i:4}  {h}")

def cmd_ls(args):
    show_all = "-a" in args
    long = "-l" in args
    human = "-h" in args
    paths = [a for a in args if not a.startswith("-")] or ["."]
    def fmt_size(n):
        if not human:
            return str(n)
        for unit in ['B','K','M','G','T']:
            if n < 1024:
                return f"{n:.0f}{unit}"
            n /= 1024
        return f"{n:.0f}P"
    for p in paths:
        p = Path(p)
        try:
            if p.is_dir():
                entries = list(p.iterdir())
                if not show_all:
                    entries = [e for e in entries if e.name not in ('.','..') and not e.name.startswith('.')]
                if len(paths) > 1:
                    print(Fore.CYAN + f"{p}:" + Fore.RESET)
                for e in sorted(entries, key=lambda x: x.name.lower()):
                    name = e.name + (os.sep if e.is_dir() else "")
                    if long:
                        st = e.stat()
                        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))
                        size = fmt_size(st.st_size)
                        perms = statmod.filemode(st.st_mode)
                        print(f"{perms} {size:>8} {mtime} {name}")
                    else:
                        print(name)
            else:
                print(p.name)
        except Exception as e:
            print(Fore.RED + f"ls error: {e}" + Fore.RESET)

def cmd_cp(args):
    if not args or len(args) < 2:
        print("Usage: cp [-r] SRC DST")
        return
    recursive = "-r" in args or "/s" in args
    src_dst = [a for a in args if not a.startswith("-")]
    if len(src_dst) != 2:
        print("Usage: cp [-r] SRC DST")
        return
    src, dst = src_dst
    try:
        if os.path.isdir(src):
            if not recursive:
                print(Fore.RED + "cp: -r required for directories" + Fore.RESET)
                return
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print("Copied.")
    except Exception as e:
        print(Fore.RED + f"cp error: {e}" + Fore.RESET)

def cmd_mv(args):
    if len(args) != 2:
        print("Usage: mv SRC DST")
        return
    try:
        shutil.move(args[0], args[1])
        print("Moved.")
    except Exception as e:
        print(Fore.RED + f"mv error: {e}" + Fore.RESET)

def cmd_rm(args):
    if not args:
        print("Usage: rm [-r] [-f] TARGET...")
        return
    recursive = "-r" in args or "/s" in args
    force = "-f" in args or "/f" in args
    targets = [a for a in args if not a.startswith("-")]
    for t in targets:
        try:
            if os.path.isdir(t) and not os.path.islink(t):
                if not recursive:
                    print(Fore.RED + f"rm: '{t}' is a directory (use -r)" + Fore.RESET)
                    continue
                if not force and not confirm(f"Recursively delete '{t}'? [y/N]: "):
                    print("Skipped.")
                    continue
                shutil.rmtree(t)
            else:
                if not force and not confirm(f"Delete '{t}'? [y/N]: "):
                    print("Skipped.")
                    continue
                os.remove(t)
            print(f"Deleted: {t}")
        except Exception as e:
            print(Fore.RED + f"rm error: {e}" + Fore.RESET)

def cmd_touch(args):
    if not args:
        print("Usage: touch FILE")
        return
    f = args[0]
    try:
        Path(f).touch()
        print(f"Touched {f}")
    except Exception as e:
        print(Fore.RED + f"touch error: {e}" + Fore.RESET)

def cmd_chmod(args):
    if len(args) != 2:
        print("Usage: chmod MODE FILE  (MODE numeric, e.g., 755)")
        return
    mode_str, path = args
    try:
        mode = int(mode_str, 8)
        os.chmod(path, mode)
        print("Mode set.")
    except Exception as e:
        print(Fore.RED + f"chmod error: {e}" + Fore.RESET)

def cmd_stat(args):
    if not args:
        print("Usage: stat FILE")
        return
    p = args[0]
    try:
        st = os.stat(p)
        print(f"Size: {st.st_size} bytes")
        print(f"Mode: {statmod.filemode(st.st_mode)}")
        print(f"Modified: {time.ctime(st.st_mtime)}")
        print(f"Created:  {time.ctime(st.st_ctime)}")
        print(f"Inode: {getattr(st, 'st_ino', 'n/a')}")
    except Exception as e:
        print(Fore.RED + f"stat error: {e}" + Fore.RESET)

def cmd_head(args):
    if not args:
        print("Usage: head [-n N] FILE")
        return
    n = 10
    if len(args) >= 2 and args[0] in ("-n", "/n"):
        try:
            n = int(args[1])
            fname = args[2]
        except Exception:
            print("Usage: head [-n N] FILE")
            return
    else:
        fname = args[0]
    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i >= n:
                    break
                print(line.rstrip("\n"))
    except Exception as e:
        print(Fore.RED + f"head error: {e}" + Fore.RESET)

def cmd_tail(args):
    if not args:
        print("Usage: tail [-n N] FILE")
        return
    n = 10
    if len(args) >= 2 and args[0] in ("-n", "/n"):
        try:
            n = int(args[1]); fname = args[2]
        except Exception:
            print("Usage: tail [-n N] FILE")
            return
    else:
        fname = args[0]
    try:
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-n:]
            for line in lines:
                print(line.rstrip("\n"))
    except Exception as e:
        print(Fore.RED + f"tail error: {e}" + Fore.RESET)

def cmd_find(args):
    if not args:
        print("Usage: find PATTERN [PATH]")
        return
    pattern = args[0]
    base = args[1] if len(args) > 1 else "."
    pattern_path = os.path.join(base, pattern)
    for p in glob.iglob(pattern_path, recursive=True):
        print(p)

def cmd_grep(args):
    if len(args) < 2:
        print("Usage: grep [-i] PATTERN FILE")
        return
    case_ins = False
    if args[0] == "-i":
        case_ins = True
        args = args[1:]
    pat, fname = args[0], args[1]
    try:
        flags = re.IGNORECASE if case_ins else 0
        rx = re.compile(pat, flags)
        with open(fname, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, start=1):
                if rx.search(line):
                    print(f"{i:6}: {line.rstrip()}")
    except Exception as e:
        print(Fore.RED + f"grep error: {e}" + Fore.RESET)

def cmd_which(args):
    if not args:
        print("Usage: which NAME")
        return
    from shutil import which
    p = which(args[0])
    print(p or "")

def cmd_open(args):
    if not args:
        print("Usage: open FILE")
        return
    path = args[0]
    try:
        if os.name == 'nt':
            os.startfile(path)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception as e:
        print(Fore.RED + f"open error: {e}" + Fore.RESET)

def cmd_edit(args):
    if not args:
        print("Usage: edit FILE")
        return
    editor = os.environ.get("EDITOR")
    if not editor:
        editor = "notepad" if os.name == 'nt' else ("nano" if shutil.which("nano") else "vi")
    try:
        subprocess.run([editor, args[0]])
    except Exception as e:
        print(Fore.RED + f"edit error: {e}" + Fore.RESET)

def cmd_checksum(args):
    if len(args) != 2:
        print("Usage: checksum md5|sha1|sha256 FILE")
        return
    alg, fname = args
    h = None
    try:
        if alg == "md5":
            h = hashlib.md5()
        elif alg == "sha1":
            h = hashlib.sha1()
        elif alg == "sha256":
            h = hashlib.sha256()
        else:
            print("Algorithm must be md5, sha1, or sha256")
            return
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        print(h.hexdigest())
    except Exception as e:
        print(Fore.RED + f"checksum error: {e}" + Fore.RESET)

def cmd_base64(args):
    if not args or args[0] not in ("encode", "decode"):
        print("Usage: base64 encode|decode <infile|-t TEXT> [outfile]")
        return
    mode = args[0]
    if len(args) >= 2 and args[1] == "-t":
        text = ' '.join(args[2:]) if len(args) > 2 else ""
        data = text.encode("utf-8")
    elif len(args) >= 2:
        infile = args[1]
        try:
            with open(infile, "rb") as f:
                data = f.read()
        except Exception as e:
            print(Fore.RED + f"base64 error: {e}" + Fore.RESET)
            return
    else:
        print("Usage: base64 encode|decode <infile|-t TEXT> [outfile]")
        return
    outfile = None
    if len(args) >= 3 and args[1] != "-t":
        outfile = args[2]
    try:
        if mode == "encode":
            out = base64.b64encode(data)
        else:
            out = base64.b64decode(data)
        if outfile:
            with open(outfile, "wb") as f:
                f.write(out)
            print(f"Wrote {outfile}")
        else:
            if mode == "encode":
                print(out.decode())
            else:
                try:
                    print(out.decode())
                except Exception:
                    print(out.hex())
    except Exception as e:
        print(Fore.RED + f"base64 error: {e}" + Fore.RESET)

def cmd_hex(args):
    if not args:
        print("Usage: hex FILE [bytes]")
        return
    fname = args[0]
    n = int(args[1]) if len(args) > 1 else 256
    try:
        with open(fname, "rb") as f:
            data = f.read(n)
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hexs = ' '.join(f"{b:02x}" for b in chunk)
            text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"{i:08x}  {hexs:<47}  {text}")
    except Exception as e:
        print(Fore.RED + f"hex error: {e}" + Fore.RESET)

def cmd_tar(args):
    if len(args) != 2:
        print("Usage: tar SRC DEST.tar|.tar.gz")
        return
    src, dest = args
    try:
        mode = "w:gz" if dest.endswith(".tar.gz") or dest.endswith(".tgz") else "w"
        with tarfile.open(dest, mode) as tf:
            arcname = os.path.basename(src.rstrip(os.sep))
            tf.add(src, arcname=arcname)
        print(f"Created {dest}")
    except Exception as e:
        print(Fore.RED + f"tar error: {e}" + Fore.RESET)

def cmd_untar(args):
    if len(args) < 1:
        print("Usage: untar FILE.tar[.gz] [DEST]")
        return
    src = args[0]
    dest = args[1] if len(args) > 1 else "."
    try:
        with tarfile.open(src, "r:*") as tf:
            tf.extractall(path=dest)
        print(f"Extracted to {dest}")
    except Exception as e:
        print(Fore.RED + f"untar error: {e}" + Fore.RESET)

def cmd_gzip(args):
    if len(args) != 1:
        print("Usage: gzip FILE")
        return
    src = args[0]
    try:
        dst = src + ".gz"
        with open(src, "rb") as f_in, gzip.open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        print(f"Created {dst}")
    except Exception as e:
        print(Fore.RED + f"gzip error: {e}" + Fore.RESET)

def cmd_gunzip(args):
    if len(args) != 1:
        print("Usage: gunzip FILE.gz")
        return
    src = args[0]
    try:
        if not src.endswith(".gz"):
            print("gunzip expects a .gz file")
            return
        dst = src[:-3]
        with gzip.open(src, "rb") as f_in, open(dst, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        print(f"Created {dst}")
    except Exception as e:
        print(Fore.RED + f"gunzip error: {e}" + Fore.RESET)

def cmd_http(args):
    port = int(args[0]) if args else 8000
    Handler = http.server.SimpleHTTPRequestHandler
    Server = getattr(http.server, "ThreadingHTTPServer", http.server.HTTPServer)
    server = Server(("", port), Handler)
    print(Fore.GREEN + f"Serving HTTP on 0.0.0.0:{port} (Ctrl+C to stop)" + Fore.RESET)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("Server stopped.")

def cmd_curl(args):
    if not args:
        print("Usage: curl URL [outfile]")
        return
    url = args[0]
    out = args[1] if len(args) > 1 else os.path.basename(urllib.parse.urlparse(url).path) or "downloaded.file"
    try:
        with urllib.request.urlopen(url) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
        print(f"Saved to {out}")
    except Exception as e:
        print(Fore.RED + f"curl error: {e}" + Fore.RESET)

def cmd_ip(args):
    try:
        host = socket.gethostname()
        print(f"Host: {host}")
        addrs = set()
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                infos = socket.getaddrinfo(host, None, family, socket.SOCK_STREAM)
                for info in infos:
                    addrs.add(info[4][0])
            except Exception:
                pass
        for a in sorted(addrs):
            print(a)
    except Exception as e:
        print(Fore.RED + f"ip error: {e}" + Fore.RESET)

def cmd_ping(args):
    if not args:
        print("Usage: ping HOST [count]")
        return
    host = args[0]
    count = args[1] if len(args) > 1 else "4"
    try:
        if os.name == 'nt':
            subprocess.run(["ping", "-n", str(count), host])
        else:
            subprocess.run(["ping", "-c", str(count), host])
    except Exception as e:
        print(Fore.RED + f"ping error: {e}" + Fore.RESET)

def cmd_ps(args):
    try:
        if os.name == 'nt':
            subprocess.run(["tasklist"])
        else:
            subprocess.run(["ps", "-ef"])
    except Exception as e:
        print(Fore.RED + f"ps error: {e}" + Fore.RESET)

def cmd_kill(args):
    if not args:
        print("Usage: kill PID")
        return
    try:
        pid = int(args[0])
        if os.name == 'nt':
            subprocess.run(["taskkill", "/PID", str(pid), "/F"])
        else:
            os.kill(pid, signal.SIGTERM)
        print(f"Killed {pid}")
    except Exception as e:
        print(Fore.RED + f"kill error: {e}" + Fore.RESET)

def cmd_run(args):
    if not args:
        print("Usage: run COMMAND [args...]")
        return
    try:
        subprocess.run(args)
    except Exception as e:
        print(Fore.RED + f"run error: {e}" + Fore.RESET)

def safe_eval(expr):
    import ast, operator as op
    ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Mod: op.mod, ast.Pow: op.pow, ast.FloorDiv: op.floordiv,
        ast.USub: op.neg, ast.UAdd: op.pos,
    }
    def eval_(node):
        if isinstance(node, ast.Expression):
            return eval_(node.body)
        if hasattr(ast, "Constant") and isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError("Only numeric constants allowed")
        if hasattr(ast, "Num") and isinstance(node, ast.Num):  # Py <3.8
            return node.n
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](eval_(node.left), eval_(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in ops:
            return ops[type(node.op)](eval_(node.operand))
        raise ValueError("Unsupported expression")
    tree = ast.parse(expr, mode="eval")
    # Disallow names, calls, attributes, etc.
    for n in ast.walk(tree):
        if isinstance(n, (ast.Call, ast.Name, getattr(ast, "Attribute", object))):
            raise ValueError("Names and calls are not allowed")
    return eval_(tree)

def cmd_calc(args):
    if not args:
        print("Usage: calc EXPRESSION")
        return
    expr = ' '.join(args)
    try:
        print(safe_eval(expr))
    except Exception as e:
        print(Fore.RED + f"calc error: {e}" + Fore.RESET)

def cmd_uuid(args):
    print(str(uuidlib.uuid4()))

def cmd_random(args):
    if len(args) < 2:
        print("Usage: random MIN MAX [COUNT]")
        return
    try:
        lo, hi = int(args[0]), int(args[1])
        count = int(args[2]) if len(args) > 2 else 1
        for _ in range(count):
            print(random.randint(lo, hi))
    except Exception as e:
        print(Fore.RED + f"random error: {e}" + Fore.RESET)

def cmd_clip(args):
    if not args:
        print("Usage: clip copy <text|-f file> | clip paste")
        return
    mode = args[0].lower()
    if mode == "copy":
        if len(args) >= 3 and args[1] == "-f":
            try:
                with open(args[2], "r", encoding="utf-8", errors="ignore") as f:
                    data = f.read()
            except Exception as e:
                print(Fore.RED + f"clip error: {e}" + Fore.RESET); return
        else:
            data = ' '.join(args[1:])
        try:
            if pyperclip:
                pyperclip.copy(data)
            else:
                if os.name == 'nt':
                    p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                    p.communicate(data.encode("utf-8"))
                elif sys.platform == "darwin":
                    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
                    p.communicate(data.encode("utf-8"))
                else:
                    if shutil.which("xclip"):
                        p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                        p.communicate(data.encode("utf-8"))
                    elif shutil.which("xsel"):
                        p = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
                        p.communicate(data.encode("utf-8"))
                    else:
                        raise RuntimeError("No clipboard backend available")
            print("Copied to clipboard.")
        except Exception as e:
            print(Fore.RED + f"clip copy error: {e}" + Fore.RESET)
    elif mode == "paste":
        try:
            if pyperclip:
                print(pyperclip.paste())
            else:
                if os.name == 'nt':
                    out = subprocess.check_output(["powershell", "-NoProfile", "-Command", "Get-Clipboard"])
                    print(out.decode("utf-8", errors="ignore"))
                elif sys.platform == "darwin":
                    out = subprocess.check_output(["pbpaste"])
                    print(out.decode("utf-8", errors="ignore"))
                else:
                    if shutil.which("xclip"):
                        out = subprocess.check_output(["xclip", "-selection", "clipboard", "-o"])
                        print(out.decode("utf-8", errors="ignore"))
                    elif shutil.which("xsel"):
                        out = subprocess.check_output(["xsel", "--clipboard", "--output"])
                        print(out.decode("utf-8", errors="ignore"))
                    else:
                        raise RuntimeError("No clipboard backend available")
        except Exception as e:
            print(Fore.RED + f"clip paste error: {e}" + Fore.RESET)
    else:
        print("Usage: clip copy <text|-f file> | clip paste")

def cmd_prompt(args):
    if not args:
        print(f"Current prompt: {settings['prompt_template']}")
        print("Vars: {cwd} {path} {drive} {time} {date} {user} {host} {ver}")
        print("Usage: prompt set TEMPLATE | prompt preview | prompt reset")
        return
    sub = args[0].lower()
    if sub == "set":
        tpl = ' '.join(args[1:])
        settings["prompt_template"] = tpl
        print("Prompt updated.")
    elif sub == "preview":
        print("Preview: " + format_prompt())
    elif sub == "reset":
        settings["prompt_template"] = "{drive}{path}> "
        print("Prompt reset.")
    else:
        print("Usage: prompt set TEMPLATE | prompt preview | prompt reset")

def cmd_theme(args):
    if not args:
        print(f"Theme: {settings['theme']} (options: light, dark)")
        return
    theme = args[0].lower()
    if theme not in ("light", "dark"):
        print("Theme must be 'light' or 'dark'")
        return
    settings["theme"] = theme
    print(f"Theme set to {theme}")

def cmd_config(args):
    if not args or args[0] == "show":
        print(json.dumps(settings, indent=2))
        return
    sub = args[0].lower()
    if sub == "save":
        save_config()
    elif sub == "load":
        load_config()
        print("Config loaded.")
    elif sub == "reset":
        settings = {
            "echo_on": True,
            "prompt_template": "{drive}{path}> ",
            "theme": "dark",
            "aliases": {},
            "log_enabled": False,
            "log_file": DEFAULT_LOG_FILE,
            "confirm_on": True,
            "history_limit": 1000,
        }
        print("Config reset (not saved yet).")
    else:
        print("Usage: config show|save|load|reset")

def cmd_log(args):
    if not args:
        on = settings.get("log_enabled", False)
        print(f"log is {'on' if on else 'off'} -> {settings.get('log_file', DEFAULT_LOG_FILE)}")
        print("Usage: log on|off [file PATH]")
        return
    sub = args[0].lower()
    if sub == "on":
        settings["log_enabled"] = True
        if len(args) > 2 and args[1] == "file":
            settings["log_file"] = args[2]
        print("Logging enabled.")
    elif sub == "off":
        settings["log_enabled"] = False
        print("Logging disabled.")
    elif sub == "file" and len(args) > 1:
        settings["log_file"] = args[1]
        print(f"Log file set: {args[1]}")
    else:
        print("Usage: log on|off [file PATH]")

def cmd_confirm(args):
    if not args:
        print(f"confirm is {'on' if settings.get('confirm_on', True) else 'off'}")
        return
    if args[0].lower() == "on":
        settings["confirm_on"] = True
    elif args[0].lower() == "off":
        settings["confirm_on"] = False
    else:
        print("Usage: confirm on|off")
        return
    print(f"confirm set to {args[0].lower()}")

def cmd_df(args):
    path = args[0] if args else os.getcwd()
    try:
        total, used, free = shutil.disk_usage(path)
        def h(n):
            for u in "BKMGT":
                if n < 1024: return f"{n:.0f}{u}"
                n/=1024
            return f"{n:.0f}P"
        print(f"Total: {h(total)} | Used: {h(used)} | Free: {h(free)}")
    except Exception as e:
        print(Fore.RED + f"df error: {e}" + Fore.RESET)

def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                fp = os.path.join(root, f)
                total += os.path.getsize(fp)
            except Exception:
                pass
    return total

def cmd_du(args):
    if not args:
        print("Usage: du PATH")
        return
    path = args[0]
    try:
        size = dir_size(path)
        def h(n):
            for u in "BKMGT":
                if n < 1024: return f"{n:.0f}{u}"
                n/=1024
            return f"{n:.0f}P"
        print(f"{h(size)}\t{path}")
    except Exception as e:
        print(Fore.RED + f"du error: {e}" + Fore.RESET)

def cmd_bench(args):
    if not args:
        print("Usage: bench COMMAND [args...]")
        return
    start = time.perf_counter()
    execute_command(args[0].lower(), args[1:], nested=True)
    dur = (time.perf_counter() - start) * 1000
    print(Fore.GREEN + f"Elapsed: {dur:.2f} ms" + Fore.RESET)

def cmd_watch(args):
    if len(args) < 2:
        print("Usage: watch SECONDS COMMAND [args...]")
        return
    try:
        interval = float(args[0])
    except Exception:
        print("watch: SECONDS must be a number")
        return
    sub = args[1].lower()
    sub_args = args[2:]
    try:
        while True:
            clear_screen()
            print(Fore.CYAN + time.strftime("%Y-%m-%d %H:%M:%S") + Fore.RESET)
            execute_command(sub, sub_args, nested=True)
            print()
            print(f"(Ctrl+C to stop) Next run in {interval}s...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watch.")

def cmd_sleep(args):
    if not args:
        print("Usage: sleep SECONDS")
        return
    try:
        t = float(args[0])
        time.sleep(t)
    except Exception as e:
        print(Fore.RED + f"sleep error: {e}" + Fore.RESET)

# Command registry
COMMANDS = {
    "help":     {"func": lambda a: show_help(a), "help": "Show help", "usage": "help [command]"},
    "time":     {"func": lambda a: lcr_time(), "help": "Show current date/time"},
    "date":     {"func": lambda a: lcr_date(), "help": "Show current date"},
    "cls":      {"func": lambda a: clear_screen(), "help": "Clear the screen"},
    "dir":      {"func": lambda a: lcr_list(), "help": "List files in current directory"},
    "cd":       {"func": lambda a: lcr_directory(a[0]) if a else print("Usage: lcr cd DIR"), "help": "Change directory"},
    "type":     {"func": lambda a: lcr_type(a[0]) if a else print("Usage: lcr type FILE"), "help": "Show file contents"},
    "copy":     {"func": lambda a: lcr_copy(a[0], a[1]) if len(a)==2 else print("Usage: lcr copy SRC DST"), "help": "Copy file/dir"},
    "move":     {"func": lambda a: lcr_move(a[0], a[1]) if len(a)==2 else print("Usage: lcr move SRC DST"), "help": "Move file/dir"},
    "del":      {"func": lambda a: lcr_delete(a[0]) if a else print("Usage: lcr del FILE"), "help": "Delete file"},
    "ren":      {"func": lambda a: lcr_rename(a[0], a[1]) if len(a)==2 else print("Usage: lcr ren OLD NEW"), "help": "Rename file"},
    "mkdir":    {"func": lambda a: lcr_make(a[0]) if a else print("Usage: lcr mkdir DIR"), "help": "Create directory"},
    "rmdir":    {"func": lambda a: lcr_remove(a[0]) if a else print("Usage: lcr rmdir DIR"), "help": "Remove empty directory"},
    "echo":     {"func": lambda a: lcr_echo(a), "help": "Print text or toggle echo on/off"},
    "pause":    {"func": lambda a: lcr_pause(), "help": "Wait for keypress"},
    "exit":     {"func": lambda a: sys.exit(0), "help": "Exit Nyrion shell"},
    "mod":      {"func": lambda a: lcr_mod(a[0]) if a else print("Usage: lcr mod script.py"), "help": "Run .py in Atlas env"},
    "updater":  {"func": lambda a: lcr_updater(), "help": "Check/install updates"},
    "zip":      {"func": lambda a: lcr_zip(a[0], a[1]) if len(a)==2 else print("Usage: lcr zip SRC DST.zip"), "help": "Create zip archive"},
    "unzip":    {"func": lambda a: lcr_unzip(a[0], (a[1] if len(a)>1 else '.')) if a else print("Usage: lcr unzip ZIP [DEST]"), "help": "Extract zip archive"},
    # New commands (all require 'lcr ' prefix)
    "pwd":      {"func": cmd_pwd, "help": "Print working directory"},
    "whoami":   {"func": cmd_whoami, "help": "Current user"},
    "hostname": {"func": cmd_hostname, "help": "Machine name"},
    "sysinfo":  {"func": cmd_sysinfo, "help": "System information"},
    "env":      {"func": cmd_env, "help": "Environment variables"},
    "alias":    {"func": cmd_alias, "help": "Set/list aliases"},
    "unalias":  {"func": cmd_unalias, "help": "Remove an alias"},
    "history":  {"func": cmd_history, "help": "Show command history"},
    "ls":       {"func": cmd_ls, "help": "List files"},
    "cp":       {"func": cmd_cp, "help": "Copy files/dirs"},
    "mv":       {"func": cmd_mv, "help": "Move files/dirs"},
    "rm":       {"func": cmd_rm, "help": "Remove files/dirs"},
    "touch":    {"func": cmd_touch, "help": "Create/update file timestamp"},
    "chmod":    {"func": cmd_chmod, "help": "Change file mode (numeric)"},
    "stat":     {"func": cmd_stat, "help": "File information"},
    "head":     {"func": cmd_head, "help": "First N lines of a file"},
    "tail":     {"func": cmd_tail, "help": "Last N lines of a file"},
    "find":     {"func": cmd_find, "help": "Glob search"},
    "grep":     {"func": cmd_grep, "help": "Search file for pattern"},
    "which":    {"func": cmd_which, "help": "Locate executable"},
    "open":     {"func": cmd_open, "help": "Open with default app"},
    "edit":     {"func": cmd_edit, "help": "Open file in editor"},
    "checksum": {"func": cmd_checksum, "help": "File checksum"},
    "base64":   {"func": cmd_base64, "help": "Base64 encode/decode"},
    "hex":      {"func": cmd_hex, "help": "Hex dump"},
    "tar":      {"func": cmd_tar, "help": "Create tar/tar.gz"},
    "untar":    {"func": cmd_untar, "help": "Extract tar/tgz"},
    "gzip":     {"func": cmd_gzip, "help": "Compress file"},
    "gunzip":   {"func": cmd_gunzip, "help": "Decompress .gz file"},
    "http":     {"func": cmd_http, "help": "Simple HTTP server"},
    "curl":     {"func": cmd_curl, "help": "Download a URL"},
    "ip":       {"func": cmd_ip, "help": "Show IP addresses"},
    "ping":     {"func": cmd_ping, "help": "Ping host"},
    "ps":       {"func": cmd_ps, "help": "List processes"},
    "kill":     {"func": cmd_kill, "help": "Kill a process"},
    "run":      {"func": cmd_run, "help": "Run external command"},
    "calc":     {"func": cmd_calc, "help": "Calculator"},
    "uuid":     {"func": cmd_uuid, "help": "Generate UUID"},
    "random":   {"func": cmd_random, "help": "Random integers"},
    "clip":     {"func": cmd_clip, "help": "Clipboard copy/paste"},
    "prompt":   {"func": cmd_prompt, "help": "Customize prompt"},
    "theme":    {"func": cmd_theme, "help": "Light/Dark theme"},
    "config":   {"func": cmd_config, "help": "Config save/load/etc"},
    "log":      {"func": cmd_log, "help": "Enable/disable logging"},
    "confirm":  {"func": cmd_confirm, "help": "Confirm destructive ops"},
    "df":       {"func": cmd_df, "help": "Disk usage/free"},
    "du":       {"func": cmd_du, "help": "Directory size"},
    "bench":    {"func": cmd_bench, "help": "Time a command"},
    "watch":    {"func": cmd_watch, "help": "Repeat a command"},
    "sleep":    {"func": cmd_sleep, "help": "Sleep for seconds"},
}

def preprocess_input(s):
    s = s.strip()
    # History expansion: !! or !N
    if s == "!!":
        if HISTORY:
            return HISTORY[-1]
        else:
            print(Fore.RED + "history: empty" + Fore.RESET)
            return ""
    if s.startswith("!") and s[1:].isdigit():
        idx = int(s[1:]) - 1
        if 0 <= idx < len(HISTORY):
            return HISTORY[idx]
        else:
            print(Fore.RED + "history: out of range" + Fore.RESET)
            return ""
    # Alias expansion only within 'lcr ...'
    try:
        parts = shlex.split(s)
    except Exception:
        parts = s.split()
    if not parts:
        return s
    if parts[0].lower() == "lcr" and len(parts) > 1:
        head = parts[1]
        tail = parts[2:]
        expanded = expand_alias(head, tail)
        if expanded:
            return " ".join(["lcr"] + shlex.split(expanded))
    return s

def expand_alias(head, tail):
    seen = set()
    cmd = head
    args = tail
    for _ in range(5):
        val = settings["aliases"].get(cmd)
        if not val:
            break
        if cmd in seen:
            print(Fore.RED + "alias loop detected" + Fore.RESET)
            return None
        seen.add(cmd)
        merged = val + (" " + " ".join(args) if args else "")
        try:
            parts = shlex.split(merged)
        except Exception:
            parts = merged.split()
        if not parts:
            return None
        cmd, args = parts[0], parts[1:]
    return " ".join([cmd] + args)

def execute_command(cmd, args, nested=False):
    if cmd in COMMANDS:
        COMMANDS[cmd]["func"](args)
        return
    print(Fore.RED + f"Unknown command: {cmd}" + Fore.RESET)

def main():
    global echo_on
    load_config()
    echo_on = settings.get("echo_on", True)

    loading_screen()
    clear_screen()
    print(Fore.WHITE + Style.BRIGHT + "Nyrion Aeon 10.3" + Style.NORMAL + Fore.RESET)
    print(BUILD)
    print(Fore.WHITE + COPYRIGHT + Fore.RESET)
    print()

    while True:
        try:
            prompt = format_prompt()
            try:
                command_line = input(prompt)
            except EOFError:
                print()
                break
            if not command_line.strip():
                continue

            processed = preprocess_input(command_line)
            if not processed:
                continue

            if echo_on:
                print(processed)
            log_command(processed)

            HISTORY.append(processed)
            if len(HISTORY) > settings.get("history_limit", 1000):
                del HISTORY[:-settings.get("history_limit", 1000)]

            try:
                parts = shlex.split(processed)
            except Exception:
                parts = processed.split()
            if not parts:
                continue

            # Enforce 'lcr ' prefix for built-ins. Allow running .py directly.
            if parts[0].lower() != 'lcr':
                # Directly run Python scripts like original behavior
                if parts[0].endswith(".py") and os.path.isfile(parts[0]):
                    lcr_run(parts[0])
                    continue
                # Small convenience: allow bare 'exit' or 'cls'
                if parts[0].lower() == "exit":
                    print("Exiting Nyrion shell...")
                    break
                if parts[0].lower() == "cls":
                    clear_screen()
                    continue
                print(Fore.RED + "Commands must start with 'lcr'. Example: lcr help" + Fore.RESET)
                continue

            if len(parts) == 1:
                continue

            cmd = parts[1].lower()
            args = parts[2:]

            if cmd == "exit":
                print("Exiting Nyrion shell...")
                break

            execute_command(cmd, args)

        except KeyboardInterrupt:
            print("\nUse 'lcr exit' or 'exit' to quit.")
        except SystemExit:
            print("Exiting Nyrion shell...")
            break
        except Exception as e:
            print(Fore.RED + f"Error: {e}" + Fore.RESET)

if __name__ == "__main__":
    main()