[app]
# (str) Title of your application
title = Kortahun United Call Logger

# (str) Package name
package.name = kortahuncalllogger

# (str) Package domain (needed for android/ios packaging)
package.domain = com.kortahununited

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,data/*,*.py

# (str) Application versioning (method 1)
version = 2.0.0

# (list) Application requirements - FIXED: Added requests explicitly and proper formatting
requirements = python3,kivy==2.1.0,requests>=2.25.0,urllib3,pyjnius,android,plyer,pillow,certifi,charset-normalizer,idna

# (str) Presplash of the application
presplash.filename = %(source.dir)s/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
android.presplash_color = #1E3A8A

# (list) Permissions - FIXED: Removed problematic permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK

# (list) features - FIXED: Proper format for features
android.features = android.hardware.telephony

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (str) Android NDK version to use
android.ndk = 25b

# (int) Android NDK API to use. This is the minimum API your app will support
android.ndk_api = 24

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (bool) If True, then skip trying to update the Android sdk
android.skip_update = False

# (bool) If True, then automatically accept SDK license agreements
android.accept_sdk_license = True

# (str) Android app theme, default is ok for Kivy-based app
android.apptheme = "@android:style/Theme.NoTitleBar"

# (bool) Enable AndroidX support
android.enable_androidx = True

# (list) add java compile options
android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"

# (list) Gradle repositories to add
android.gradle_repositories = "google()", "mavenCentral()", "gradlePluginPortal()"

# (list) packaging options to add - FIXED: Added more exclusions for build issues
android.add_packaging_options = "exclude 'META-INF/DEPENDENCIES'", "exclude 'META-INF/LICENSE'", "exclude 'META-INF/LICENSE.txt'", "exclude 'META-INF/NOTICE'", "exclude 'META-INF/NOTICE.txt'", "exclude 'META-INF/*.kotlin_module'", "exclude 'META-INF/common.kotlin_module'"

# (str) launchMode to set for the main activity
android.manifest.launch_mode = singleTop

# (bool) Indicate whether the screen should stay on
android.wakelock = True

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D KortahunUnited:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (list) The Android archs to build for
android.archs = arm64-v8a, armeabi-v7a

# (int) overrides automatic versionCode computation
android.numeric_version = 20

# (bool) enables Android auto backup feature
android.allow_backup = True

# Release configuration
android.release_artifact = aab
android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) python-for-android branch to use
p4a.branch = master

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# Control passing the --private and --dir arguments to p4a
p4a.private_storage = True

#
# Buildozer (global) settings
#

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
bin_dir = ./bin

# Exclude unnecessary files from the build - FIXED: Added more exclusions
[app:source.exclude_patterns]
license
*.pyc
*.pyo
*.git*
*/__pycache__/*
*/.*
*~
*.bak
*.swp
*.tmp
.DS_Store
Thumbs.db
.buildozer/*
bin/*
venv/*
env/*
.env
*.log
tests/*
test_*
*_test.py
README.md
*.md
docs/*
# FIXED: Exclude problematic Python test files
*/test/*
*/tests/*
**/test/**
**/tests/**
lib/python*/test/*
lib/python*/tests/*

# Development profile
[app@dev]
title = %(title)s (Dev)

# Production profile
[app@production]
title = %(title)s
android.release_artifact = aab