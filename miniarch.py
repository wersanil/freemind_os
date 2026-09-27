#!/usr/bin/python3
"""
miniarch - a minimalist Python shell for FreeMind OS.
Primary shell on top of BusyBox. No external dependencies.
"""

import os
import sys
import time
import shutil
import subprocess
import platform
from datetime import datetime

sys.dont_write_bytecode = True

VERSION = "0.5.0"
NAME = "FreeMind"

COLORS = {
    'red': 31, 'green': 32, 'yellow': 33, 'blue': 34,
    'magenta': 35, 'cyan': 36, 'white': 37, 'grey': 90,
}

# ─── Logo: circuit-tree ───────────────────────────────────────
LOGO_UNICODE = [
    "     ◯           ◯",
    "      ╲         ╱",
    "       ╲       ╱",
    "        ╲     ╱",
    "         ╲   ╱",
    "          ╲ ╱",
    "           │",
    "     ◯     │     ◯",
    "      ╲    │    ╱",
    "       ╲   │   ╱",
    "        ╲  │  ╱",
    "         ╲ │ ╱",
    "          ╲│╱",
    "           │",
    "     ◯     │     ◯",
    "      ╲    │    ╱",
    "       ╲   │   ╱",
    "        ╲  │  ╱",
    "         ╲ │ ╱",
    "          ╲│╱",
    "           │",
    "           │",
    "           │",
]

LOGO_ASCII = [
    "     o           o",
    "      \\         /",
    "       \\       /",
    "        \\     /",
    "         \\   /",
    "          \\ /",
    "           |",
    "     o     |     o",
    "      \\    |    /",
    "       \\   |   /",
    "        \\  |  /",
    "         \\ | /",
    "          \\|/",
    "           |",
    "     o     |     o",
    "      \\    |    /",
    "       \\   |   /",
    "        \\  |  /",
    "         \\ | /",
    "          \\|/",
    "           |",
    "           |",
    "           |",
]


