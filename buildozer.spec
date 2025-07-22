[app]

# (str) Title of your application
title = Call Log Monitor

# (str) Package name
package.name = calllogmonitor

# (str) Package domain (needed for android/ios packaging)
package.domain = com.monitor.calllog

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,txt

# (str) Application versioning (method 1)
version = 2.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,kivy==2.1.0,requests,pyjnius,android,urllib3

# (str) Supported orientation (landscape, sensorLandscape, portrait, all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,INTERNET,WRITE_EXTERNAL_STORAGE,ACCESS_NETWORK_STATE

# (int) Target Android API, should be as high as possible.
android.api = 30

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 23b

# (str) Android SDK version to use
android.sdk = 30

# (bool) If True, then skip trying to update the Android sdk
android.skip_update = False

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (str) Android entry point, default is ok for Kivy-based app
android.entrypoint = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Android Activity
android.activity_class_name = org.kivy.android.PythonActivity

# (str) Full name including package path of the Java class that implements Python Service
android.service_class_name = org.kivy.android.PythonService

# (list) Pattern to whitelist for the whole project
android.whitelist =

# (str) Path to a custom whitelist file
android.whitelist_src =

# (str) Path to a custom blacklist file
android.blacklist_src =

# (list) List of Java .jar files to add to the libs so that pyjnius can access their classes. Don't add jars that you do not need, since extra jars can slow down the build process. Allows wildcards matching, for example: OUYA-ODK/libs/*.jar
android.add_jars = 

# (list) List of Java files to add to the android project (can be java or a directory containing the files)
android.add_src =

# (list) Android AAR archives to add
android.add_aars =

# (list) Gradle dependencies to add
android.gradle_dependencies =

# (list) add java compile options
android.add_compile_options =

# (list) Gradle repositories to add {can be necessary for some android.gradle_dependencies}
android.gradle_repositories =

# (str) python-for-android fork to use, defaults to upstream (kivy)
p4a.fork = kivy

# (str) python-for-android branch to use, defaults to master
p4a.branch = master

# (str) python-for-android specific commit to use, defaults to HEAD, must be within p4a.branch
p4a.commit = HEAD

# (str) python-for-android git clone directory (if empty, it will be automatically cloned from github)
p4a.source_dir =

# (str) The directory in which python-for-android should look for your own build recipes (if any)
p4a.local_recipes =

# (str) Filename to the hook for p4a
p4a.hook =

# (str) Bootstrap to use for android builds
p4a.bootstrap = sdl2

# (int) port number to specify an explicit --port= p4a argument (eg for bootstrap flask)
p4a.port =

# Control passing the --private-data-dir argument to p4a
p4a.private_data_dir = True

# Pass --use-setup-py or --ignore-setup-py to p4a
# p4a.setup_py = false

# (str) extra command line arguments to pass when invoking pythonforandroid.toolchain
p4a.extra_args =


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
bin_dir = ./bin