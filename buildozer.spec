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
source.exclude_dirs = tests,bin,.buildozer,venv,__pycache__,.git,.github

# (list) List of exclusions using pattern matching
source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 2.0.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.1.0,android,pyjnius,plyer,requests,urllib3,certifi,charset-normalizer,idna

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
# Supported formats are: #RRGGBB #AARRGGBB or one of the following names:
# red, blue, green, black, white, gray, cyan, magenta, yellow, lightgray,
# darkgray, grey, lightgrey, darkgrey, aqua, fuchsia, lime, maroon, navy,
# olive, purple, silver, teal.
android.presplash_color = #FFFFFF

# (string) Presplash animation using Lottie format.
# see https://lottiefiles.com/ for examples and https://airbnb.design/lottie/
# for general documentation.
# Lottie files can be created using various tools, like Adobe After Effects or Synfig.
# android.presplash_lottie = "path/to/lottie/file.json"

# (str) Adaptive icon of the application (used if Android API level is 26+ at runtime)
# icon.adaptive_foreground.filename = %(source.dir)s/data/icon_fg.png
# icon.adaptive_background.filename = %(source.dir)s/data/icon_bg.png

# (list) Permissions
# (See https://python-for-android.readthedocs.io/en/latest/buildoptions/#build-options-1 for all the supported syntaxes and properties)
android.permissions = android.permission.INTERNET,
    android.permission.ACCESS_NETWORK_STATE,
    android.permission.READ_CALL_LOG,
    android.permission.READ_PHONE_STATE,
    android.permission.READ_CONTACTS,
    android.permission.WAKE_LOCK,
    android.permission.FOREGROUND_SERVICE

# (list) Android application meta-data to set (key=value format)
android.meta_data = com.google.android.gms.version=@integer/google_play_services_version

# (list) Android library project to add (will be added in the
# project.properties automatically.)
# android.add_lib_project = path/to/lib/project

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
# In past, was `android.arch` as we weren't supporting builds for multiple archs at the same time.
android.archs = arm64-v8a, armeabi-v7a

# (int) overrides automatic versionCode computation (used in build.gradle)
# this is not the same as app version and should only be edited if you know what you're doing
# android.numeric_version = 1

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) XML file for Android auto backup rules
# android.backup_rules = path/to/backup_rules.xml

# (str) If you need to insert variables into your AndroidManifest.xml file,
# you can do so with the manifestPlaceholders property.
# This property takes a map of key-value pairs. (via a string)
# Usage example : android.manifest_placeholders = key:value, key2:value2, ...
# android.manifest_placeholders = com.google.android.gms.ads.APPLICATION_ID:ca-app-pub-1234567890123456~1234567890

# (bool) Skip byte compile for .py files
# android.no-byte-compile-python = False

# (str) The format used to package the app for release mode (aab or apk or aar).
android.release_artifact = apk

# (str) The format used to package the app for debug mode (apk or aar).
android.debug_artifact = apk

#
# Python for android (p4a) specific
#

# (str) python-for-android URL to use for checkout
# p4a.url = https://github.com/kivy/python-for-android.git

# (str) python-for-android fork to use in case if p4a.url is not specified, defaults to upstream (kivy)
# p4a.fork = kivy

# (str) python-for-android branch to use, defaults to master
p4a.branch = master

# (str) python-for-android specific commit to use, defaults to HEAD, must be within p4a.branch
# p4a.commit = HEAD

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
# p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes (if any)
# p4a.local_recipes =

# (str) Filename to the hook for p4a
# p4a.hook =

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
# p4a.port =

# Control passing the --private and --add-source to p4a
# --private the private directory will be passed to p4a
# --add-source pass the extra source dirs to p4a
# --depends pass the extra depends to p4a
# --port pass the port to p4a (if specified)
# --use-setup-py process setup.py files (used with flask/django bootstraps)
# --ignore-setup-py do not process setup.py (if you have a setup.py in your
#                     folder but do not want to use it, works with bootstraps
#                     that don't use setup.py)
# Here is a list of available options:
# https://python-for-android.readthedocs.io/en/latest/quickstart/#usage
# p4a.cmd_line = --private $BUILDOZER_BUILD_DIR --package $BUILDOZER_PROJECT_NAME --name "$BUILDOZER_PROJECT_TITLE" --version $BUILDOZER_VERSION --bootstrap $BUILDOZER_BOOTSTRAP --arch $BUILDOZER_ARCH --dist_name=$BUILDOZER_DIST_NAME --depends $BUILDOZER_REQUIREMENTS --permission $BUILDOZER_PERMISSIONS

#
# iOS specific
#

# (str) Path to a custom kivy-ios folder
# ios.kivy_ios_url = https://github.com/kivy/kivy-ios
# ios.kivy_ios_branch = master

# Alternately, specify the URL and branch of a git checkout:
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master

# (str) Name of the certificate to use for signing the debug version
# Get a list of available identities: ios-deploy -c ios
# ios.codesign.debug = "iPhone Developer: <lastname> <firstname> (<hexstring>)"

# (str) The development team to use for signing the debug version
# (str) Name of the certificate to use for signing the release version
# ios.codesign.release = %(ios.codesign.debug)s

# (str) The development team to use for signing the release version
# ios.codesign.development_team.release = <hexstring>

# (str) URL pointing to .ipa file to be installed
# This option should be defined along with `display-image-url` and `full-size-image-url` options.
# ios.manifest.app_url =

# (str) URL pointing to an icon (57x57px) to be displayed during download
# This option should be defined along with `app-url` and `full-size-image-url` options.
# ios.manifest.display_image_url =

# (str) URL pointing to a large icon (512x512px) to be used by iTunes
# This option should be defined along with `app-url` and `display-image-url` options.
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
#    List as sections
#
#    You can define all the "list" as [section:key].
#    Each line will be considered as a option to the list.
#    Let's take [app] / source.exclude_patterns.
#    Instead of doing:
#
# [app]
# source.exclude_patterns = license,data/audio/*.wav,data/images/original/*
#
#    This can be translated into:
#
# [app:source.exclude_patterns]
# license
# data/audio/*.wav
# data/images/original/*
#

#    -----------------------------------------------------------------------------
#    Profiles
#
#    You can extend section / key with a profile
#    For example, you want to deploy a demo version of your application without
#    HD content. You could first change the title to add "(demo)" in the name
#    and extend the excluded directories to remove the HD content.
#
# [app@demo]
# title = My Application (demo)
#
# [app:source.exclude_patterns@demo]
# images/hd/*
#
#    Then, invoke the command line with the "demo" profile:
#
# buildozer --profile demo android debug

# Profile for release builds
[app@release]
# Add any release-specific configurations here
android.release_artifact = apk

# Profile for debug builds
[app@debug]
# Add any debug-specific configurations here
android.debug_artifact = apk