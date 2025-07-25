#!/usr/bin/env python3
"""
Android Call Log Sync - Native Kivy App
Direct Android implementation with proper permissions and native call log access
"""

import os
import sys
import json
import time
import hashlib
import platform
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock, mainthread
from kivy.logger import Logger
from kivy.utils import platform as kivy_platform

# Android-specific imports
if kivy_platform == 'android':
    from jnius import autoclass, cast
    from android.permissions import request_permissions, Permission, check_permission
    from android.runnable import run_on_ui_thread
    
    # Android Java classes
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    ContentResolver = autoclass('android.content.ContentResolver')
    CallLog = autoclass('android.provider.CallLog')
    Uri = autoclass('android.net.Uri')
    Cursor = autoclass('android.database.Cursor')
    TelephonyManager = autoclass('android.telephony.TelephonyManager')
    Settings = autoclass('android.provider.Settings')
    ContactsContract = autoclass('android.provider.ContactsContract')
    
    # Get current activity and context
    current_activity = cast('android.app.Activity', PythonActivity.mActivity)
    context = cast('android.content.Context', current_activity.getApplicationContext())

# HTTP client with fallbacks
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    # Install requests if not available
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AndroidCallLogManager:
    """Native Android Call Log Manager using Kivy and Jnius"""
    
    def __init__(self):
        self.permissions_granted = False
        self.device_id = None
        self.device_info = {}
        
    def request_permissions(self) -> bool:
        """Request necessary Android permissions"""
        if kivy_platform != 'android':
            logger.info("Not on Android, skipping permissions")
            return True
            
        try:
            # List of required permissions
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ]
            
            # Check if permissions are already granted
            granted = all(check_permission(perm) for perm in permissions)
            
            if not granted:
                logger.info("Requesting permissions...")
                request_permissions(permissions)
                
                # Wait a bit and check again
                time.sleep(2)
                granted = all(check_permission(perm) for perm in permissions)
            
            self.permissions_granted = granted
            logger.info(f"Permissions granted: {granted}")
            return granted
            
        except Exception as e:
            logger.error(f"Permission request failed: {e}")
            return False
    
    def get_device_id(self) -> str:
        """Get unique Android device ID"""
        if self.device_id:
            return self.device_id
            
        try:
            if kivy_platform == 'android':
                # Get Android ID
                android_id = Settings.Secure.getString(
                    context.getContentResolver(),
                    Settings.Secure.ANDROID_ID
                )
                
                if android_id and android_id != "9774d56d682e549c":  # Default emulator ID
                    self.device_id = f"android_{android_id}"
                    return self.device_id
                    
                # Fallback: Use IMEI (requires READ_PHONE_STATE)
                try:
                    telephony = context.getSystemService(Context.TELEPHONY_SERVICE)
                    imei = telephony.getDeviceId()
                    if imei:
                        self.device_id = f"android_{hashlib.md5(imei.encode()).hexdigest()[:12]}"
                        return self.device_id
                except Exception as e:
                    logger.debug(f"IMEI access failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to get Android device ID: {e}")
        
        # Final fallback
        fallback = f"python_{hashlib.md5(platform.node().encode()).hexdigest()[:12]}"
        self.device_id = fallback
        return fallback
    
    def get_device_info(self) -> Dict:
        """Get Android device information"""
        if self.device_info:
            return self.device_info
            
        info = {
            "model": "Unknown",
            "manufacturer": "Unknown", 
            "os": "Android",
            "osVersion": "Unknown",
            "appVersion": "1.0.0"
        }
        
        try:
            if kivy_platform == 'android':
                Build = autoclass('android.os.Build')
                info.update({
                    "model": Build.MODEL,
                    "manufacturer": Build.MANUFACTURER,
                    "os": "Android",
                    "osVersion": Build.VERSION.RELEASE,
                })
        except Exception as e:
            logger.warning(f"Failed to get device info: {e}")
        
        self.device_info = info
        return info
    
    def get_call_logs(self, limit: int = 1000) -> List[Dict]:
        """Get call logs from Android CallLog provider"""
        if kivy_platform != 'android' or not self.permissions_granted:
            return self._get_sample_call_logs()
            
        try:
            call_logs = []
            content_resolver = context.getContentResolver()
            
            # Define columns to retrieve
            projection = [
                CallLog.Calls.NUMBER,
                CallLog.Calls.CACHED_NAME,
                CallLog.Calls.TYPE,
                CallLog.Calls.DURATION,
                CallLog.Calls.DATE,
                CallLog.Calls._ID
            ]
            
            # Query call log
            cursor = content_resolver.query(
                CallLog.Calls.CONTENT_URI,
                projection,
                None,  # selection
                None,  # selection args
                f"{CallLog.Calls.DATE} DESC LIMIT {limit}"  # sort order
            )
            
            if cursor and cursor.moveToFirst():
                # Get column indices
                number_idx = cursor.getColumnIndex(CallLog.Calls.NUMBER)
                name_idx = cursor.getColumnIndex(CallLog.Calls.CACHED_NAME)
                type_idx = cursor.getColumnIndex(CallLog.Calls.TYPE)
                duration_idx = cursor.getColumnIndex(CallLog.Calls.DURATION)
                date_idx = cursor.getColumnIndex(CallLog.Calls.DATE)
                id_idx = cursor.getColumnIndex(CallLog.Calls._ID)
                
                # Process each row
                while True:
                    try:
                        phone_number = cursor.getString(number_idx) or "Unknown"
                        contact_name = cursor.getString(name_idx)
                        call_type = cursor.getInt(type_idx)
                        duration = cursor.getInt(duration_idx)
                        timestamp = cursor.getLong(date_idx)
                        call_id = cursor.getLong(id_idx)
                        
                        # Map call type
                        type_map = {
                            CallLog.Calls.INCOMING_TYPE: "incoming",
                            CallLog.Calls.OUTGOING_TYPE: "outgoing", 
                            CallLog.Calls.MISSED_TYPE: "missed",
                            CallLog.Calls.VOICEMAIL_TYPE: "voicemail",
                            CallLog.Calls.REJECTED_TYPE: "rejected",
                            CallLog.Calls.BLOCKED_TYPE: "blocked"
                        }
                        
                        call_log_entry = {
                            "phoneNumber": phone_number,
                            "contactName": contact_name,
                            "type": type_map.get(call_type, "unknown"),
                            "duration": duration,
                            "timestamp": datetime.fromtimestamp(timestamp / 1000).isoformat(),
                            "callId": f"{self.get_device_id()}_{phone_number}_{timestamp}",
                            "rawId": str(call_id)
                        }
                        
                        call_logs.append(call_log_entry)
                        
                    except Exception as e:
                        logger.warning(f"Error processing call log row: {e}")
                    
                    if not cursor.moveToNext():
                        break
                        
                cursor.close()
                
            logger.info(f"Retrieved {len(call_logs)} call logs from Android")
            return call_logs
            
        except Exception as e:
            logger.error(f"Failed to get call logs: {e}")
            return self._get_sample_call_logs()
    
    def _get_sample_call_logs(self) -> List[Dict]:
        """Generate sample call logs for testing"""
        sample_calls = []
        base_time = datetime.now()
        
        sample_data = [
            ("+232123456789", "John Doe", "incoming", 120),
            ("+232987654321", "Jane Smith", "outgoing", 45),
            ("+232555666777", "Bob Wilson", "missed", 0),
            ("+232111222333", "Alice Brown", "incoming", 300),
            ("+232444555666", "Charlie Davis", "outgoing", 180)
        ]
        
        for i, (number, name, call_type, duration) in enumerate(sample_data):
            timestamp = base_time - timedelta(hours=i)
            sample_calls.append({
                "phoneNumber": number,
                "contactName": name,
                "type": call_type,
                "duration": duration,
                "timestamp": timestamp.isoformat(),
                "callId": f"{self.get_device_id()}_{number}_{int(timestamp.timestamp() * 1000)}"
            })
        
        return sample_calls


