#!/bin/bash
# FreeMind OS builder — минималистичная сборка (tinyconfig kernel + BusyBox + miniarch)
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   FreeMind OS — BusyBox + miniarch (основной шелл)      ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"

WORK_DIR="$PWD/build"
ROOTFS_DIR="$WORK_DIR/rootfs"
ISO_DIR="$WORK_DIR/iso"
KERNEL_VERSION="6.12.103"
MINIARCH_SRC="$PWD/miniarch.py"
KARCH="x86_64"

# ─── Проверка зависимостей ────────────────────────────────────
GRUB_MKRESCUE=""
for cand in grub-mkrescue grub2-mkrescue; do
    if command -v "$cand" >/dev/null 2>&1; then
        GRUB_MKRESCUE="$cand"; break
    fi
done

missing=0
for tool in wget tar make cpio gzip busybox python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo -e "${RED}❌ Отсутствует: $tool${NC}"
        missing=1
    fi
done

if [ -z "$GRUB_MKRESCUE" ]; then
    echo -e "${RED}❌ grub-mkrescue / grub2-mkrescue не найден${NC}"
    missing=1
fi

[ "$missing" -eq 1 ] && exit 1

if [ ! -f "$MINIARCH_SRC" ]; then
    echo -e "${RED}❌ miniarch.py не найден!${NC}"
    exit 1
fi

# ─── [1/6] Каркас ─────────────────────────────────────────────
echo -e "${YELLOW}[1/6] Создание папок...${NC}"
rm -rf "$WORK_DIR"
mkdir -p "$ROOTFS_DIR"/{bin,sbin,etc/init.d,proc,sys,dev,tmp,root,home/user}
mkdir -p "$ROOTFS_DIR"/usr/{bin,sbin,lib,lib64}
mkdir -p "$ROOTFS_DIR"/var/{log,run}
mkdir -p "$ISO_DIR"/boot/grub

# ─── [2/6] Ядро: скачивание ───────────────────────────────────
echo -e "${YELLOW}[2/6] Скачивание ядра $KERNEL_VERSION...${NC}"
if [ ! -f "$WORK_DIR/linux-$KERNEL_VERSION.tar.xz" ]; then
    wget -O "$WORK_DIR/linux-$KERNEL_VERSION.tar.xz" \
        "https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-$KERNEL_VERSION.tar.xz"
fi
tar -xf "$WORK_DIR/linux-$KERNEL_VERSION.tar.xz" -C "$WORK_DIR"

# ─── [3/6] Ядро: tinyconfig + точечные опции ──────────────────
echo -e "${YELLOW}[3/6] Конфигурация и сборка ядра (ARCH=$KARCH)...${NC}"
cd "$WORK_DIR/linux-$KERNEL_VERSION"

# tinyconfig для 64-битного x86 — обязательно с ARCH=x86_64,
# иначе Kbuild сделает 32-битный i386-конфиг
make ARCH="$KARCH" tinyconfig

# Шаг 1: базовые опции архитектуры. 64BIT — ПЕРВЫМ, до всего остального.
./scripts/config --file .config \
    --enable  64BIT \
    --enable  X86_64 \
    --enable  SMP \
    --enable  MMU \
    --enable  X86_MSR \
    --enable  X86_CPUID