class FreeMind:
    """Main shell class."""

    def __init__(self):
        self.running = True
        self.current_dir = os.path.expanduser("~") or "/"
        try:
            os.chdir(self.current_dir)
        except OSError:
            self.current_dir = "/"
        self.has_terminal = sys.stdout.isatty()
        self.use_unicode = os.environ.get('TERM', '') != 'linux'
        self.session_log = []   # (timestamp, command)
        self.commands = {}
        self.init_commands()

    def init_commands(self):
        self.commands = {
            # control
            'help':     self.cmd_help,
            'exit':     self.cmd_exit,   'quit': self.cmd_exit,
            'reboot':   self.cmd_reboot,
            'shutdown': self.cmd_shutdown, 'poweroff': self.cmd_shutdown, 'halt': self.cmd_shutdown,
            'clear':    self.cmd_clear,
            'shell':    self.cmd_shell, 'sh': self.cmd_shell,
            'history':  self.cmd_history,
            'log':      self.cmd_log,
            'less':     self.cmd_less,   'more': self.cmd_less,

            # files
            'ls':    self.cmd_ls,   'dir': self.cmd_ls,
            'pwd':   self.cmd_pwd,
            'cd':    self.cmd_cd,
            'mkdir': self.cmd_mkdir,
            'rm':    self.cmd_rm,   'del': self.cmd_rm,
            'cat':   self.cmd_cat,
            'touch': self.cmd_touch,
            'cp':    self.cmd_cp,
            'mv':    self.cmd_mv,
            'head':  self.cmd_head,
            'tail':  self.cmd_tail,
            'wc':    self.cmd_wc,
            'grep':  self.cmd_grep,
            'find':  self.cmd_find,
            'tree':  self.cmd_tree,
            'stat':  self.cmd_stat,
            'chmod': self.cmd_chmod,
            'ln':    self.cmd_ln,
            'du':    self.cmd_du,
            'df':    self.cmd_df,
            'sort':  self.cmd_sort,
            'uniq':  self.cmd_uniq,

            # system
            'date':     self.cmd_date,  'time': self.cmd_date,
            'sysinfo':  self.cmd_sysinfo, 'info': self.cmd_sysinfo,
            'neofetch': self.cmd_neofetch, 'fetch': self.cmd_neofetch,
            'whoami':   self.cmd_whoami,
            'uptime':   self.cmd_uptime,
            'uname':    self.cmd_uname,
            'id':       self.cmd_id,
            'hostname': self.cmd_hostname,
            'env':      self.cmd_env,
            'which':    self.cmd_which,
            'free':     self.cmd_free,
            'sleep':    self.cmd_sleep,
            'seq':      self.cmd_seq,

            # applications
            'echo':    self.cmd_echo,
            'calc':    self.cmd_calc,
            'calcfig': self.cmd_calcfig,
        }

    # ────────────────────────────────────────────────────────────
    #  Utilities
    # ────────────────────────────────────────────────────────────

    def colorize(self, text, color):
        if not self.has_terminal or color not in COLORS:
            return str(text)
        return f"\033[{COLORS[color]}m{text}\033[0m"

    def _user(self):
        return (os.environ.get('USER') or
                os.environ.get('LOGNAME') or
                'user')

    def _uptime(self):
        try:
            with open('/proc/uptime') as f:
                secs = float(f.read().split()[0])
            d, secs = divmod(int(secs), 86400)
            h, secs = divmod(secs, 3600)
            m = secs // 60
            if d: return f"{d}d {h}h {m}m"
            if h: return f"{h}h {m}m"
            return f"{m}m"
        except Exception:
            return "n/a"

    def _meminfo(self):
        try:
            data = {}
            with open('/proc/meminfo') as f:
                for line in f:
                    k, v = line.split(':', 1)
                    data[k] = int(v.strip().split()[0])
            total = data['MemTotal'] / 1024
            avail = data.get('MemAvailable', data.get('MemFree', 0)) / 1024
            used = total - avail
            return f"{used:.0f} MiB / {total:.0f} MiB"
        except Exception:
            return None

    def _cpuinfo(self):
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if line.lower().startswith('model name'):
                        return line.split(':', 1)[1].strip()
        except Exception:
            pass
        return platform.processor() or None

    def _diskfree(self):
        try:
            st = os.statvfs('/')
            total = st.f_blocks * st.f_frsize / 1024**2
            free = st.f_bavail * st.f_frsize / 1024**2
            return f"{total - free:.0f} MiB / {total:.0f} MiB"
        except Exception:
            return "n/a"

    def clear_screen(self):
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()

    def get_prompt(self):
        user = self._user()
        host = platform.node() or 'freemind'
        dir_name = os.path.basename(self.current_dir) or '/'
        return (f"{self.colorize(user, 'green')}@"
                f"{self.colorize(host, 'cyan')} "
                f"{self.colorize(dir_name, 'blue')}$ ")

    # ────────────────────────────────────────────────────────────
    #  Main loop
    # ────────────────────────────────────────────────────────────

    def boot(self):
        self.clear_screen()
        print(f"{self.colorize(NAME + ' ' + VERSION, 'cyan')}  "
              f"{self.colorize('\"Freedom. Simplicity. Control\"', 'grey')}")
        print(f"{self.colorize('help - list of commands, Shift+PgUp/PgDn - scroll', 'grey')}\n")
        self.main_loop()

    def main_loop(self):
        while self.running:
            try:
                line = input(self.get_prompt())
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                break
            line = line.strip()
            if not line:
                continue
            self.session_log.append((datetime.now(), line))
            self.execute_command(line)

    def execute_command(self, line):
        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in self.commands:
            try:
                self.commands[cmd](args)
            except KeyboardInterrupt:
                print()
            except Exception as e:
                print(self.colorize(f"error: {e}", 'red'))
        else:
            self.execute_system_command(line)

    def execute_system_command(self, command):
        try:
            subprocess.run(command, shell=True)
        except FileNotFoundError:
            print(self.colorize(f"command not found: {command}", 'red'))
        except Exception as e:
            print(self.colorize(f"error: {e}", 'red'))

    # ────────────────────────────────────────────────────────────
    #  Control
    # ────────────────────────────────────────────────────────────

    def cmd_help(self, args):
        """Show command reference"""
        groups = [
            ("Control", ['help', 'history', 'log', 'clear', 'shell',
                         'exit', 'reboot', 'shutdown']),
            ("Files", ['ls', 'pwd', 'cd', 'mkdir', 'rm', 'touch', 'cat',
                       'cp', 'mv', 'head', 'tail', 'wc', 'grep', 'find',
                       'tree', 'stat', 'chmod', 'ln', 'du', 'less']),
            ("System", ['date', 'uname', 'id', 'hostname', 'env', 'which',
                        'whoami', 'uptime', 'free', 'df', 'sysinfo', 'neofetch']),
            ("Utilities", ['echo', 'calc', 'calcfig', 'sleep', 'seq',
                           'sort', 'uniq']),
        ]
        print()
        for title, cmds in groups:
            print(self.colorize(f"  {title}", 'yellow'))
            for c in cmds:
                if c in self.commands:
                    doc = self.commands[c].__doc__ or ""
                    print(f"    {c:<10} {self.colorize(doc, 'grey')}")
            print()
        print(self.colorize("  Up/Down arrows - command history, Shift+PgUp/PgDn - scroll screen.", 'grey'))
        print(self.colorize("  Any other command is passed to BusyBox: vi, top, ps, ping...", 'grey'))
        print()

    def cmd_exit(self, args):
        """Exit miniarch (BusyBox init will respawn)"""
        print(self.colorize("Exiting...", 'grey'))
        self.running = False

    def cmd_reboot(self, args):
        """Reboot the system"""
        print(self.colorize("Rebooting...", 'yellow'))
        try:
            subprocess.run(["/sbin/reboot"])
        except Exception:
            self.running = False

    def cmd_shutdown(self, args):
        """Shut down the system"""
        print(self.colorize("Shutting down...", 'yellow'))
        try:
            subprocess.run(["/sbin/poweroff"])
        except Exception:
            sys.exit(0)

    def cmd_clear(self, args):
        """Clear the screen"""
        self.clear_screen()

    def cmd_shell(self, args):
        """Start BusyBox sh (exit or Ctrl+D to return)"""
        print(self.colorize("BusyBox shell. Exit: exit or Ctrl+D.", 'grey'))
        try:
            subprocess.call(["/bin/sh"])
        except Exception as e:
            print(self.colorize(f"shell: {e}", 'red'))

    def cmd_history(self, args):
        """Command history (persisted across sessions)"""
        try:
            import readline
            n = readline.get_current_history_length()
            for i in range(1, n + 1):
                item = readline.get_history_item(i)
                if item:
                    print(f"  {i:5d}  {item}")
        except ImportError:
            for i, (_, cmd) in enumerate(self.session_log, 1):
                print(f"  {i:5d}  {cmd}")

    def cmd_log(self, args):
        """Commands of the current session with timestamps"""
        if not self.session_log:
            print(self.colorize("(empty)", 'grey'))
            return
        for ts, cmd in self.session_log:
            print(f"  {ts.strftime('%H:%M:%S')}  {cmd}")

    def cmd_less(self, args):
        """Paged file viewer (Enter - next page, q - quit)"""
        if not args:
            print("Usage: less <file>")
            return
        try:
            with open(args[0], errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            print(self.colorize(f"less: {e}", 'red'))
            return
        try:
            rows = os.get_terminal_size().lines
        except OSError:
            rows = 24
        page = max(rows - 2, 5)
        i = 0
        while i < len(lines):
            end = min(i + page, len(lines))
            for line in lines[i:end]:
                sys.stdout.write(line)
            i = end
            if i >= len(lines):
                break
            try:
                ans = input(self.colorize("-- more -- [Enter]=next [q]=quit: ", 'grey'))
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if ans.strip().lower() == 'q':
                break

    # ────────────────────────────────────────────────────────────
    #  Files
    # ────────────────────────────────────────────────────────────

    def cmd_ls(self, args):
        """List files and directories"""
        path = self.current_dir
        show_all = False
        for a in args:
            if a in ('-a', '/a', '--all'):
                show_all = True
            else:
                path = a
        try:
            items = os.listdir(path)
        except Exception as e:
            print(self.colorize(f"ls: {e}", 'red'))
            return
        if not show_all:
            items = [i for i in items if not i.startswith('.')]
        items.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        for item in items:
            full = os.path.join(path, item)
            if os.path.isdir(full):
                print(self.colorize(item + "/", 'blue'))
            elif os.access(full, os.X_OK):
                print(self.colorize(item + "*", 'green'))
            else:
                print(item)

    def cmd_pwd(self, args):
        """Print working directory"""
        print(self.current_dir)

    def cmd_cd(self, args):
        """Change directory"""
        target = args[0] if args else (os.path.expanduser("~") or "/")
        if target == "-":
            target = self.current_dir
        try:
            os.chdir(target)
            self.current_dir = os.getcwd()
        except Exception as e:
            print(self.colorize(f"cd: {e}", 'red'))

    def cmd_mkdir(self, args):
        """Create a directory"""
        if not args:
            print("Usage: mkdir <dir>...")
            return
        for d in args:
            try:
                os.mkdir(d)
            except Exception as e:
                print(self.colorize(f"mkdir: {d}: {e}", 'red'))

    def cmd_rm(self, args):
        """Remove a file or directory (recursive)"""
        if not args:
            print("Usage: rm <path>...")
            return
        for p in args:
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except Exception as e:
                print(self.colorize(f"rm: {p}: {e}", 'red'))

    def cmd_cat(self, args):
        """Print file contents"""
        if not args:
            print("Usage: cat <file>...")
            return
        for fn in args:
            try:
                with open(fn, 'r', errors='replace') as f:
                    sys.stdout.write(f.read())
            except Exception as e:
                print(self.colorize(f"cat: {fn}: {e}", 'red'))

    def cmd_touch(self, args):
        """Create an empty file"""
        if not args:
            print("Usage: touch <file>...")
            return
        for fn in args:
            try:
                with open(fn, 'a'):
                    os.utime(fn, None)
            except Exception as e:
                print(self.colorize(f"touch: {fn}: {e}", 'red'))

    def cmd_cp(self, args):
        """Copy a file or directory"""
        if len(args) < 2:
            print("Usage: cp <src> <dst>")
            return
        src, dst = args[0], args[1]
        try:
            if os.path.isdir(src):
                if os.path.isdir(dst):
                    dst = os.path.join(dst, os.path.basename(src.rstrip('/')))
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        except Exception as e:
            print(self.colorize(f"cp: {e}", 'red'))

    def cmd_mv(self, args):
        """Move / rename"""
        if len(args) < 2:
            print("Usage: mv <src> <dst>")
            return
        try:
            shutil.move(args[0], args[1])
        except Exception as e:
            print(self.colorize(f"mv: {e}", 'red'))

    def cmd_head(self, args):
        """First N lines of a file (default 10)"""
        n = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] in ('-n', '-') and i + 1 < len(args):
                try:
                    n = int(args[i + 1]); i += 2; continue
                except ValueError:
                    pass
            files.append(args[i]); i += 1
        if not files:
            print("Usage: head [-n N] <file>...")
            return
        for fn in files:
            try:
                with open(fn, errors='replace') as f:
                    for _ in range(n):
                        line = f.readline()
                        if not line:
                            break
                        sys.stdout.write(line)
            except Exception as e:
                print(self.colorize(f"head: {fn}: {e}", 'red'))

    def cmd_tail(self, args):
        """Last N lines of a file (default 10)"""
        n = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] in ('-n', '-') and i + 1 < len(args):
                try:
                    n = int(args[i + 1]); i += 2; continue
                except ValueError:
                    pass
            files.append(args[i]); i += 1
        if not files:
            print("Usage: tail [-n N] <file>...")
            return
        for fn in files:
            try:
                with open(fn, errors='replace') as f:
                    lines = f.readlines()
                for line in lines[-n:]:
                    sys.stdout.write(line)
            except Exception as e:
                print(self.colorize(f"tail: {fn}: {e}", 'red'))

    def cmd_wc(self, args):
        """Count lines, words, bytes"""
        if not args:
            print("Usage: wc <file>...")
            return
        for fn in args:
            try:
                with open(fn, 'rb') as f:
                    data = f.read()
                nl = chr(10).encode()
                print(f"{data.count(nl):>8d} "
                      f"{len(data.split()):>8d} "
                      f"{len(data):>8d} {fn}")
            except Exception as e:
                print(self.colorize(f"wc: {fn}: {e}", 'red'))

    def cmd_grep(self, args):
        """Print lines matching a substring"""
        if len(args) < 2:
            print("Usage: grep <pattern> <file>...")
            return
        pattern = args[0]
        multi = len(args) > 2
        for fn in args[1:]:
            try:
                with open(fn, errors='replace') as f:
                    for line in f:
                        if pattern in line:
                            prefix = f"{fn}:" if multi else ""
                            sys.stdout.write(f"{prefix}{line}")
            except Exception as e:
                print(self.colorize(f"grep: {fn}: {e}", 'red'))

    def cmd_find(self, args):
        """Find files by name (substring match)"""
        root = "."
        pattern = None
        if len(args) == 1:
            pattern = args[0]
        elif len(args) >= 2:
            root, pattern = args[0], args[1]
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for name in files + dirs:
                if pattern is None or pattern in name:
                    print(os.path.join(base, name))

    def cmd_tree(self, args):
        """Directory tree"""
        root = args[0] if args else "."

        def walk(path, prefix=""):
            try:
                items = sorted(i for i in os.listdir(path) if not i.startswith('.'))
            except OSError:
                return
            for i, item in enumerate(items):
                full = os.path.join(path, item)
                last = (i == len(items) - 1)
                branch = "└── " if last else "├── "
                is_dir = os.path.isdir(full)
                name = item + ("/" if is_dir else "")
                col = 'blue' if is_dir else 'white'
                print(f"{prefix}{branch}{self.colorize(name, col)}")
                if is_dir:
                    walk(full, prefix + ("    " if last else "│   "))

        print(self.colorize(root, 'blue'))
        walk(root)

    def cmd_stat(self, args):
        """Show file information"""
        if not args:
            print("Usage: stat <file>...")
            return
        for fn in args:
            try:
                st = os.stat(fn)
                print(f"  File:    {fn}")
                print(f"  Size:    {st.st_size}")
                print(f"  Mode:    {oct(st.st_mode)}")
                print(f"  Mtime:   {datetime.fromtimestamp(st.st_mtime).isoformat(' ', 'seconds')}")
            except Exception as e:
                print(self.colorize(f"stat: {fn}: {e}", 'red'))

    def cmd_chmod(self, args):
        """Change permissions (octal)"""
        if len(args) < 2:
            print("Usage: chmod <mode> <file>...")
            return
        try:
            mode = int(args[0], 8)
        except ValueError:
            print(self.colorize(f"chmod: invalid mode: {args[0]}", 'red'))
            return
        for fn in args[1:]:
            try:
                os.chmod(fn, mode)
            except Exception as e:
                print(self.colorize(f"chmod: {fn}: {e}", 'red'))

    def cmd_ln(self, args):
        """Create a link: ln [-s] <target> <link>"""
        sym = False
        rest = []
        for a in args:
            if a == '-s':
                sym = True
            else:
                rest.append(a)
        if len(rest) < 2:
            print("Usage: ln [-s] <target> <link>")
            return
        try:
            if sym:
                os.symlink(rest[0], rest[1])
            else:
                os.link(rest[0], rest[1])
        except Exception as e:
            print(self.colorize(f"ln: {e}", 'red'))

    def cmd_du(self, args):
        """Show directory size"""
        root = args[0] if args else "."
        total = 0
        try:
            for base, _dirs, files in os.walk(root):
                for name in files:
                    try:
                        total += os.path.getsize(os.path.join(base, name))
                    except OSError:
                        pass
            print(f"{total:>12} {root}")
        except Exception as e:
            print(self.colorize(f"du: {e}", 'red'))

    def cmd_df(self, args):
        """Filesystem usage (from /proc/mounts)"""
        def human(n):
            for u in ('B', 'K', 'M', 'G', 'T'):
                if n < 1024:
                    return f"{n:.0f}{u}"
                n /= 1024
            return f"{n:.0f}P"

        try:
            with open('/proc/mounts') as f:
                entries = [line.split()[:3] for line in f if len(line.split()) >= 3]
            print(f"{'Filesystem':22} {'Type':10} {'Size':>8} {'Used':>8} {'Avail':>8}  Mounted")
            for dev, mnt, fs in entries:
                try:
                    st = os.statvfs(mnt)
                    size = st.f_blocks * st.f_frsize
                    free = st.f_bavail * st.f_frsize
                    used = size - st.f_bfree * st.f_frsize
                    print(f"{dev:22} {fs:10} {human(size):>8} "
                          f"{human(used):>8} {human(free):>8}  {mnt}")
                except OSError:
                    pass
        except Exception as e:
            print(self.colorize(f"df: {e}", 'red'))

    def cmd_sort(self, args):
        """Sort lines of a file"""
        if not args:
            print("Usage: sort <file>")
            return
        try:
            with open(args[0], errors='replace') as f:
                for line in sorted(f.readlines()):
                    sys.stdout.write(line)
        except Exception as e:
            print(self.colorize(f"sort: {e}", 'red'))

    def cmd_uniq(self, args):
        """Remove adjacent duplicate lines"""
        if not args:
            print("Usage: uniq <file>")
            return
        try:
            prev = None
            with open(args[0], errors='replace') as f:
                for line in f:
                    if line != prev:
                        sys.stdout.write(line)
                    prev = line
        except Exception as e:
            print(self.colorize(f"uniq: {e}", 'red'))

    # ────────────────────────────────────────────────────────────
    #  System
    # ────────────────────────────────────────────────────────────

    def cmd_date(self, args):
        """Show date and time"""
        now = datetime.now()
        print(f"{self.colorize('Date:', 'yellow')} {now.strftime('%Y-%m-%d')}")
        print(f"{self.colorize('Time:', 'yellow')} {now.strftime('%H:%M:%S')}")

    def cmd_echo(self, args):
        """Print text"""
        print(' '.join(args))

    def cmd_whoami(self, args):
        """Print current user name"""
        print(self._user())

    def cmd_uptime(self, args):
        """Show system uptime"""
        print(f"up {self._uptime()}")

    def cmd_uname(self, args):
        """Kernel information"""
        u = platform.uname()
        print(f"{u.system} {u.node} {u.release} {u.version} {u.machine}")

    def cmd_id(self, args):
        """UID/GID of the current user"""
        try:
            print(f"uid={os.getuid()}({self._user()}) gid={os.getgid()}")
        except Exception:
            print("id: n/a")

    def cmd_hostname(self, args):
        """Host name (can be set: hostname <name>)"""
        if args:
            try:
                os.sethostname(args[0])
            except Exception as e:
                print(self.colorize(f"hostname: {e}", 'red'))
        else:
            print(platform.node() or "localhost")

    def cmd_env(self, args):
        """Environment variables"""
        for k, v in sorted(os.environ.items()):
            print(f"{k}={v}")

    def cmd_which(self, args):
        """Locate a program in PATH"""
        if not args:
            print("Usage: which <cmd>...")
            return
        path_dirs = os.environ.get('PATH', '/bin:/usr/bin').split(':')
        for cmd in args:
            found = None
            for d in path_dirs:
                p = os.path.join(d, cmd)
                if os.path.isfile(p) and os.access(p, os.X_OK):
                    found = p
                    break
            print(found if found else f"{cmd}: not found")

    def cmd_free(self, args):
        """Memory usage (from /proc/meminfo)"""
        try:
            data = {}
            with open('/proc/meminfo') as f:
                for line in f:
                    k, v = line.split(':', 1)
                    data[k] = int(v.strip().split()[0])

            def mb(kb):
                return f"{kb / 1024:.0f} MiB"

            total = data['MemTotal']
            free = data['MemFree']
            buffers = data.get('Buffers', 0)
            cached = data.get('Cached', 0)
            avail = data.get('MemAvailable', free)
            used = total - free - buffers - cached

            print(f"{'':6}{'total':>10} {'used':>10} {'free':>10} {'avail':>10}")
            print(f"{'Mem:':6}{mb(total):>10} {mb(used):>10} "
                  f"{mb(free):>10} {mb(avail):>10}")
        except Exception as e:
            print(self.colorize(f"free: {e}", 'red'))

    def cmd_sleep(self, args):
        """Pause for N seconds"""
        try:
            time.sleep(float(args[0]) if args else 1.0)
        except Exception:
            pass

    def cmd_seq(self, args):
        """Number sequence: seq <n> | seq <start> <end> [step]"""
        try:
            nums = [int(a) for a in args]
        except ValueError:
            print("Usage: seq <n> | seq <start> <end> [step]")
            return
        if len(nums) == 1:
            rng = range(1, nums[0] + 1)
        elif len(nums) == 2:
            rng = range(nums[0], nums[1] + 1)
        elif len(nums) >= 3:
            rng = range(nums[0], nums[1] + 1, nums[2])
        else:
            return
        for n in rng:
            print(n)

    def cmd_sysinfo(self, args):
        """Brief system information"""
        print()
        print(self.colorize("  FreeMind system info", 'yellow'))
        print(f"  OS:        {NAME} {VERSION}")
        print(f"  System:    {platform.system()} {platform.release()}")
        print(f"  Host:      {platform.node() or 'freemind'}")
        print(f"  User:      {self._user()}")
        print(f"  CWD:       {self.current_dir}")
        print(f"  Python:    {platform.python_version()}")
        up = self._uptime()
        if up != "n/a":
            print(f"  Uptime:    {up}")
        mem = self._meminfo()
        if mem:
            print(f"  Memory:    {mem}")
        print(f"  Disk /:    {self._diskfree()}")
        print()

    # ────────────────────────────────────────────────────────────
    #  Applications
    # ────────────────────────────────────────────────────────────

    def cmd_calc(self, args):
        """Mini calculator (q to quit)"""
        print(self.colorize("Calculator. Quit: q", 'yellow'))
        allowed = set("0123456789+-*/()., %")
        while True:
            try:
                expr = input("calc> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not expr:
                continue
            if expr.lower() in ('q', 'quit', 'exit'):
                break
            if not all(c in allowed for c in expr):
                print(self.colorize("Only digits and + - * / ( ) .", 'red'))
                continue
            try:
                print(f"= {eval(expr, {'__builtins__': {}}, {})}")
            except Exception as e:
                print(self.colorize(f"error: {e}", 'red'))

    def cmd_calcfig(self, args):
        """Rectangle area and perimeter (text output)"""
        try:
            if len(args) >= 2:
                length = int(args[0])
                width = int(args[1])
            else:
                print("Enter rectangle sides:")
                length = int(input("  Length: "))
                width = int(input("  Width:  "))
        except (ValueError, EOFError, KeyboardInterrupt):
            print(self.colorize("Error: an integer is required.", 'red'))
            return

        area = length * width
        perim = 2 * (length + width)

        c = self.colorize
        print()
        print(f"  {c('Sides', 'cyan')}      : {length} x {width}")
        print(f"  {c('Perimeter', 'cyan')}  : {perim}")
        print(f"  {c('Area', 'cyan')}       : {area}")
        print()

    # ────────────────────────────────────────────────────────────
    #  Neofetch
    # ────────────────────────────────────────────────────────────

    def cmd_neofetch(self, args):
        """ASCII logo and system information"""
        logo_src = LOGO_UNICODE if self.use_unicode else LOGO_ASCII
        logo = [self.colorize(line, 'cyan') for line in logo_src]

        user = self._user()
        host = platform.node() or 'freemind'
        info = []
        info.append(f"{self.colorize(user, 'green')}@{self.colorize(host, 'green')}")
        info.append(self.colorize("-" * 24, 'grey'))
        info.append(f"{self.colorize('OS:', 'yellow')}      {NAME} {VERSION}")
        info.append(f"{self.colorize('Kernel:', 'yellow')}  {platform.release()}")
        info.append(f"{self.colorize('Arch:', 'yellow')}    {platform.machine()}")
        info.append(f"{self.colorize('Shell:', 'yellow')}   miniarch (py {platform.python_version()})")
        info.append(f"{self.colorize('Term:', 'yellow')}    {os.environ.get('TERM', 'linux')}")
        info.append(f"{self.colorize('Uptime:', 'yellow')}  {self._uptime()}")

        mem = self._meminfo()
        if mem:
            info.append(f"{self.colorize('Memory:', 'yellow')}  {mem}")

        cpu = self._cpuinfo()
        if cpu:
            info.append(f"{self.colorize('CPU:', 'yellow')}     {cpu}")

        info.append(f"{self.colorize('Disk /:', 'yellow')}  {self._diskfree()}")

        info.append("")
        info.append(f"{self.colorize('*', 'cyan')} "
                    f"{self.colorize('OPEN KNOWLEDGE', 'green')} "
                    f"{self.colorize('/', 'grey')} "
                    f"{self.colorize('FREE ACCESS', 'green')}")

        height = max(len(logo), len(info))
        while len(logo) < height:
            logo.append("")
        while len(info) < height:
            info.append("")

        print()
        for left, right in zip(logo, info):
            print(f"{left}   {right}")
        print()


# ────────────────────────────────────────────────────────────────
#  Entry point
# ────────────────────────────────────────────────────────────────

def _setup_readline():
    """Enable Up/Down arrow history and persist it across sessions."""
    try:
        import readline
    except ImportError:
        return False
    histfile = os.path.expanduser("~/.miniarch_history")
    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass
    except Exception:
        pass
    readline.set_history_length(1000)

    import atexit
    def _save():
        try:
            readline.write_history_file(histfile)
        except Exception:
            pass
    atexit.register(_save)
    return True


def main():
    _setup_readline()   # must run before the first input(), otherwise arrows won't work
    shell = FreeMind()
    try:
        shell.boot()
    except KeyboardInterrupt:
        print()
    except Exception as e:
        print(f"critical: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
