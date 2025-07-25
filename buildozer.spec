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
        
    - name: Setup Android SDK with comprehensive fallbacks
      run: |
        # Define paths
        BUILDOZER_SDK_PATH="$HOME/.buildozer/android/platform/android-sdk"
        
        echo "=== Setting up Android SDK at: $BUILDOZER_SDK_PATH ==="
        
        # Create SDK directory
        mkdir -p "$BUILDOZER_SDK_PATH"
        cd "$BUILDOZER_SDK_PATH"
        
        # Download command line tools with retries
        if [ ! -d "cmdline-tools" ]; then
          echo "Downloading Android command line tools..."
          
          # Try multiple download sources/versions
          CMDTOOLS_URLS=(
            "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
            "https://dl.google.com/android/repository/commandlinetools-linux-10406996_latest.zip"
            "https://dl.google.com/android/repository/commandlinetools-linux-9477386_latest.zip"
          )
          
          for url in "${CMDTOOLS_URLS[@]}"; do
            echo "Trying download from: $url"
            if wget -q "$url" -O cmdtools.zip; then
              if unzip -q cmdtools.zip; then
                rm cmdtools.zip
                echo "✅ Successfully downloaded and extracted command line tools"
                break
              else
                echo "❌ Failed to extract, trying next URL"
                rm -f cmdtools.zip
              fi
            else
              echo "❌ Failed to download, trying next URL"
            fi
          done
          
          # Verify we have cmdline-tools
          if [ ! -d "cmdline-tools" ]; then
            echo "❌ Failed to download command line tools from all sources"
            exit 1
          fi
          
          # Organize cmdline-tools properly
          mkdir -p cmdline-tools/latest
          mv cmdline-tools/* cmdline-tools/latest/ 2>/dev/null || true
        fi
        
        # Set environment
        export ANDROID_SDK_ROOT="$BUILDOZER_SDK_PATH"
        export ANDROID_HOME="$BUILDOZER_SDK_PATH"
        export PATH="$PATH:$BUILDOZER_SDK_PATH/cmdline-tools/latest/bin"
        
        echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
        echo "Verifying sdkmanager..."
        which sdkmanager || { echo "❌ sdkmanager not found"; exit 1; }
        
        # Accept licenses with retries
        echo "Accepting Android SDK licenses..."
        for i in {1..3}; do
          if yes | timeout 60 sdkmanager --licenses --sdk_root="$ANDROID_SDK_ROOT" >/dev/null 2>&1; then
            echo "✅ Licenses accepted"
            break
          else
            echo "⚠️ License acceptance attempt $i failed, retrying..."
            sleep 2
          fi
        done
        
        # Install components with comprehensive fallback strategy
        echo "Installing Android SDK components..."
        
        # Define component lists in order of preference
        BUILD_TOOLS_VERSIONS=("33.0.2" "33.0.1" "33.0.0" "32.0.0" "31.0.0")
        PLATFORM_VERSIONS=("android-33" "android-32" "android-31")
        NDK_VERSIONS=("25.1.8937393" "25.0.8775105" "24.0.8215888")
        
        # Install platform-tools first (most reliable)
        echo "Installing platform-tools..."
        sdkmanager --install "platform-tools" --sdk_root="$ANDROID_SDK_ROOT" --verbose
        
        # Try build-tools versions until one works
        BUILD_TOOLS_SUCCESS=""
        for version in "${BUILD_TOOLS_VERSIONS[@]}"; do
          echo "Attempting to install build-tools;$version..."
          if sdkmanager --install "build-tools;$version" --sdk_root="$ANDROID_SDK_ROOT" --verbose; then
            # Verify aidl exists
            if [ -f "$ANDROID_SDK_ROOT/build-tools/$version/aidl" ]; then
              chmod +x "$ANDROID_SDK_ROOT/build-tools/$version/aidl"
              if "$ANDROID_SDK_ROOT/build-tools/$version/aidl" --help >/dev/null 2>&1; then
                echo "✅ Successfully installed working build-tools;$version"
                BUILD_TOOLS_SUCCESS="$version"
                echo "BUILD_TOOLS_VERSION=$version" >> $GITHUB_ENV
                break
              else
                echo "⚠️ build-tools;$version installed but aidl not working"
              fi
            else
              echo "⚠️ build-tools;$version installed but aidl not found"
            fi
          else
            echo "❌ Failed to install build-tools;$version"
          fi
        done
        
        if [ -z "$BUILD_TOOLS_SUCCESS" ]; then
          echo "❌ Failed to install any working build-tools version"
          exit 1
        fi
        
        # Install platform
        PLATFORM_SUCCESS=""
        for platform in "${PLATFORM_VERSIONS[@]}"; do
          echo "Attempting to install platforms;$platform..."
          if sdkmanager --install "platforms;$platform" --sdk_root="$ANDROID_SDK_ROOT" --verbose; then
            echo "✅ Successfully installed $platform"
            PLATFORM_SUCCESS="$platform"
            break
          fi
        done
        
        # Install NDK (optional, continue if fails)
        for ndk in "${NDK_VERSIONS[@]}"; do
          echo "Attempting to install ndk;$ndk..."
          if sdkmanager --install "ndk;$ndk" --sdk_root="$ANDROID_SDK_ROOT" --verbose; then
            echo "✅ Successfully installed ndk;$ndk"
            break
          else
            echo "⚠️ Failed to install ndk;$ndk, trying next..."
          fi
        done
        
        # Final verification
        echo "=== Installation Summary ==="
        echo "Build-tools version: $BUILD_TOOLS_SUCCESS"
        echo "Platform: $PLATFORM_SUCCESS"
        echo "SDK contents:"
        ls -la "$ANDROID_SDK_ROOT/"
        echo "Build-tools contents:"
        ls -la "$ANDROID_SDK_ROOT/build-tools/"
        echo "Specific build-tools version contents:"
        ls -la "$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_SUCCESS/"
        
        # Test final aidl
        AIDL_PATH="$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_SUCCESS/aidl"
        echo "Testing aidl at: $AIDL_PATH"
        if [ -f "$AIDL_PATH" ] && "$AIDL_PATH" --help >/dev/null 2>&1; then
          echo "✅ Final aidl verification successful"
        else
          echo "❌ Final aidl verification failed"
          exit 1
        fi
        
    - name: Build APK
      run: |
        # Set environment
        export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
        export ANDROID_SDK_ROOT="$HOME/.buildozer/android/platform/android-sdk"
        export ANDROID_HOME="$ANDROID_SDK_ROOT"
        
        # Use the build-tools version that was successfully installed
        BUILD_TOOLS_VER=${BUILD_TOOLS_VERSION:-33.0.2}
        export PATH="$PATH:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools:$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_VER"
        
        echo "=== Final build environment ==="
        echo "JAVA_HOME: $JAVA_HOME"
        echo "ANDROID_SDK_ROOT: $ANDROID_SDK_ROOT"
        echo "BUILD_TOOLS_VERSION: $BUILD_TOOLS_VER"
        echo "Java version:"
        java -version
        
        # Final environment check
        AIDL_PATH="$ANDROID_SDK_ROOT/build-tools/$BUILD_TOOLS_VER/aidl"
        if [ -f "$AIDL_PATH" ]; then
          echo "✅ Build environment ready - aidl found at: $AIDL_PATH"
        else
          echo "❌ Build environment check failed - aidl not found"
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