# Шаг 2: всё остальное
./scripts/config --file .config \
    --enable  BINFMT_ELF \
    --enable  BINFMT_SCRIPT \
    --enable  MULTIUSER \
    --enable  FHANDLE \
    --enable  FUTEX \
    --enable  EPOLL \
    --enable  EVENTFD \
    --enable  SIGNALFD \
    --enable  TIMERFD \
    --enable  SHMEM \
    --enable  AIO \
    --enable  POSIX_TIMERS \
    --enable  TMPFS \
    --enable  TMPFS_POSIX_ACL \
    --enable  TMPFS_XATTR \
    --enable  DEVTMPFS \
    --enable  DEVTMPFS_MOUNT \
    --enable  PROC_FS \
    --enable  SYSFS \
    --enable  EXT4_FS \
    --enable  EXT4_USE_FOR_EXT2 \
    --enable  PRINTK \
    --enable  TTY \
    --enable  VT \
    --enable  VT_CONSOLE \
    --enable  VGA_CONSOLE \
    --enable  DUMMY_CONSOLE \
    --enable  UNIX98_PTYS \
    --enable  INPUT \
    --enable  KEYBOARD_ATKBD \
    --enable  SERIO \
    --enable  SERIO_I8042 \
    --enable  SERIAL_8250 \
    --enable  SERIAL_8250_CONSOLE \
    --enable  BLK_DEV_INITRD \
    --enable  RD_GZIP \
    --enable  BLK_DEV_SD \
    --enable  SCSI \
    --enable  ATA \
    --enable  ATA_PIIX \
    --enable  VIRTIO \
    --enable  VIRTIO_PCI \
    --enable  VIRTIO_BLK \
    --enable  VIRTIO_NET \
    --enable  E1000 \
    --enable  NET \
    --enable  PACKET \
    --enable  UNIX \
    --enable  INET \
    --enable  PCI \
    --enable  PCI_MSI \
    --enable  HW_RANDOM \
    --enable  HW_RANDOM_VIRTIO \
    --enable  RANDOM_TRUST_CPU \
    --enable  RANDOM_TRUST_BOOTLOADER \
    --enable  CONSOLE_TRANSLATIONS \
    --enable  NLS \
    --enable  NLS_UTF8 \
    --enable  FONTS \
    --enable  FONT_8x16 \
    --enable  FONT_AUTOSELECT \
    --enable  FRAMEBUFFER_CONSOLE \
    --disable MODULES \
    --disable COMPAT \
    --disable IA32_EMULATION \
    --disable SOUND \
    --disable USB_SUPPORT \
    --disable WLAN \
    --disable BT \
    --disable DRM \
    --disable MEDIA_SUPPORT \
    --disable FB \
    --disable HID \
    --disable IPV6 \
    --disable NETFILTER \
    --disable WIRELESS \
    --disable BTRFS_FS \
    --disable XFS_FS \
    --disable F2FS_FS \
    --disable NTFS_FS \
    --disable MSDOS_FS \
    --disable VFAT_FS \
    --disable NFS_FS \
    --disable CIFS \
    --disable ISO9660_FS \
    --disable SQUASHFS \
    --disable MD \
    --disable BLK_DEV_DM \
    --disable KVM \
    --disable XEN \
    --disable HYPERV

make ARCH="$KARCH" olddefconfig

# Шаг 3: КРИТИЧНО — вернуть 64BIT и binfmt после olddefconfig (иначе снимутся)
./scripts/config --file .config --enable 64BIT
./scripts/config --file .config --enable BINFMT_ELF
./scripts/config --file .config --enable BINFMT_SCRIPT
make ARCH="$KARCH" olddefconfig

# Шаг 4: валидация конфига — падаем до сборки, если чего-то нет
fail=0
for opt in 64BIT BINFMT_ELF BINFMT_SCRIPT DEVTMPFS DEVTMPFS_MOUNT \
           BLK_DEV_INITRD RD_GZIP TMPFS PROC_FS SYSFS; do
    if ! grep -q "^CONFIG_${opt}=y" .config; then
        echo -e "${RED}❌ CONFIG_${opt} не включён в .config${NC}"
        fail=1
    fi
done
if [ "$fail" -eq 1 ]; then
    echo -e "${RED}Ядро не собрано: конфиг неполный.${NC}"
    exit 1
fi

# Шаг 5: сборка
make ARCH="$KARCH" -j"$(nproc)" bzImage

# Шаг 6: финальная проверка — ядро должно быть 64-битным
if ! file vmlinux | grep -q 'ELF 64-bit'; then
    echo -e "${RED}❌ vmlinux не 64-битный! Проверь ARCH и CONFIG_64BIT.${NC}"
    file vmlinux
    exit 1
fi

cp arch/x86/boot/bzImage "$ISO_DIR/boot/vmlinuz"
echo -e "${GREEN}→ Ядро: $(file arch/x86/boot/bzImage | cut -d: -f2 | cut -c1-40)…${NC}"
echo -e "${GREEN}→ Размер ядра: $(du -h "$ISO_DIR/boot/vmlinuz" | cut -f1)${NC}"

