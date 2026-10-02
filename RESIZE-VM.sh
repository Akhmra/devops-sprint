#!/bin/bash
# Расширение корневого раздела после увеличения диска в панели Cloud.ru.
# Запускать ПОСЛЕ того, как в панели диск стал больше (например 15 -> 40 ГБ):
#     bash ~/devops-sprint/RESIZE-VM.sh
#
# Схема разделов на этой ВМ: vda1 (/boot), vda2 — расширенный, vda5 — логический (LVM PV).
# Поэтому растягиваем СНАЧАЛА расширенный раздел, потом логический: если сделать наоборот,
# growpart падает с "Failed to add #3 partition: No space left on device"
# (проверено 02.10.2026 на копии диска — при этом таблица откатывается, данные целы).
set -e

echo "== до =="
lsblk
df -h / | tail -1
free -m | head -2

PV=$(sudo pvs --noheadings -o pv_name | tr -d ' ')
[ -n "$PV" ] || { echo "Не нашёл физический том LVM"; exit 1; }
PART=$(basename "$PV")                 # vda5
DISK=${PART%%[0-9]*}                   # vda
NUM=${PART##*[!0-9]}                   # 5
EXTNUM=$(sudo sfdisk --dump "/dev/$DISK" 2>/dev/null | awk '/type=5|type=f|type=85/ {print $1; exit}')
EXTNUM=${EXTNUM##*[!0-9]}
echo "Диск /dev/$DISK: PV $PV (раздел $NUM), расширенный раздел: ${EXTNUM:-нет}"

# заставляем ядро перечитать размер диска (если увеличен на ходу, без перезагрузки)
echo 1 | sudo tee "/sys/block/$DISK/device/rescan" >/dev/null 2>&1 || true
# защита: если диск в системе не вырос, ничего не делаем
DISKSZ=$(sudo lsblk -bdno SIZE "/dev/$DISK")
PVSZ=$(sudo /sbin/blockdev --getsize64 "$PV" 2>/dev/null || echo 0)
if [ -z "$FORCE" ] && [ $((DISKSZ - PVSZ)) -lt $((1024 * 1024 * 1024)) ]; then
    echo "ВНИМАНИЕ: диск в системе не вырос ($((DISKSZ/1024/1024/1024)) ГБ) — в панели Cloud.ru он ещё не увеличен"
    echo "(или ВМ не перезагружена). Сначала увеличь диск, потом запускай этот скрипт."
    echo "Продолжить всё равно: FORCE=1 bash RESIZE-VM.sh"
    exit 1
fi

# 1. расширенный раздел до конца диска, затем логический с LVM
[ -n "$EXTNUM" ] && sudo growpart "/dev/$DISK" "$EXTNUM" || true   # NOCHANGE — это не ошибка
sudo growpart "/dev/$DISK" "$NUM" || true
sudo partx -u "/dev/$DISK" 2>/dev/null || true

# 2. PV -> LV root
sudo /sbin/pvresize "$PV"
sudo /sbin/lvextend -l +100%FREE /dev/mapper/debian11--vg-root

# 3. файловая система на ходу (ext4)
sudo /sbin/resize2fs /dev/mapper/debian11--vg-root

echo "== после =="
df -h / | tail -1
sudo /sbin/vgs --units g | tail -2
free -m | head -2
echo
echo "Готово. Если менял RAM — проверь: free -m (ожидается 8192 МБ)."
