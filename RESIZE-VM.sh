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

# пытаемся заставить ядро перечитать размер диска. У virtio-blk файла rescan НЕТ (это атрибут SCSI),
# но в этом ядре драйвер умеет перечитывать ёмкость по событию от гипервизора (virtblk_update_capacity),
# поэтому чаще всего новый размер уже виден: проверь lsblk -bdno SIZE. Если нет — полный power-off/on ВМ.
if [ -e "/sys/block/$DISK/device/rescan" ]; then
    echo 1 | sudo tee "/sys/block/$DISK/device/rescan" >/dev/null 2>&1 || true
else
    echo "Примечание: /sys/block/$DISK/device/rescan недоступен (virtio-blk, а не SCSI). Драйвер может"
    echo "подхватить новый размер сам; если lsblk -bdno SIZE /dev/$DISK всё ещё показывает $(( $(sudo lsblk -bdno SIZE /dev/$DISK) / 1024/1024/1024 )) ГБ — нужен Выключить -> Включить ВМ."
fi

# Сколько места в конце диска НЕ занято разделами — считать через start+size!
# ВАЖНО: раздел vda5 начинается со смещения 1001472 сектора (~513 МБ), поэтому «размер диска минус
# размер раздела» врёт: даёт ложные 489 МБ свободного там, где хвост диска уже нулевой.
STARTSEC=$(cat "/sys/block/$DISK/$PART/start")
SIZESEC=$(cat "/sys/block/$DISK/$PART/size")
DISKSEC=$(( $(sudo lsblk -bdno SIZE "/dev/$DISK") / 512 ))
FREESEC=$(( DISKSEC - STARTSEC - SIZESEC ))
DISKSZ=$(( DISKSEC * 512 ))
if [ $((FREESEC * 512)) -lt $((1024 * 1024)) ]; then
    echo "Расти нечего: диск $((DISKSZ/1024/1024/1024)) ГБ полностью разложен по разделам (хвост $((FREESEC * 512)) байт)."
    echo "Если в панели ты только что заказал диск побольше — до ОС новый размер не дошёл. Проверь:"
    echo "  Инфраструктура -> Виртуальные машины -> ВМ -> вкладка «Диски» -> системный диск -> Размер,"
    echo "  затем Выключить -> Включить ВМ (рост на ходу драйвер замечает не всегда) и запусти этот скрипт снова."
    exit 0
fi
echo "В конце диска не занято $((FREESEC * 512 / 1024 / 1024)) МБ — есть что растягивать."

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