# ─── [4/6] rootfs ─────────────────────────────────────────────
echo -e "${YELLOW}[4/6] Создание rootfs...${NC}"
cd "$ROOTFS_DIR"

# --- BusyBox (Fedora: busybox.static может быть симлинком на busybox) ---
BUSYBOX_BIN=""
for p in /usr/bin/busybox.static /usr/bin/busybox.musl.static \
         /bin/busybox /usr/bin/busybox /usr/local/bin/busybox; do
    if [ -x "$p" ] || [ -L "$p" ]; then
        if [ -x "$(readlink -f "$p" 2>/dev/null || echo "$p")" ]; then
            BUSYBOX_BIN="$p"; break
        fi
    fi
done
if [ -z "$BUSYBOX_BIN" ]; then
    echo -e "${RED}❌ BusyBox не найден. Установи: dnf install busybox${NC}"
    exit 1
fi
echo -e "${GREEN}→ BusyBox: $BUSYBOX_BIN${NC}"

cp -L "$BUSYBOX_BIN" bin/busybox
chmod +x bin/busybox

for cmd in sh ls cat vi grep sed awk ps top mount umount cp mv rm mkdir rmdir \
           echo ifconfig route ping netstat ip udhcpc clear dmesg \
           head tail wc sort uniq tr cut find xargs which env \
           uname hostname id whoami date sleep seq \
           chmod chown ln stat touch sync tar gzip gunzip \
           df du free uptime mknod mkfifo mountpoint \
           setfont loadkmap; do
    ln -sf /bin/busybox "bin/$cmd"
done
for cmd in reboot poweroff halt; do
    ln -sf /bin/busybox "sbin/$cmd"
done
# /sbin/init — скрипт, а не симлинк. Это надёжнее для ядра на раннем этапе.
cat > sbin/init << 'EOF'
#!/bin/busybox sh
exec /bin/busybox init
EOF
chmod +x sbin/init

# --- Python ---
echo -e "${YELLOW}Копирование Python...${NC}"
PYTHON_BIN=$(command -v python3)
cp -L "$PYTHON_BIN" usr/bin/python3

