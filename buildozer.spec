[app]
# Application configuration
title = Call Center Sync
package.name = callcentersync
package.domain = com.callcenter.sync

# Source code settings
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,json

# Application version
version = 1.0
version.regex = __version__ = ['"]([^'"]*)['"]
version.filename = %(source.dir)s/main.py

# Requirements
requirements = python3,kivy,requests,pyjnius,android

# Android specific settings
[android]
# Android API settings
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31

# Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS

# Architecture
android.archs = arm64-v8a,armeabi-v7a

# Application metadata
android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

# Gradle dependencies
android.gradle_dependencies = 

# Add java src directory for custom java code
android.add_src = java

[buildozer]
# Buildozer settings
log_level = 2
warn_on_root = 1