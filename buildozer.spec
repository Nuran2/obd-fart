[app]
title = OBD Fart
package.name = obdfart
package.domain = org.example
source.dir = .
source.include_exts = py
version = 0.1
requirements = python3,kivy,numpy,pyjnius
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_NETWORK_STATE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
