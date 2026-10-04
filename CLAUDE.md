# SamAB Face

Wear OS watch face (Watch Face Format) for a Galaxy Watch (SM-R920), sideloaded over Wi-Fi ADB with `./install.sh <watch-ip:port>`.

## Watch connection

- Keep the watch connected while edits are in progress, so each change can be installed without pairing again.
- At the end of every watch face change, ask the user whether they are happy with the edits and whether to disconnect the watch.
- When the user says to disconnect: run `~/Android/Sdk/platform-tools/adb disconnect` and `~/Android/Sdk/platform-tools/adb kill-server`, then remind them to turn off Wireless debugging on the watch (Settings > Developer options). If left on, it keeps the watch's Wi-Fi on all the time, drains the battery and makes the phone connection unstable.
- The watch's connect port changes; `adb mdns services` shows the current one. adb may list the watch twice (by IP and by mDNS name), so install with `adb -s <ip:port> install -r watchface/build/outputs/apk/debug/watchface-debug.apk` if `install.sh` reports "more than one device".