PY_STDLIB=$(python3 -c "import sysconfig; print(sysconfig.get_path('stdlib'))")
PY_LIBDIR=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('platlibdir') or 'lib')")
PY_VER=$(python3 -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")

# На Fedora Python ищет stdlib в /usr/<platlibdir>/pythonX.Y — обычно /usr/lib64/pythonX.Y.
# platstdlib указывает на /usr/local/... (пусто) — его игнорируем.
# lib-dynload лежит ВНУТРИ stdlib (например /usr/lib64/pythonX.Y/lib-dynload),
# и sys.path по умолчанию смотрит именно туда.
TARGET_STD="$ROOTFS_DIR/usr/$PY_LIBDIR/$PY_VER"
mkdir -p "$TARGET_STD"
cp -a "$PY_STDLIB/." "$TARGET_STD/"

# Обрезка stdlib
STD="$TARGET_STD"
rm -rf "$STD"/test "$STD"/tests "$STD"/idlelib "$STD"/tkinter 2>/dev/null || true
rm -rf "$STD"/ensurepip "$STD"/distutils "$STD"/lib2to3 2>/dev/null || true
rm -rf "$STD"/pydoc_data "$STD"/turtledemo "$STD"/unittest 2>/dev/null || true
rm -rf "$STD"/asyncio "$STD"/concurrent "$STD"/multiprocessing 2>/dev/null || true
rm -rf "$STD"/sqlite3 "$STD"/curses "$STD"/dbm "$STD"/wsgiref 2>/dev/null || true
rm -rf "$STD"/venv "$STD"/site-packages "$STD"/__pycache__ 2>/dev/null || true
rm -rf "$STD"/email "$STD"/http "$STD"/xml "$STD"/urllib 2>/dev/null || true
rm -rf "$STD"/html "$STD"/json "$STD"/xmlrpc 2>/dev/null || true
find "$STD" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find "$STD" -name '*.pyc' -delete 2>/dev/null || true

# Жёсткая проверка — без encodings Python не стартует
if [ ! -d "$STD/encodings" ]; then
    echo -e "${RED}❌ $STD/encodings отсутствует${NC}"
    exit 1
fi
if [ ! -d "$STD/lib-dynload" ]; then
    echo -e "${YELLOW}⚠  $STD/lib-dynload отсутствует — Python запустится, но без C-расширений${NC}"
fi
echo -e "${GREEN}→ stdlib: usr/$PY_LIBDIR/$PY_VER ($(du -sh "$STD" | cut -f1))${NC}"

# --- Динамический линковщик ---
mkdir -p lib lib64
for cand in \
    /lib64/ld-linux-x86-64.so.2 \
    /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
    /usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
do
    if [ -f "$cand" ]; then
        cp -L "$cand" lib64/ld-linux-x86-64.so.2
        break
    fi
done

# --- Собрать .so, от которых зависят python3 и его C-расширения ---
collect_deps() {
    ldd "$1" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i ~ /^\//) print $i}'
}

{
    collect_deps "$PYTHON_BIN"
    if [ -d "$TARGET_STD/lib-dynload" ]; then
        find "$TARGET_STD/lib-dynload" -name '*.so' -exec ldd {} \; 2>/dev/null \
            | awk '{for(i=1;i<=NF;i++) if($i ~ /^\//) print $i}'
    fi
} | sort -u | while read -r lib; do
    [ -f "$lib" ] || continue
    name=$(basename "$lib")
    case "$lib" in
        */lib64/*)
            [ -f "lib64/$name" ] || cp -L "$lib" lib64/
            [ -f "lib/$name" ]   || cp -L "$lib" lib/
            ;;
        */lib/*)
            [ -f "lib/$name" ] || cp -L "$lib" lib/
            ;;
    esac
done

# --- Кириллический шрифт для VGA-консоли ---
FONT_SRC=""
for cand in \
    /usr/lib/kbd/consolefonts/latcyrheb-sun16.psf.gz \
    /usr/lib/kbd/consolefonts/Cyr_a8x16.psf.gz \
    /usr/lib/kbd/consolefonts/UniCyr_8x16.psf.gz \
    /usr/share/consolefonts/latcyrheb-sun16.psf.gz \
    /usr/share/consolefonts/Cyr_a8x16.psf.gz
do
    [ -f "$cand" ] && { FONT_SRC="$cand"; break; }
done
if [ -z "$FONT_SRC" ]; then
    echo -e "${YELLOW}⚠  .psf кириллический не найден — установи: dnf install kbd-misc${NC}"
else
    cp -L "$FONT_SRC" etc/consolefont.psf.gz
    echo -e "${GREEN}→ Шрифт: $(basename "$FONT_SRC")${NC}"
fi

# --- miniarch ---
cp "$MINIARCH_SRC" usr/bin/miniarch
chmod +x usr/bin/miniarch

cat > bin/miniarch-shell << 'EOF'
#!/bin/sh
exec /usr/bin/python3 /usr/bin/miniarch "$@"
EOF
chmod +x bin/miniarch-shell

# --- /etc/inittab ---
cat > etc/inittab << 'EOF'
::sysinit:/etc/init.d/rcS
::respawn:/usr/bin/miniarch
::ctrlaltdel:/sbin/reboot
::shutdown:/bin/umount -a -r
::restart:/sbin/init
EOF

# --- /etc/init.d/rcS ---
cat > etc/init.d/rcS << 'EOF'
#!/bin/sh
# /dev уже смонтирован ядром через CONFIG_DEVTMPFS_MOUNT=y.
# НЕ монтируем поверх него tmpfs — иначе стираем /dev/null, /dev/urandom и т.д.
if ! [ -e /dev/null ]; then
    mount -t devtmpfs devtmpfs /dev 2>/dev/null || mount -t tmpfs tmpfs /dev
fi
mount -t proc  proc  /proc 2>/dev/null
mount -t sysfs sysfs /sys  2>/dev/null
mkdir -p /dev/pts /dev/shm /tmp
mount -t devpts devpts /dev/pts 2>/dev/null
mount -t tmpfs  tmpfs  /dev/shm 2>/dev/null
mount -t tmpfs  tmpfs  /tmp     2>/dev/null
[ -c /dev/null ]    || mknod -m 666 /dev/null    c 1 3
[ -c /dev/zero ]    || mknod -m 666 /dev/zero    c 1 5
[ -c /dev/urandom ] || mknod -m 666 /dev/urandom c 1 9
[ -c /dev/random ]  || mknod -m 666 /dev/random  c 1 8
[ -c /dev/tty ]     || mknod -m 666 /dev/tty     c 5 0
# --- Русский язык: шрифт + UTF-8 ---
[ -f /etc/consolefont.psf.gz ] && setfont -u /etc/consolefont.psf.gz 2>/dev/null

export HOME=/home/user
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export TERM=linux
export PYTHONDONTWRITEBYTECODE=1
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
# --- UTF-8 режим VGA-консоли (KDSKBMODE=K_UNICODE) ---
/usr/bin/python3 - <<PYUTF8 2>/dev/null || true
import fcntl, os
KDSKBMODE = 0x4B45
K_UNICODE = 0x01
for tty in ("/dev/tty0", "/dev/tty1", "/dev/console"):
    try:
        fd = os.open(tty, os.O_RDWR)
        fcntl.ioctl(fd, KDSKBMODE, K_UNICODE)
        os.close(fd)
    except OSError:
        pass
PYUTF8

hostname freemind 2>/dev/null || true
EOF
chmod +x etc/init.d/rcS

# --- Профиль и motd ---
cat > etc/profile << 'EOF'
export HOME=/home/user
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export TERM=linux
export PYTHONDONTWRITEBYTECODE=1
EOF

cat > etc/motd << 'EOF'

  FreeMind OS 0.5   •   "Свобода. Простота. Контроль"
  ───────────────────────────────────────────────────
  miniarch запущен автоматически.
  Прокрутка: Shift+PgUp / Shift+PgDn
  История команд: ↑ / ↓   •   Список: history
  Выход в BusyBox: shell   •   Справка: help

EOF

# --- Быстрая самопроверка rootfs ---
if ! file bin/busybox | grep -q 'ELF 64-bit'; then
    echo -e "${RED}❌ bin/busybox не ELF64!${NC}"
    file bin/busybox
    exit 1
fi

# ─── [5/6] initramfs ──────────────────────────────────────────
echo -e "${YELLOW}[5/6] Создание initramfs...${NC}"
cd "$ROOTFS_DIR"
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
find . -name '*.pyc' -delete 2>/dev/null || true
find . | cpio -o -H newc 2>/dev/null | gzip -9 > "$ISO_DIR/boot/initramfs.img"
echo -e "${GREEN}→ Размер initramfs: $(du -h "$ISO_DIR/boot/initramfs.img" | cut -f1)${NC}"

# ─── [6/6] GRUB + ISO ─────────────────────────────────────────
echo -e "${YELLOW}[6/6] Сборка ISO...${NC}"

cat > "$ISO_DIR/boot/grub/grub.cfg" << 'EOF'
set default=0
set timeout=3

menuentry "FreeMind OS (serial + VGA)" {
    linux /boot/vmlinuz console=ttyS0,115200 console=tty0 root=/dev/ram0 init=/sbin/init quiet
    initrd /boot/initramfs.img
}

menuentry "FreeMind OS (verbose)" {
    linux /boot/vmlinuz console=ttyS0,115200 console=tty0 root=/dev/ram0 init=/sbin/init
    initrd /boot/initramfs.img
}
EOF

"$GRUB_MKRESCUE" -o "$WORK_DIR/freemind.iso" "$ISO_DIR" 2>/dev/null

echo -e "${GREEN}✅ Готово!${NC}"
ls -lh "$WORK_DIR/freemind.iso"
echo
echo -e "${GREEN}Запуск в QEMU (serial):${NC}"
echo "  qemu-system-x86_64 -m 512 -cdrom build/freemind.iso -nographic"
echo -e "${GREEN}Запуск в QEMU (окно, есть Shift+PgUp/PgDn):${NC}"
echo "  qemu-system-x86_64 -m 512 -cdrom build/freemind.iso"
