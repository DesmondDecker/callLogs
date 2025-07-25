[app]

# (str) Title of your application
title = Call Log Sync

# (str) Package name
package.name = calllogsync

# (str) Package domain (needed for android/ios packaging)
package.domain = com.kortahun

# (str) Source code where the main.py is located
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 2.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy>=2.1.0,kivymd>=1.1.1,requests>=2.28.0,pyjnius>=1.4.2,plyer>=2.1,certifi>=2022.12.7

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) Java package name for the service
#service.main = myapp.service.main

# (str) Java package domain for the service
#service.domain = org.example

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin

[android]

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Android Activity
#android.activity_class_name = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Python Service
#android.service_class_name = org.kivy.android.PythonService

# (list) Pattern to whitelist for the whole project
#android.whitelist =

# (bool) Enable AndroidX support. Enable when 'android.gradle_dependencies'
# contains an 'androidx' package, or any package from Kotlin source.
# android.enable_androidx requires android.api >= 28
android.enable_androidx = True

# (str) Android app theme, default is ok for Kivy-based app
# android.theme = "@android:style/Theme.NoTitleBar"

# (list) Java classes to add as activities to the manifest.
#android.add_activities = com.example.ExampleActivity

# (str) OUYA Console category. Should be one of GAME or APP
# If you leave this blank, OUYA support will not be enabled
#android.ouya.category = GAME

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters =

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (list) Android application meta-data to set (key=value format)
android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

# (list) Android library project to add (will be added in the
# project.properties automatically.)
#android.library_references = @jar/my-android-library.jar

# (list) Android shared libraries which will be added to the libs folder.
#android.add_libs_x86 = libs/android/x86/library.so
#android.add_libs_x86_64 = libs/android/x86_64/library.so
#android.add_libs_armeabi = libs/android/armeabi/library.so
#android.add_libs_armeabi_v7a = libs/android/armeabi-v7a/library.so
#android.add_libs_arm64_v8a = libs/android/arm64-v8a/library.so

# (bool) Indicate whether the screen should stay on
# Don't forget to add the WAKE_LOCK permission if you set this to True
android.wakelock = False

# (list) Android gradle dependencies to add
#android.gradle_dependencies =

# (str) python-for-android fork to use, defaults to upstream (kivy)
#p4a.fork = kivy

# (str) python-for-android branch to use, defaults to master
#p4a.branch = master

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
#p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes (if any)
#p4a.local_recipes =

# (str) Filename to the hook for p4a
#p4a.hook =

# (str) Bootstrap to use for android builds
# Run `buildozer android p4a -- bootstraps` to see supported bootstraps.
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument (eg: --port=1024, shorten from 1024)
#p4a.port =

# Control passing the --private data-dir to p4a
# (str) Argument to pass to p4a
# p4a.private_version = current (default)
# p4a.private_version = force-private
# p4a.private_version = force-not-private
p4a.private_version = current

# (str) python-for-android whitelist
#p4a.whitelist =

# (bool) If True, then skip trying to update the Android sdk
# This can be useful to avoid excess Internet downloads or save time
# when an update is due and you just want to test/build your package
android.skip_update = False

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only. If set to False,
# the default, you will be shown the license when first running
# buildozer.
android.accept_sdk_license = True

# (str) Android NDK version to use
android.ndk = 23b

# (int) Android API to use (targetSdkVersion AND compileSdkVersion)
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android SDK version to use
android.sdk = 33

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_dir =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_dir =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_dir =

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# In past, was `android.arch` as we weren't supporting builds for multiple archs at the same time.
android.archs = arm64-v8a, armeabi-v7a

# (int) overrides automatic versionCode computation (used in build.gradle)
# this is not the same as app version and should only be edited if you know what you're doing
# android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) XML file for custom backup rules (see official auto backup documentation)
# android.backup_rules =

# (str) If you need to insert variables into your AndroidManifest.xml file,
# you can do so with the manifestPlaceholders property.
# This property takes a map of key-value pairs. (via a string)
# Usage example : android.manifest_placeholders = [myCustomUrl:\"org.kivy.customurl\"]
# android.manifest_placeholders = [:]

# (bool) Skip byte compile for .py files
# android.no-byte-compile-python = False

# (str) Use 'android.injected_option_*' to pass any other property to the gradle build script.
# android.injected_option_enableProguard = False

# Android permissions
android.permissions = INTERNET,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,ACCESS_NETWORK_STATE,WAKE_LOCK,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

#    -----------------------------------------------------------------------------
#    Profile for release
#    -----------------------------------------------------------------------------

[app:release]

# (str) Build artifact storage for release
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin