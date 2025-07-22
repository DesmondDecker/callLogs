[app]
title = Call Log Monitor
package.name = calllogmonitor
package.domain = com.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy==2.1.0,requests,pyjnius,android,urllib3,plyer
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

[buildozer]
log_level = 2

[android]
permissions = INTERNET,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,ACCESS_NETWORK_STATE
api = 33
minapi = 21
ndk = 25b
accept_sdk_license = True
arch = arm64-v8a,armeabi-v7a

# Prevent autotools conflicts by pinning python-for-android
p4a.branch = master
p4a.bootstrap = sdl2

[android.gradle_dependencies]

[android.add_src]