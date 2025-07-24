[app]
# Application configuration
title = Call Center Sync
package.name = callcentersync
package.domain = com.callcenter.sync

# Source code settings
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json

# Application version and entry point
version = 1.0
version.regex = __version__ = ['"]([^'"]*)['"]
version.filename = %(source.dir)s/main.py

# Entry point
source.main = main.py

# Requirements - reduced to essential only
requirements = python3,kivy==2.1.0,requests,pyjnius,android

# Icon (optional - remove if you don't have one)
# icon.filename = %(source.dir)s/icon.png

# Presplash (optional - remove if you don't have one)  
# presplash.filename = %(source.dir)s/presplash.png

# Supported orientations
orientation = portrait

# Services (none needed for this app)
services = 

# Skip dist info
skip_dist = 1

[android]
# Android API settings - using stable versions
android.api = 31
android.minapi = 21
android.ndk = 23c
android.sdk = 31

# NDK path (let buildozer handle it)
android.accept_sdk_license = True

# Permissions required by the app
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,WAKE_LOCK

# Architecture - focus on common ones for CI
android.archs = arm64-v8a

# Application metadata
android.meta_data = 

# Gradle dependencies (none needed)
android.gradle_dependencies = 

# Java source directory (not needed)
# android.add_src = 

# Bootstrap (use stable version)
p4a.bootstrap = sdl2

# Build tools version
android.gradle_repositories = google(), mavenCentral()

# Release keystore (for production builds)
# android.debug_keystore = ~/.android/debug.keystore

[buildozer]
# Buildozer settings
log_level = 2
warn_on_root = 0

# Build directory
build_dir = ./.buildozer

# Binary directory  
bin_dir = ./bin