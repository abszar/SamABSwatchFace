# SamABSwatchFace — Design Spec

Date: 2026-08-22
Target device: Samsung Galaxy Watch 5 Pro (450×450 round, Wear OS 5 / One UI Watch 6)
Distribution: sideload via ADB to the owner's watch (no Play Store publishing)

## Goal

A Watch Face Format (WFF) v2 digital watch face reproducing the provided mockup:
black background, blue (#3B82F6-family) accent, bold condensed digits, dense
informational layout (weather, forecast, health, dual battery).

## Approach

- **Watch Face Format v2** — declarative XML only, no runtime code.
- Single Gradle module `watchface/`, debug-signed APK, installed with `adb install`.
- Package: `com.abszar.samabwatchface`.
- Data that WFF cannot provide natively is exposed as **styled complication
  slots**; the user assigns providers on the watch (Samsung Health, One UI
  phone battery).

## Project structure

```
SamABSwatchFace/
├── settings.gradle.kts
├── gradle/ + gradlew            (wrapper)
├── tools/
│   └── gen_background.py        (generates bezel/background PNG + weather icons if needed)
├── install.sh                   (build + adb install helper)
└── watchface/
    ├── build.gradle.kts
    └── src/main/
        ├── AndroidManifest.xml
        ├── res/raw/watchface.xml        (entire face definition)
        ├── res/xml/watch_face_info.xml
        ├── res/drawable*/               (background, icons, preview)
        └── res/font/                    (bundled condensed bold font)
```

## Face layout (interactive mode), top → bottom

1. **Bezel**: minute tick marks + blue accent arcs, pre-rendered into a
   background PNG by `tools/gen_background.py` (script committed; PNG committed).
2. **Seconds indicator**: small blue filled circle orbiting the bezel radius,
   rotated `SECOND × 6°` around center — ticks once per second (no smooth
   sweep, for battery). Hidden in ambient mode.
3. **Weather header**: current condition icon + temperature (native
   `[WEATHER.CONDITION]` / `[WEATHER.TEMPERATURE]`, unit follows watch
   setting), location name with pin icon below.
4. **Date line**: localized full date (e.g. `SATURDAY, 22 AUGUST 2026`),
   follows watch language.
5. **Big time**: HH:MM — hours blue, minutes white, blue colon dots; follows
   the watch 12/24h setting; bundled condensed bold font.
6. **Day strip**: 7 localized short day names MON–SUN; current day highlighted
   with a blue rounded outline (conditional on `[DAY_OF_WEEK]`).
7. **Hourly forecast row**: 6 columns (hour label — first column "NOW",
   condition icon, temperature) from native WFF hourly forecast
   (`[WEATHER.HOURS.n.*]`).
8. **Health row**:
   - Left: **sleep** complication slot (SHORT_TEXT/SMALL_IMAGE; intended
     provider Samsung Health Sleep).
   - Center: **native step count** `[STEP_COUNT]` with progress bar toward
     `[STEP_GOAL]`; beneath it one **small complication slot** for
     distance-or-calories (provider's choice — no native WFF source).
   - Right: **sleep score** complication slot (RANGED_VALUE ring, styled with
     purple/blue ring per mockup).
9. **Bottom battery pair**:
   - Left: **watch battery** — native `[BATTERY_PERCENT]`, segmented ring arc
     colored blue→yellow→orange→red by level, % text + label.
   - Right: **phone battery** — RANGED_VALUE complication slot styled
     identically (intended provider: One UI Phone battery).
   - Small link icon between them (static).

## Ambient / always-on mode

Minimal dimmed variant: time + date only, thin/dimmed rendering, no seconds
dot, no complications, black background (OLED burn-in safe).

## Accepted constraints

- Complication slot content (sleep, sleep score, km/kcal, phone battery) is
  provider-rendered data: position/size/colors/fonts are ours, exact wording
  is not (e.g. sleep time range "23:45 – 07:17" depends on Samsung Health).
- Weather requires Wear OS 5 (confirmed on device) and location permission
  granted to the watch's weather provider.

## Build & install

- Install Android cmdline-tools + platform/build-tools 34 under `~/Android/Sdk`
  (machine currently has Java 17, gradle, adb; no SDK).
- `./gradlew :watchface:assembleDebug` → debug APK.
- Validate `watchface.xml` with Google's WFF validator during development.
- Optional visual check on a Wear OS emulator before the real watch.
- Install: watch in Developer options → Wireless debugging; `adb pair` /
  `adb connect <ip:port>`, then `install.sh` (`adb install -r ...`), select the
  face on watch.

## Testing

- WFF XML validator passes (format v2).
- APK builds reproducibly with the wrapper.
- Emulator screenshot review vs mockup.
- On-device: complication slots accept the intended providers; weather
  populates; ambient mode renders; battery drain acceptable over a day.

## Git / GitHub

- Public repo `abszar/SamABSwatchFace`, git init from project start,
  incremental commits.
- House rules: no "Anthropic" mention in commit messages; no `.md` / plan /
  demo-HTML files committed (this spec stays local).