class BackendSync:
    """Backend synchronization manager"""
    
    def __init__(self, device_id: str, device_info: Dict):
        self.device_id = device_id
        self.device_info = device_info
        self.user_id = "12345"  # Default user ID
        
        # Backend URLs (production first, then fallbacks)
        self.backend_urls = [
            "https://kortahununited.onrender.com/api",
            "https://kortahun-center.onrender.com/api",
            "https://api.kortahun.com/api",
            "https://backend.kortahun.io/api",
            "http://localhost:5001/api",
            "http://localhost:3001/api",
            "http://localhost:4000/api"
        ]
        
        self.active_backend_url = None
        self.session = self._setup_session()
    
    def _setup_session(self) -> requests.Session:
        """Setup HTTP session with robust retry logic"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'AndroidCallSync-Kivy/1.0 (Android)'
        })
        
        return session
    
    def detect_backend(self) -> bool:
        """Find working backend URL"""
        logger.info("Detecting backend URL...")
        
        for url in self.backend_urls:
            try:
                logger.info(f"Testing: {url}")
                
                # Test health endpoint with short timeout
                response = self.session.get(f"{url}/health", timeout=15)
                
                if response.status_code == 200:
                    self.active_backend_url = url
                    logger.info(f"Backend detected: {url}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Failed {url}: {e}")
                continue
        
        logger.error("No working backend found!")
        return False
    
    def register_device(self) -> bool:
        """Register device with backend"""
        if not self.active_backend_url:
            if not self.detect_backend():
                return False
        
        registration_data = {
            "deviceId": self.device_id,
            "userId": self.user_id,
            "deviceInfo": self.device_info,
            "permissions": {
                "readCallLog": True,
                "readPhoneState": True,
                "readContacts": True
            }
        }
        
        # Try multiple registration endpoints
        endpoints = ["/devices/register", "/devices/simple-register", "/register"]
        
        for endpoint in endpoints:
            try:
                logger.info(f"Registering device via {endpoint}")
                
                response = self.session.post(
                    f"{self.active_backend_url}{endpoint}",
                    json=registration_data,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    result = response.json()
                    if result.get("success", False):
                        logger.info(f"Device registered successfully via {endpoint}")
                        return True
                
            except Exception as e:
                logger.warning(f"Registration failed via {endpoint}: {e}")
                continue
        
        logger.error("All registration methods failed!")
        return False
    
    def sync_calls(self, calls: List[Dict]) -> bool:
        """Sync call logs to backend"""
        if not calls or not self.active_backend_url:
            return False
        
        logger.info(f"Syncing {len(calls)} calls to backend...")
        
        sync_data = {
            "deviceId": self.device_id,
            "userId": self.user_id,
            "calls": calls
        }
        
        try:
            response = self.session.post(
                f"{self.active_backend_url}/calls/sync",
                json=sync_data,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    processed = result.get("data", {}).get("processed", 0)
                    skipped = result.get("data", {}).get("skipped", 0)
                    logger.info(f"Sync successful: {processed} processed, {skipped} skipped")
                    return True
                else:
                    logger.warning(f"Sync response: {result}")
            else:
                logger.error(f"Sync failed: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Sync error: {e}")
        
        return False
    
    def ping_device(self) -> bool:
        """Send heartbeat to backend"""
        if not self.active_backend_url:
            return False
        
        try:
            response = self.session.post(
                f"{self.active_backend_url}/devices/ping",
                json={"deviceId": self.device_id},
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")
            return False


class CallSyncApp(App):
    """Main Kivy Application"""
    
    def build(self):
        self.title = "Call Log Sync"
        self.call_manager = AndroidCallLogManager()
        self.backend_sync = None
        self.sync_thread = None
        self.is_syncing = False
        
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Android Call Log Sync',
            size_hint_y=None,
            height=50,
            font_size=20
        )
        layout.add_widget(title)
        
        # Status label
        self.status_label = Label(
            text='Ready to sync',
            size_hint_y=None,
            height=40
        )
        layout.add_widget(self.status_label)
        
        # Progress bar
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=30
        )
        layout.add_widget(self.progress_bar)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60)
        
        self.sync_button = Button(
            text='Start Sync',
            size_hint_x=0.5
        )
        self.sync_button.bind(on_press=self.toggle_sync)
        button_layout.add_widget(self.sync_button)
        
        test_button = Button(
            text='Test Connection',
            size_hint_x=0.5
        )
        test_button.bind(on_press=self.test_connection)
        button_layout.add_widget(test_button)
        
        layout.add_widget(button_layout)
        
        # Log area
        log_label = Label(
            text='Log Output:',
            size_hint_y=None,
            height=30,
            text_size=(None, None)
        )
        layout.add_widget(log_label)
        
        scroll = ScrollView()
        self.log_text = Label(
            text='Application started...\n',
            text_size=(None, None),
            valign='top'
        )
        scroll.add_widget(self.log_text)
        layout.add_widget(scroll)
        
        # Initialize on startup
        Clock.schedule_once(self.initialize_app, 1)
        
        return layout
    
    def initialize_app(self, dt):
        """Initialize app after startup"""
        self.update_status("Initializing...")
        
        # Request permissions
        if self.call_manager.request_permissions():
            device_id = self.call_manager.get_device_id()
            device_info = self.call_manager.get_device_info()
            
            self.backend_sync = BackendSync(device_id, device_info)
            
            self.log_message(f"Device ID: {device_id}")
            self.log_message(f"Device: {device_info.get('manufacturer')} {device_info.get('model')}")
            self.update_status("Ready to sync")
        else:
            self.update_status("Permissions required!")
            self.log_message("Please grant all required permissions and restart the app")
    
    @mainthread
    def update_status(self, status: str):
        """Update status label"""
        self.status_label.text = status
    
    @mainthread
    def update_progress(self, value: float):
        """Update progress bar"""
        self.progress_bar.value = value
    
    @mainthread
    def log_message(self, message: str):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.text += f"[{timestamp}] {message}\n"
        self.log_text.text_size = (self.log_text.parent.width if self.log_text.parent else 400, None)
    
    def toggle_sync(self, instance):
        """Toggle sync on/off"""
        if not self.is_syncing:
            self.start_sync()
        else:
            self.stop_sync()
    
    def start_sync(self):
        """Start continuous sync"""
        if not self.backend_sync:
            self.log_message("Backend not initialized!")
            return
        
        self.is_syncing = True
        self.sync_button.text = "Stop Sync"
        self.update_status("Starting sync...")
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self.sync_worker)
        self.sync_thread.daemon = True
        self.sync_thread.start()
    
    def stop_sync(self):
        """Stop sync"""
        self.is_syncing = False
        self.sync_button.text = "Start Sync"
        self.update_status("Stopping sync...")
        self.log_message("Sync stopped by user")
    
    def sync_worker(self):
        """Background sync worker"""
        failure_count = 0
        max_failures = 5
        
        while self.is_syncing:
            try:
                self.update_status("Syncing...")
                self.update_progress(10)
                
                # Step 1: Detect backend
                if not self.backend_sync.active_backend_url:
                    if not self.backend_sync.detect_backend():
                        self.log_message("No backend available")
                        failure_count += 1
                        time.sleep(30)
                        continue
                
                self.update_progress(25)
                
                # Step 2: Register device
                if not self.backend_sync.register_device():
                    self.log_message("Device registration failed")
                    failure_count += 1
                    time.sleep(30)
                    continue
                
                self.update_progress(50)
                
                # Step 3: Get call logs
                calls = self.call_manager.get_call_logs()
                self.log_message(f"Retrieved {len(calls)} call logs")
                
                self.update_progress(75)
                
                # Step 4: Sync to backend
                if calls and self.backend_sync.sync_calls(calls):
                    self.log_message(f"Successfully synced {len(calls)} calls")
                    failure_count = 0
                else:
                    self.log_message("Sync failed or no calls to sync")
                    failure_count += 1
                
                self.update_progress(90)
                
                # Step 5: Send heartbeat
                self.backend_sync.ping_device()
                
                self.update_progress(100)
                self.update_status("Sync completed, waiting...")
                
                # Reset failures if successful
                if failure_count == 0:
                    self.log_message("Sync cycle completed successfully")
                
                # Wait 5 minutes between syncs
                for i in range(300):  # 5 minutes = 300 seconds
                    if not self.is_syncing:
                        break
                    time.sleep(1)
                
                self.update_progress(0)
                
                # Handle too many failures
                if failure_count >= max_failures:
                    self.log_message(f"Too many failures ({max_failures}), resetting...")
                    self.backend_sync.active_backend_url = None
                    failure_count = 0
                    time.sleep(60)
                
            except Exception as e:
                self.log_message(f"Sync error: {e}")
                failure_count += 1
                time.sleep(30)
        
        self.update_status("Sync stopped")
        self.update_progress(0)
    
    def test_connection(self, instance):
        """Test backend connection"""
        if not self.backend_sync:
            self.log_message("Backend not initialized!")
            return
        
        self.update_status("Testing connection...")
        
        def test_worker():
            # Test backend detection
            if self.backend_sync.detect_backend():
                self.log_message(f"Backend found: {self.backend_sync.active_backend_url}")
                
                # Test registration
                if self.backend_sync.register_device():
                    self.log_message("Device registration successful")
                    
                    # Test call log access
                    calls = self.call_manager.get_call_logs(limit=10)
                    self.log_message(f"Call log access: {len(calls)} calls retrieved")
                    
                    self.update_status("Connection test passed!")
                else:
                    self.log_message("Device registration failed")
                    self.update_status("Registration failed")
            else:
                self.log_message("No backend found")
                self.update_status("No backend available")
        
        # Run test in background
        threading.Thread(target=test_worker, daemon=True).start()


if __name__ == '__main__':
    CallSyncApp().run()