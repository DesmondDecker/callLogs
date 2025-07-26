[app]

# (str) Title of your application
title = Call Log Sync Pro

# (str) Package name
package.name = callsync

# (str) Package domain (needed for android/ios packaging)
package.domain = com.kortahununited

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt,md

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec,pyc,pyo

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests,bin,.buildozer,venv,__pycache__,.git,.github,docs

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*/*.jpg,*.pyc,*.pyo

# (str) Application versioning (method 1)
version = 2.0.0

# (list) Application requirements - simplified for better compatibility
requirements = python3,kivy,android,pyjnius,plyer,requests,urllib3,certifi,charset-normalizer,idna,python-dateutil,simplejson,colorama,six

# (str) Custom source folders for requirements
# Sets custom source for any requirements with recipes
# requirements.source.kivy = ../../kivy

# (str) Presplash of the application
# presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
# icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) List of service to declare
# services = NAME:ENTRYPOINT_TO_PY,NAME2:ENTRYPOINT2_TO_PY

#
# OSX Specific
#

#
# author = © Copyright Info

# change the major version of python used by the app
osx.python_version = 3

# Kivy version to use
osx.kivy_version = 1.9.1

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (string) Presplash background color (for android toolchain)
android.presplash_color = #FFFFFF

# (string) Presplash animation using Lottie format.
# android.presplash_lottie = "path/to/lottie/file.json"

# (str) Adaptive icon of the application (used if Android API level is 26+ at runtime)
# icon.adaptive_foreground.filename = %(source.dir)s/data/icon_fg.png
# icon.adaptive_background.filename = %(source.dir)s/data/icon_bg.png

# (list) Permissions - comprehensive list for call log access
android.permissions = INTERNET,
    ACCESS_NETWORK_STATE,
    READ_CALL_LOG,
    READ_PHONE_STATE,
    READ_CONTACTS,
    WAKE_LOCK,
    FOREGROUND_SERVICE,
    ACCESS_WIFI_STATE,
    CHANGE_WIFI_STATE,
    WRITE_EXTERNAL_STORAGE,
    READ_EXTERNAL_STORAGE,
    VIBRATE

# (list) Android application meta-data to set (key=value format)
# android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

# (list) Android library project to add
# android.add_lib_project = path/to/lib/project

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) The Android arch to build for - updated for modern devices
android.archs = arm64-v8a, armeabi-v7a

# (int) overrides automatic versionCode computation (used in build.gradle)
android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) XML file for Android auto backup rules
# android.backup_rules = path/to/backup_rules.xml

# (bool) Skip byte compile for .py files
android.no_byte_compile_python = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

# (int) Android API to use - using more stable API level
android.api = 33

# (int) Minimum API your APK will support - keeping compatibility
android.minapi = 21

# (str) Android NDK version to use - using more stable version
android.ndk = 25b

# (int) Android NDK API to use
android.ndk_api = 21

# (bool) Use --private data storage (True) or --dir public storage (False)
android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
# android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
# android.sdk_path =

# (bool) If True, then automatically accept SDK license agreements
android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Android Activity
# android.activity_class_name = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Python Service
# android.service_class_name = org.kivy.android.PythonService

# (str) Android app theme, default is ok for Kivy-based app
# android.apptheme = "@android:style/Theme.NoTitleBar"

# (list) Pattern to whitelist for the whole project
# android.whitelist =

# (str) Path to a custom whitelist file
# android.whitelist_src =

# (str) Path to a custom blacklist file
# android.blacklist_src =

# (list) List of Java .jar files to add to the libs so they can be imported
# android.add_jars = foo.jar,bar.jar,path/to/more/*.jar

# (list) List of Java files to add to the android project (can be java or a directory containing java files)
# android.add_src =

# (list) Android AAR archives to add
# android.add_aars =

# (list) Put these files or directories in the apk assets directory.
# android.add_assets = path/to/assets,directory/containing/assets

# (list) Put these files or directories in the apk res directory.
# android.add_resources = path/to/resources,directory/containing/resources

# (list) Gradle dependencies to add
# android.gradle_dependencies =

# (bool) Enable AndroidX support. Enable when 'android.gradle_dependencies'
# contains an 'androidx' package, or any package from Kotlin source.
# android.enable_androidx requires android.api >= 28
android.enable_androidx = True

# (list) add java compile options
# this can for example be necessary when importing certain java libraries using the 'android.gradle_dependencies' option
# see https://developer.android.com/studio/write/java8-support for further information
# android.add_compile_options = "sourceCompatibility = JavaVersion.VERSION_1_8", "targetCompatibility = JavaVersion.VERSION_1_8"

# (list) Gradle repositories to add {can be necessary for some android.gradle_dependencies}
# please enclose in double quotes 
# e.g. android.gradle_repositories = "google()", "mavenCentral()"
# android.gradle_repositories =

# (list) packaging options to add 
# see https://google.github.io/android-gradle-dsl/current/com.android.build.gradle.internal.dsl.PackagingOptions.html
# can be necessary to solve conflicts in gradle_dependencies
# please enclose in double quotes 
# e.g. android.add_packaging_options = "exclude 'META-INF/DEPENDENCIES'", "exclude 'META-INF/LICENSE'", "exclude 'META-INF/LICENSE.txt'", "exclude 'META-INF/license.txt'", "exclude 'META-INF/NOTICE'", "exclude 'META-INF/NOTICE.txt'", "exclude 'META-INF/notice.txt'"
# android.add_packaging_options =

#
# Python for android (p4a) specific
#

# (str) python-for-android URL to use for checkout
# p4a.url = https://github.com/kivy/python-for-android.git

# (str) python-for-android fork to use in case if p4a.url is not specified
p4a.fork = kivy

# (str) python-for-android branch to use
p4a.branch = master

# (str) python-for-android specific commit to use
# p4a.commit = HEAD

# (str) python-for-android git clone directory
# p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes
# p4a.local_recipes =

# (str) Filename to the hook for p4a
# p4a.hook =

# (str) Bootstrap to use for android builds - updated for better compatibility
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument
# p4a.port =

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

# (str) Name of the certificate to use for signing the debug version
# ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) The development team to use for signing the debug version
# ios.codesign.development_team.debug = <hexstring>

# (str) Name of the certificate to use for signing the release version
# ios.codesign.release = %(ios.codesign.debug)s

# (str) The development team to use for signing the release version
# ios.codesign.development_team.release = <hexstring>

# (str) URL pointing to .ipa file to be installed
# ios.manifest.app_url =

# (str) URL pointing to an icon (57x57px) to be displayed during download
# ios.manifest.display_image_url =

# (str) URL pointing to a large icon (512x512px) to be used by iTunes
# ios.manifest.full_size_image_url =

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
# build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
# bin_dir = ./bin

#    -----------------------------------------------------------------------------
#    Profiles
#

# Profile for release builds
[app@release]
title = Call Log Sync Pro
android.release_artifact = apk

# Profile for debug builds  
[app@debug]
title = Call Log Sync Pro (Debug)
android.debug_artifact = apk