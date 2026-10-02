#!/bin/bash
# Расширение корневого раздела после увеличения диска в панели Cloud.ru.
# Запускать ПОСЛЕ того, как в панели диск стал больше (например 15 -> 40 ГБ):
#     bash ~/devops-sprint/RESIZE-VM.sh
# Ничего не удаляет: растягивает раздел с LVM PV до конца диска, затем PV -> LV root -> ФС.
set -e

echo "== до =="
lsblk
df -h / | tail -1
free -m | head -2

PV=$(sudo pvs --noheadings -o pv_name | tr -d ' ')
[ -n "$PV" ] || { echo "Не нашёл физический том LVM"; exit 1; }
PART=$(basename "$PV")                 # например vda5
DISK=${PART%%[0-9]*}                   # vda
NUM=${PART##*[!0-9]}                   # 5
echo "PV: $PV (диск /dev/$DISK, раздел $NUM)"

# 1. раздел до конца диска (growpart из cloud-guest-utils сам тянет extended-контейнер)
sudo growpart "/dev/$DISK" "$NUM"

# 2. PV -> LV root
sudo /sbin/pvresize "$PV"
sudo /sbin/lvextend -l +100%FREE /dev/mapper/debian11--vg-root

# 3. файловая система на ходу (ext4)
sudo /sbin/resize2fs /dev/mapper/debian11--vg-root

echo "== после =="
df -h / | tail -1
sudo /sbin/vgs --units g | tail -2
echo
echo "Готово. При смене RAM перезагрузка обычно нужна — проверить: free -m (должно быть 8192 МБ)."
echo "Если growpart отказался (нумерация разделов иная):"
echo "  apt-get install -y parted && sudo parted /dev/$DISK resizepart $NUM 100% && повторить шаги 2-3"
