#!/usr/bin/env bash
# Sideload the watch face to a Galaxy Watch over Wi-Fi ADB.
# On the watch: Settings > Developer options > Wireless debugging > Pair new device
# One-time pairing: adb pair <ip:pairing-port>   (enter the code shown on the watch)
# Usage: ./install.sh <watch-ip:port>
set -euo pipefail
ADB="${ANDROID_HOME:-$HOME/Android/Sdk}/platform-tools/adb"
[ $# -ge 1 ] && "$ADB" connect "$1"
./gradlew :watchface:assembleDebug
"$ADB" install -r watchface/build/outputs/apk/debug/watchface-debug.apk
echo "Installed. Long-press the current watch face on the watch and select 'SamAB Face'."
