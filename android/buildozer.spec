[app]
title = ytmp3
package.name = ytmp3
package.domain = org.ronanrr
source.dir = .
source.include_exts = py
version = 1.0.0

# Kept to pure-Python deps so python-for-android can build without native recipes.
# Skipping pycryptodomex/brotli means some rare videos may fail; most work fine.
requirements = python3,kivy,yt-dlp,certifi,urllib3,charset-normalizer,idna,requests

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 34
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = 1
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 0
