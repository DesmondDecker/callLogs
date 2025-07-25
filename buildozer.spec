name: Build Android APK

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-22.04
    
    steps:
    - name: Checkout repository
      uses: actions/checkout@v4
      
    - name: Setup Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
        
    - name: Setup Java JDK
      uses: actions/setup-java@v4
      with:
        distribution: 'temurin'
        java-version: '17'
        
    - name: Install system dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y \
          build-essential \
          git \
          python3-dev \
          libffi-dev \
          libssl-dev \
          libbz2-dev \
          libsqlite3-dev \
          libncurses5-dev \
          libncursesw5-dev \
          xz-utils \
          tk-dev \
          libxml2-dev \
          libxmlsec1-dev \
          liblzma-dev \
          unzip \
          wget \
          curl \
          zlib1g-dev \
          autoconf \
          libtool \
          pkg-config \
          cmake
          
    - name: Setup environment
      run: |
        echo "JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64" >> $GITHUB_ENV
        
    - name: Cache Buildozer global directory
      uses: actions/cache@v4
      with:
        path: .buildozer_global
        key: buildozer-global-${{ hashFiles('buildozer.spec') }}
        restore-keys: buildozer-global-
        
    - name: Cache Buildozer directory
      uses: actions/cache@v4
      with:
        path: .buildozer
        key: ${{ runner.os }}-buildozer-${{ hashFiles('buildozer.spec') }}
        restore-keys: ${{ runner.os }}-buildozer-
          
    - name: Install Python dependencies
      run: |
        python -m pip install --upgrade pip
        pip install buildozer==1.5.0 cython==0.29.36
        pip install -r requirements.txt
        
    - name: Create buildozer spec
      run: |
        cat > buildozer.spec << 'EOF'
        [app]
        title = Call Center Sync
        package.name = callcentersync
        package.domain = com.callcenter.sync
        source.dir = .
        source.include_exts = py,png,jpg,kv,atlas,txt,json
        version.regex = __version__ = ['"]([^'"]*)['"]
        version.filename = %(source.dir)s/main.py
        source.main = main.py
        requirements = python3,kivy==2.1.0,requests,pyjnius,android
        orientation = portrait
        services = 
        skip_dist = 1
        fullscreen = 0

        [android]
        android.api = 33
        android.minapi = 21
        android.ndk = 25b
        android.sdk = 33
        android.accept_sdk_license = True
        android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_CALL_LOG,READ_PHONE_STATE,READ_CONTACTS,WAKE_LOCK
        android.archs = arm64-v8a,armeabi-v7a
        android.gradle_repositories = google(), mavenCentral()
        p4a.bootstrap = sdl2
        p4a.branch = master

        [buildozer]
        log_level = 2
        warn_on_root = 1
        build_dir = ./.buildozer
        bin_dir = ./bin
        EOF
        
    - name: Initialize buildozer (first run to create directories)
      run: |
        echo "=== Initializing buildozer to create directory structure ==="
        buildozer android debug --verbose || echo "First run completed (expected to possibly fail)"
        
    - name: Install Android SDK components to buildozer location
      run: |
        # Define the buildozer SDK path
        BUILDOZER_SDK_PATH="$HOME/.buildozer/android/platform/android-sdk"
        
        echo "=== Installing Android SDK to buildozer location: $BUILDOZER_SDK_PATH ==="
        
        # Create SDK directory
        mkdir -p "$BUILDOZER_SDK_PATH"
        cd "$BUILDOZER_SDK_PATH"
        
        # Download command line tools if not present
        if [ ! -d "cmdline-tools" ]; then
          echo "Downloading Android command line tools..."
          wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
          unzip -q commandlinetools-linux-11076708_latest.zip
          rm commandlinetools-linux-11076708_latest.zip
          
          # Organize cmdline-tools properly
          mkdir -p cmdline-tools/latest
          mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true
        fi
        
        # Set up environment for SDK manager
        export ANDROID_SDK_ROOT="$BUILDOZER_SDK_PATH"
        export ANDROID_HOME="$BUILDOZER_SDK_PATH"
        export PATH="$PATH:$BUILDOZER_SDK_PATH/cmdline-tools/latest/bin"
        
        echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
        echo "PATH includes: $BUILDOZER_SDK_PATH/cmdline-tools/latest/bin"
        
        # Accept licenses
        echo "Accepting Android SDK licenses..."
        yes | sdkmanager --licenses >/dev/null 2>&1 || true
        
        # Install essential components
        echo "Installing Android SDK components..."
        sdkmanager --install \
          "build-tools;33.0.2" \
          "platform-tools" \
          "platforms;android-33" \
          "ndk;25.1.8937393" \
          --verbose
        
        # Verify aidl installation
        AIDL_PATH="$BUILDOZER_SDK_PATH/build-tools/33.0.2/aidl"
        if [ -f "$AIDL_PATH" ]; then
          chmod +x "$AIDL_PATH"
          echo "✅ aidl found and made executable at: $AIDL_PATH"
          ls -la "$AIDL_PATH"
          
          # Test aidl
          if "$AIDL_PATH" --help >/dev/null 2>&1; then
            echo "✅ aidl is working correctly"
          else
            echo "⚠️ aidl executable but may have issues"
          fi
        else
          echo "❌ aidl not found at expected location: $AIDL_PATH"
          
          # Debug: show what's in build-tools
          echo "Contents of build-tools directory:"
          ls -la "$BUILDOZER_SDK_PATH/build-tools/" 2>/dev/null || echo "build-tools directory not found"
          
          # Look for aidl anywhere
          echo "Searching for aidl in buildozer SDK:"
          find "$BUILDOZER_SDK_PATH" -name "aidl" -type f 2>/dev/null || echo "No aidl found"
          
          exit 1
        fi
        
    - name: Build APK
      run: |
        # Set environment for buildozer
        export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
        export ANDROID_SDK_ROOT="$HOME/.buildozer/android/platform/android-sdk"
        export ANDROID_HOME="$ANDROID_SDK_ROOT"
        export PATH="$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/build-tools/33.0.2"
        
        echo "=== Final build environment ==="
        echo "JAVA_HOME: $JAVA_HOME"
        echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
        echo "Java version:"
        java -version
        
        # Final aidl check
        AIDL_PATH="$ANDROID_SDK_ROOT/build-tools/33.0.2/aidl"
        if [ -f "$AIDL_PATH" ]; then
          echo "✅ Final aidl check passed: $AIDL_PATH"
        else
          echo "❌ Final aidl check failed"
          exit 1
        fi
        
        echo "=== Starting APK build ==="
        buildozer android debug --verbose
        
    - name: List build results
      run: |
        echo "=== Build Results ==="
        echo "Contents of bin directory:"
        ls -la bin/ 2>/dev/null || echo "No bin directory found"
        
        echo "Searching for APK files:"
        find . -name "*.apk" -type f -exec ls -la {} \; 2>/dev/null || echo "No APK files found"
        
    - name: Upload APK
      uses: actions/upload-artifact@v4
      if: success()
      with:
        name: call-center-sync-apk
        path: |
          bin/*.apk
          .buildozer/android/platform/build-**/outputs/apk/**/*.apk
        retention-days: 30
        if-no-files-found: warn
        
    - name: Upload build logs on failure
      uses: actions/upload-artifact@v4
      if: failure()
      with:
        name: build-logs-failure
        path: |
          .buildozer/android/platform/build-*/logs/
          .buildozer/android/platform/python-for-android/
          .buildozer/android/platform/build.log
        retention-days: 7
        if-no-files-found: ignore