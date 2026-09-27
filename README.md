# FreeMind OS

A minimalist Linux distribution with a Python shell on top of BusyBox.
No systemd. No GUI. Just kernel + shell.

- **Kernel:** Linux 6.12.103 LTS, `tinyconfig` (**1.6 MB** `bzImage`)
- **Shell:** BusyBox (static/musl) + **miniarch** (Python 3.14)
- **Size:** ~65 MB ISO, ~35 MB initramfs
- **License:** GPL v2

---

## Requirements

**Host OS:** Fedora 40+ (or any distro with equivalent packages).
**Disk:** ~10 GB free. **Time:** ~15 min on modern CPU.

### Fedora

```bash
sudo dnf install gcc make bc flex bison openssl-devel elfutils-libelf-devel \
                 wget tar cpio gzip busybox python3 \
                 grub2-tools grub2-tools-minimal grub2-tools-extra \
                 grub2-efi-x64-modules xorriso mtools
```

### Debian / Ubuntu

```bash
sudo apt install build-essential bc flex bison libssl-dev libelf-dev \
                 wget cpio busybox-static python3 \
                 grub-pc-bin grub-efi-amd64-bin xorriso mtools
```

---

## Build

```bash
git clone https://github.com/wersanil/freemind_os
cd freemind_os
chmod +x build.sh
./build.sh
```

Result: `build/freemind.iso`.

First run downloads the kernel (~145 MB, one time). Subsequent runs reuse
`build/linux-*.tar.xz` if you keep it — but note that `rm -rf build` deletes it.

---

## Run

### QEMU (fastest, no reboot needed)

```bash
# GUI window (VGA)
qemu-system-x86_64 -m 512 -cdrom build/freemind.iso

# Terminal only (serial → your terminal, best for copy/paste)
qemu-system-x86_64 -m 512 -cdrom build/freemind.iso -nographic
```

Inside QEMU, `Ctrl+A` then `X` exits `-nographic`.

### Real hardware (USB stick)

> ⚠️ `dd` destroys data on the target device. Read `lsblk` output twice.

```bash
# 1. Find your USB device — look for the disk, not a partition
lsblk

# 2. Write ISO to USB (replace /dev/sdX with your device, WITHOUT a number)
sudo dd if=build/freemind.iso of=/dev/sdX bs=4M status=progress conv=fsync
sync
```

Boot from USB. Both **BIOS** and **UEFI** are supported via GRUB.

---

## Usage

Type `help` inside miniarch. To drop into BusyBox shell — `shell`.
To return — `exit`.

```
ls  cd  cat  cp  mv  grep  find  tree  less
df  free  uptime  uname  hostname  env  which
calc  calcfig 5 8  neofetch  history  log
shell  reboot  shutdown  exit
```

Arrow keys `↑` / `↓` — command history (saved to `~/.miniarch_history`).
`Shift+PgUp` / `Shift+PgDn` — scroll VGA console.

---

## Links

- Source: <https://github.com/wersanil/freemind_os>
- Releases: <https://github.com/wersanil/freemind_os/releases>

## License

GPL v2. See `LICENSE`.
