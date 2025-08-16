[app]

# (str) Title of your application
title = Kortahun United

# (str) Package name
package.name = kortahununited

# (str) Package domain (needed for android/ios packaging)
package.domain = com.kortahununited

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec,pyc,pyo

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, .git, .github, __pycache__, .pytest_cache, .buildozer, .vscode, .idea, node_modules, .mypy_cache

# (str) Application versioning (method 1)
version = 2.0.0

# (list) Application requirements - Compatible versions
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests==2.31.0,urllib3==2.0.7,certifi,charset-normalizer,idna,pyjnius==1.4.2,android,plyer==2.1.0

# (str) Supported orientation (landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
android.presplash_color = #2196F3

# (list) Permissions - Updated for compatibility
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,CAMERA,WAKE_LOCK,VIBRATE,ACCESS_WIFI_STATE

# (list) Android application meta-data to set (key=value format)
android.meta_data = android.max_aspect=2.5

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D KortahunUnited:D

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a,armeabi-v7a

# (int) overrides automatic versionCode computation (used in build.gradle)
android.numeric_version = 200

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (bool) Skip byte compile for .py files
android.no-byte-compile-python = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

# (int) Android API to use (targetSdkVersion AND compileSdkVersion) - Stable version
android.api = 30

# (int) Minimum API your APK / AAB will support - Compatible version
android.minapi = 21

# (str) Android NDK version to use - Stable version
android.ndk = 23b

# (int) Android NDK API to use. This is the minimum API your app will support
android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (bool) If True, then skip trying to update the Android sdk
android.skip_update = False

# (bool) If True, then automatically accept SDK license agreements
android.accept_sdk_license = True

# (list) Gradle dependencies - Compatible versions
android.gradle_dependencies = com.android.support:support-v4:28.0.0

# (str) Bootstrap to use for android builds - sdl2 is recommended for Kivy apps
p4a.bootstrap = sdl2

# Control passing the --use-setup-py vs --ignore-setup-py to p4a
p4a.setup_py = false

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1