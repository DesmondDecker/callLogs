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

# Requirements - essential only for stability
requirements = python3,kivy==2.1.0,requests,pyjnius,android

# Icon and presplash (uncomment if you have them)
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Supported orientations
orientation = portrait

# Services (none needed for this app)
services = 

# Skip dist info to reduce build time
skip_dist = 1

# Fullscreen mode
fullscreen = 0

[android]
# Android API settings - using stable, well-tested versions
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31

# Accept SDK license automatically
android.accept_sdk_license = True

# Permissions required by the app
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,WAKE_LOCK

# Architecture - support both common architectures
android.archs = arm64-v8a,armeabi-v7a

# Application metadata
android.meta_data = 

# Gradle settings
android.gradle_dependencies = 
android.gradle_repositories = google(), mavenCentral()

# Bootstrap - SDL2 is stable and well-supported
p4a.bootstrap = sdl2

# Branch for python-for-android (use stable)
p4a.branch = master

# Local recipes (if any custom recipes are needed)
p4a.local_recipes = 

# Hook for additional setup
# p4a.hook = 

# Add extra Java files or libraries if needed
# android.add_src = 
# android.add_jars = 

# Whitelist for dynamic libraries
# android.whitelist = 

# Private storage permissions
android.private_storage = True

# Wakelock permission usage
android.wakelock = True

# Release keystore settings (for production builds)
# android.debug_keystore = ~/.android/debug.keystore
# android.release_keystore = 
# android.release_keystore_passwd = 
# android.release_keyalias = 
# android.release_keyalias_passwd = 

[buildozer]
# Buildozer settings
log_level = 2
warn_on_root = 1

# Build directory
build_dir = ./.buildozer

# Binary directory  
bin_dir = ./bin

# Exclude patterns (add files/folders to ignore)
exclude_patterns = .git/*,.github/*,*.pyc,*~,__pycache__/*,.pytest_cache/*,venv/*,.venv/*,env/*,.env/*,*.log,*.tmp