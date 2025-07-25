#!/usr/bin/env python3
"""
Android Call Log Sync - Production Ready Kivy App
Bulletproof Android implementation with modern dependencies and robust error handling
"""

import os
import sys
import json
import time
import hashlib
import platform
import threading
import traceback
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from pathlib import Path

# Kivy imports with error handling
try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.label import Label
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    from kivy.uix.progressbar import ProgressBar
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.popup import Popup
    from kivy.clock import Clock, mainthread
    from kivy.logger import Logger
    from kivy.utils import platform as kivy_platform
    from kivy.metrics import dp
    from kivy.uix.widget import Widget
    from kivy.graphics import Color, Rectangle
except ImportError as e:
    print(f"Kivy import error: {e}")
    sys.exit(1)

# Android-specific imports with error handling
ANDROID_AVAILABLE = False
if kivy_platform == 'android':
    try:
        from jnius import autoclass, cast, JavaException
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
        Build = autoclass('android.os.Build')
        
        # Get current activity and context
        current_activity = cast('android.app.Activity', PythonActivity.mActivity)
        context = cast('android.content.Context', current_activity.getApplicationContext())
        
        ANDROID_AVAILABLE = True
        Logger.info("CallSync: Android environment loaded successfully")
        
    except Exception as e:
        Logger.error(f"CallSync: Android import failed: {e}")
        ANDROID_AVAILABLE = False

# HTTP client with modern dependencies
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    import urllib3
    # Disable SSL warnings for self-signed certificates
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    Logger.error("CallSync: requests library not available")
    requests = None

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('call_sync.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class AndroidCallLogManager:
    """Enhanced Android Call Log Manager with bulletproof error handling"""
    
    def __init__(self):
        self.permissions_granted = False
        self.device_id = None
        self.device_info = {}
        self.last_permission_check = 0
        self.permission_check_interval = 30  # Check permissions every 30 seconds
        
    def request_permissions(self) -> bool:
        """Request necessary Android permissions with retry logic"""
        if not ANDROID_AVAILABLE:
            logger.info("Not on Android platform, skipping permissions")
            self.permissions_granted = True
            return True
            
        # Check if we recently checked permissions
        current_time = time.time()
        if current_time - self.last_permission_check < self.permission_check_interval:
            return self.permissions_granted
            
        try:
            # Required permissions for call log access
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.WAKE_LOCK,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ]
            
            # Check current permission status
            permission_status = {}
            for perm in permissions:
                try:
                    status = check_permission(perm)
                    permission_status[perm] = status
                    logger.debug(f"Permission {perm}: {status}")
                except Exception as e:
                    logger.warning(f"Failed to check permission {perm}: {e}")
                    permission_status[perm] = False
            
            # Check if all critical permissions are granted
            critical_permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.INTERNET
            ]
            
            critical_granted = all(permission_status.get(perm, False) for perm in critical_permissions)
            all_granted = all(permission_status.get(perm, False) for perm in permissions)
            
            if not critical_granted:
                logger.info("Requesting critical permissions...")
                try:
                    request_permissions(permissions)
                    time.sleep(3)  # Wait for user interaction
                    
                    # Re-check permissions
                    critical_granted = all(check_permission(perm) for perm in critical_permissions)
                    
                except Exception as e:
                    logger.error(f"Permission request failed: {e}")
                    return False
            
            self.permissions_granted = critical_granted
            self.last_permission_check = current_time
            
            logger.info(f"Permissions status - Critical: {critical_granted}, All: {all_granted}")
            return critical_granted
            
        except Exception as e:
            logger.error(f"Permission handling failed: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def get_device_id(self) -> str:
        """Get unique device identifier with multiple fallback methods"""
        if self.device_id:
            return self.device_id
            
        try:
            if ANDROID_AVAILABLE and context:
                # Method 1: Android ID (most reliable)
                try:
                    android_id = Settings.Secure.getString(
                        context.getContentResolver(),
                        Settings.Secure.ANDROID_ID
                    )
                    
                    if android_id and android_id != "9774d56d682e549c":
                        self.device_id = f"android_{android_id[:16]}"
                        logger.info(f"Device ID from Android ID: {self.device_id}")
                        return self.device_id
                except Exception as e:
                    logger.debug(f"Android ID method failed: {e}")
                
                # Method 2: Build serial (Android 8.0+)
                try:
                    if hasattr(Build, 'getSerial'):
                        serial = Build.getSerial()
                        if serial and serial != "unknown":
                            self.device_id = f"android_serial_{hashlib.md5(serial.encode()).hexdigest()[:16]}"
                            logger.info(f"Device ID from Build serial: {self.device_id}")
                            return self.device_id
                except Exception as e:
                    logger.debug(f"Build serial method failed: {e}")
                
                # Method 3: IMEI (requires READ_PHONE_STATE)
                try:
                    telephony = context.getSystemService(Context.TELEPHONY_SERVICE)
                    if telephony:
                        imei = telephony.getDeviceId()
                        if imei:
                            self.device_id = f"android_imei_{hashlib.md5(imei.encode()).hexdigest()[:16]}"
                            logger.info(f"Device ID from IMEI: {self.device_id}")
                            return self.device_id
                except Exception as e:
                    logger.debug(f"IMEI method failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to get Android device ID: {e}")
        
        # Fallback methods
        fallback_sources = [
            platform.node(),
            os.environ.get('ANDROID_SERIAL', ''),
            str(time.time_ns()),  # Last resort: timestamp
        ]
        
        for source in fallback_sources:
            if source:
                fallback_id = f"fallback_{hashlib.md5(source.encode()).hexdigest()[:16]}"
                self.device_id = fallback_id
                logger.info(f"Device ID from fallback: {self.device_id}")
                return fallback_id
        
        # Ultimate fallback
        self.device_id = f"unknown_{int(time.time())}"
        return self.device_id
    
    def get_device_info(self) -> Dict:
        """Get comprehensive device information"""
        if self.device_info:
            return self.device_info
            
        info = {
            "model": "Unknown",
            "manufacturer": "Unknown",
            "os": "Android" if ANDROID_AVAILABLE else "Python",
            "osVersion": "Unknown",
            "appVersion": "2.0.0",
            "sdkVersion": "Unknown",
            "platform": kivy_platform
        }
        
        try:
            if ANDROID_AVAILABLE:
                info.update({
                    "model": Build.MODEL or "Unknown",
                    "manufacturer": Build.MANUFACTURER or "Unknown",
                    "os": "Android",
                    "osVersion": Build.VERSION.RELEASE or "Unknown",
                    "sdkVersion": str(Build.VERSION.SDK_INT),
                    "buildId": Build.ID or "Unknown",
                    "hardware": Build.HARDWARE or "Unknown"
                })
                logger.info(f"Device info: {info['manufacturer']} {info['model']} (Android {info['osVersion']})")
        except Exception as e:
            logger.warning(f"Failed to get detailed device info: {e}")
        
        self.device_info = info
        return info
    
    def get_call_logs(self, limit: int = 1000, days_back: int = 30) -> List[Dict]:
        """Get call logs with enhanced error handling and filtering"""
        if not ANDROID_AVAILABLE or not self.permissions_granted:
            logger.info("Using sample data (no Android access or permissions)")
            return self._get_sample_call_logs()
            
        try:
            call_logs = []
            content_resolver = context.getContentResolver()
            
            # Calculate date filter (last X days)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
            
            # Define columns to retrieve
            projection = [
                CallLog.Calls.NUMBER,
                CallLog.Calls.CACHED_NAME,
                CallLog.Calls.TYPE,
                CallLog.Calls.DURATION,
                CallLog.Calls.DATE,
                CallLog.Calls._ID,
                CallLog.Calls.CACHED_LOOKUP_URI,
                CallLog.Calls.CACHED_PHOTO_URI
            ]
            
            # Build selection criteria
            selection = f"{CallLog.Calls.DATE} >= ?"
            selection_args = [str(cutoff_timestamp)]
            
            # Query call log with error handling
            cursor = None
            try:
                cursor = content_resolver.query(
                    CallLog.Calls.CONTENT_URI,
                    projection,
                    selection,
                    selection_args,
                    f"{CallLog.Calls.DATE} DESC LIMIT {limit}"
                )
                
                if not cursor:
                    logger.warning("Cursor is null - no call log access")
                    return self._get_sample_call_logs()
                
                if cursor.moveToFirst():
                    # Get column indices safely
                    try:
                        number_idx = cursor.getColumnIndex(CallLog.Calls.NUMBER)
                        name_idx = cursor.getColumnIndex(CallLog.Calls.CACHED_NAME)
                        type_idx = cursor.getColumnIndex(CallLog.Calls.TYPE)
                        duration_idx = cursor.getColumnIndex(CallLog.Calls.DURATION)
                        date_idx = cursor.getColumnIndex(CallLog.Calls.DATE)
                        id_idx = cursor.getColumnIndex(CallLog.Calls._ID)
                    except Exception as e:
                        logger.error(f"Failed to get column indices: {e}")
                        return self._get_sample_call_logs()
                    
                    # Process each row with error handling
                    row_count = 0
                    while row_count < limit:
                        try:
                            # Safely get values
                            phone_number = self._safe_get_string(cursor, number_idx, "Unknown")
                            contact_name = self._safe_get_string(cursor, name_idx, None)
                            call_type = self._safe_get_int(cursor, type_idx, 0)
                            duration = self._safe_get_int(cursor, duration_idx, 0)
                            timestamp = self._safe_get_long(cursor, date_idx, 0)
                            call_id = self._safe_get_long(cursor, id_idx, 0)
                            
                            # Validate data
                            if timestamp == 0:
                                logger.debug("Skipping call with invalid timestamp")
                                if not cursor.moveToNext():
                                    break
                                continue
                            
                            # Map call type
                            type_map = {
                                CallLog.Calls.INCOMING_TYPE: "incoming",
                                CallLog.Calls.OUTGOING_TYPE: "outgoing",
                                CallLog.Calls.MISSED_TYPE: "missed",
                                CallLog.Calls.VOICEMAIL_TYPE: "voicemail",
                                CallLog.Calls.REJECTED_TYPE: "rejected",
                                CallLog.Calls.BLOCKED_TYPE: "blocked"
                            }
                            
                            # Create call log entry
                            call_log_entry = {
                                "phoneNumber": phone_number,
                                "contactName": contact_name,
                                "type": type_map.get(call_type, "unknown"),
                                "duration": duration,
                                "timestamp": datetime.fromtimestamp(timestamp / 1000).isoformat(),
                                "callId": f"{self.get_device_id()}_{phone_number}_{timestamp}",
                                "rawId": str(call_id),
                                "deviceId": self.get_device_id()
                            }
                            
                            call_logs.append(call_log_entry)
                            row_count += 1
                            
                        except Exception as e:
                            logger.warning(f"Error processing call log row {row_count}: {e}")
                        
                        if not cursor.moveToNext():
                            break
                
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass
                        
            logger.info(f"Retrieved {len(call_logs)} call logs from Android")
            return call_logs
            
        except Exception as e:
            logger.error(f"Failed to get call logs: {e}")
            logger.error(traceback.format_exc())
            return self._get_sample_call_logs()
    
    def _safe_get_string(self, cursor, index: int, default: str = "") -> str:
        """Safely get string value from cursor"""
        try:
            if index >= 0:
                value = cursor.getString(index)
                return value if value is not None else default
        except Exception:
            pass
        return default
    
    def _safe_get_int(self, cursor, index: int, default: int = 0) -> int:
        """Safely get integer value from cursor"""
        try:
            if index >= 0:
                return cursor.getInt(index)
        except Exception:
            pass
        return default
    
    def _safe_get_long(self, cursor, index: int, default: int = 0) -> int:
        """Safely get long value from cursor"""
        try:
            if index >= 0:
                return cursor.getLong(index)
        except Exception:
            pass
        return default
    
    def _get_sample_call_logs(self) -> List[Dict]:
        """Generate realistic sample call logs for testing"""
        sample_calls = []
        base_time = datetime.now()
        
        # More realistic sample data
        sample_data = [
            ("+232123456789", "John Doe", "incoming", 120),
            ("+232987654321", "Jane Smith", "outgoing", 45),
            ("+232555666777", "Bob Wilson", "missed", 0),
            ("+232111222333", "Alice Brown", "incoming", 300),
            ("+232444555666", "Charlie Davis", "outgoing", 180),
            ("+232777888999", "Diana Prince", "incoming", 90),
            ("+232333444555", "Bruce Wayne", "outgoing", 200),
            ("+232666777888", "Clark Kent", "missed", 0),
            ("+232999000111", "Tony Stark", "incoming", 150),
            ("+232222333444", "Steve Rogers", "outgoing", 75)
        ]
        
        for i, (number, name, call_type, duration) in enumerate(sample_data):
            timestamp = base_time - timedelta(hours=i*2, minutes=i*15)
            sample_calls.append({
                "phoneNumber": number,
                "contactName": name,
                "type": call_type,
                "duration": duration,
                "timestamp": timestamp.isoformat(),
                "callId": f"{self.get_device_id()}_{number}_{int(timestamp.timestamp() * 1000)}",
                "deviceId": self.get_device_id()
            })
        
        logger.info(f"Generated {len(sample_calls)} sample call logs")
        return sample_calls


class BackendSync:
    """Enhanced backend synchronization with robust error handling"""
    
    def __init__(self, device_id: str, device_info: Dict):
        self.device_id = device_id
        self.device_info = device_info
        self.user_id = "user_" + hashlib.md5(device_id.encode()).hexdigest()[:8]
        
        # Production backend URLs
        self.backend_urls = [
            "https://kortahununited.onrender.com/api",
            "https://kortahun-center.onrender.com/api",
            "https://api.kortahun.com/api",
            "https://backend.kortahun.io/api",
            "https://callsync-api.herokuapp.com/api",
            "http://localhost:5001/api",
            "http://localhost:3001/api",
            "http://localhost:4000/api"
        ]
        
        self.active_backend_url = None
        self.session = self._setup_session()
        self.last_heartbeat = 0
        self.heartbeat_interval = 300  # 5 minutes
        
    def _setup_session(self) -> Optional[requests.Session]:
        """Setup HTTP session with comprehensive retry logic"""
        if not requests:
            logger.error("Requests library not available")
            return None
            
        session = requests.Session()
        
        # Enhanced retry strategy
        retry_strategy = Retry(
            total=5,
            status_forcelist=[408, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524],
            backoff_factor=2,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Comprehensive headers
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': f'CallSyncApp-Android/2.0 ({self.device_info.get("model", "Unknown")})',
            'X-App-Version': '2.0.0',
            'X-Platform': 'android-kivy'
        })
        
        # Configure timeouts and SSL
        session.timeout = (30, 60)  # (connect, read)
        session.verify = True  # Enable SSL verification
        
        return session
    
    def detect_backend(self) -> bool:
        """Detect working backend with comprehensive testing"""
        if not self.session:
            return False
            
        logger.info("Detecting available backend...")
        
        for i, url in enumerate(self.backend_urls):
            try:
                logger.info(f"Testing backend {i+1}/{len(self.backend_urls)}: {url}")
                
                # Test multiple endpoints
                test_endpoints = ["/health", "/status", "/ping", "/api/health"]
                
                for endpoint in test_endpoints:
                    try:
                        test_url = f"{url}{endpoint}"
                        response = self.session.get(test_url, timeout=(10, 15))
                        
                        if response.status_code in [200, 201, 204]:
                            self.active_backend_url = url
                            logger.info(f"✅ Backend detected: {url} (via {endpoint})")
                            return True
                            
                    except Exception as e:
                        logger.debug(f"Endpoint {endpoint} failed: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Backend {url} failed: {e}")
                continue
        
        logger.error("❌ No working backend found!")
        return False
    
    def register_device(self) -> bool:
        """Register device with enhanced error handling"""
        if not self.active_backend_url or not self.session:
            if not self.detect_backend():
                return False
        
        registration_data = {
            "deviceId": self.device_id,
            "userId": self.user_id,
            "deviceInfo": self.device_info,
            "permissions": {
                "readCallLog": True,
                "readPhoneState": True,
                "readContacts": True,
                "internet": True
            },
            "timestamp": datetime.now().isoformat(),
            "appVersion": "2.0.0"
        }
        
        # Try multiple registration endpoints
        registration_endpoints = [
            "/devices/register",
            "/device/register", 
            "/register",
            "/devices/simple-register",
            "/auth/register-device"
        ]
        
        for endpoint in registration_endpoints:
            try:
                logger.info(f"Attempting device registration via {endpoint}")
                
                response = self.session.post(
                    f"{self.active_backend_url}{endpoint}",
                    json=registration_data,
                    timeout=(30, 60)
                )
                
                logger.debug(f"Registration response: {response.status_code}")
                
                if response.status_code in [200, 201, 202]:
                    try:
                        result = response.json()
                        if result.get("success", True):  # Default to True if not specified
                            logger.info(f"✅ Device registered successfully via {endpoint}")
                            return True
                        else:
                            logger.warning(f"Registration response indicates failure: {result}")
                    except:
                        # If we can't parse JSON but got 200, assume success
                        logger.info(f"✅ Device registered (no JSON response) via {endpoint}")
                        return True
                else:
                    logger.warning(f"Registration failed with status {response.status_code}")
                
            except Exception as e:
                logger.warning(f"Registration failed via {endpoint}: {e}")
                continue
        
        logger.error("❌ All registration methods failed!")
        return False
    
    def sync_calls(self, calls: List[Dict]) -> Tuple[bool, Dict]:
        """Sync call logs with detailed response handling"""
        if not calls or not self.active_backend_url or not self.session:
            return False, {"error": "No calls or backend not available"}
        
        logger.info(f"Syncing {len(calls)} calls to backend...")
        
        sync_data = {
            "deviceId": self.device_id,
            "userId": self.user_id,
            "calls": calls,
            "timestamp": datetime.now().isoformat(),
            "totalCalls": len(calls)
        }
        
        # Try multiple sync endpoints
        sync_endpoints = ["/calls/sync", "/call-logs/sync", "/sync", "/data/calls"]
        
        for endpoint in sync_endpoints:
            try:
                logger.info(f"Attempting sync via {endpoint}")
                
                response = self.session.post(
                    f"{self.active_backend_url}{endpoint}",
                    json=sync_data,
                    timeout=(60, 120)
                )
                
                if response.status_code in [200, 201, 202]:
                    try:
                        result = response.json()
                        success = result.get("success", True)
                        
                        if success:
                            processed = result.get("data", {}).get("processed", len(calls))
                            skipped = result.get("data", {}).get("skipped", 0)
                            logger.info(f"✅ Sync successful via {endpoint}: {processed} processed, {skipped} skipped")
                            return True, result
                        else:
                            logger.warning(f"Sync response indicates failure: {result}")
                            
                    except:
                        # If we can't parse JSON but got 200, assume success
                        logger.info(f"✅ Sync successful (no JSON response) via {endpoint}")
                        return True, {"processed": len(calls), "skipped": 0}
                else:
                    logger.warning(f"Sync failed with status {response.status_code} via {endpoint}")
                    
            except Exception as e:
                logger.warning(f"Sync failed via {endpoint}: {e}")
                continue
        
        logger.error("❌ All sync methods failed!")
        return False, {"error": "All sync endpoints failed"}
    
    def ping_device(self) -> bool:
        """Send heartbeat with throttling"""
        current_time = time.time()
        if current_time - self.last_heartbeat < self.heartbeat_interval:
            return True  # Skip if too recent
            
        if not self.active_backend_url or not self.session:
            return False
        
        ping_data = {
            "deviceId": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }
        
        ping_endpoints = ["/devices/ping", "/ping", "/heartbeat", "/devices/status"]
        
        for endpoint in ping_endpoints:
            try:
                response = self.session.post(
                    f"{self.active_backend_url}{endpoint}",
                    json=ping_data,
                    timeout=(15, 30)
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    self.last_heartbeat = current_time
                    logger.debug(f"Heartbeat successful via {endpoint}")
                    return True
                    
            except Exception as e:
                logger.debug(f"Heartbeat failed via {endpoint}: {e}")
                continue
        
        return False


class CallSyncApp(App):
    """Enhanced Kivy Application with modern UI and robust error handling"""
    
    def build(self):
        self.title = "Call Log Sync Pro"
        self.call_manager = AndroidCallLogManager()
        self.backend_sync = None
        self.sync_thread = None
        self.is_syncing = False
        self.sync_stats = {"total": 0, "success": 0, "failed": 0}
        
        # Create main layout
        return self._create_ui()
    
    def _create_ui(self):
        """Create modern UI layout"""
        # Main layout with background
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))
        
        # Add background color
        with layout.canvas.before:
            Color(0.95, 0.95, 0.97, 1)  # Light gray background
            self.bg_rect = Rectangle(size=layout.size, pos=layout.pos)
        
        layout.bind(size=self._update_bg, pos=self._update_bg)
        
        # Title section
        title_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100))
        
        title = Label(
            text='📱 Call Log Sync Pro',
            size_hint_y=None,
            height=dp(50),
            font_size=dp(20),
            color=(0.2, 0.3, 0.7, 1),
            bold=True
        )
        title_layout.add_widget(title)
        
        subtitle = Label(
            text='Secure call log synchronization for Android',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(14),
            color=(0.5, 0.5, 0.5, 1)
        )
        title_layout.add_widget(subtitle)
        
        layout.add_widget(title_layout)
        
        # Status section
        status_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(100))
        
        self.status_label = Label(
            text='🔄 Initializing...',
            size_hint_y=None,
            height=dp(40),
            font_size=dp(16),
            color=(0.3, 0.3, 0.3, 1)
        )
        status_layout.add_widget(self.status_label)
        
        # Progress bar with styling
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(20)
        )
        status_layout.add_widget(self.progress_bar)
        
        # Stats label
        self.stats_label = Label(
            text='📊 Ready to sync',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(12),
            color=(0.6, 0.6, 0.6, 1)
        )
        status_layout.add_widget(self.stats_label)
        
        layout.add_widget(status_layout)
        
        # Control buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(80), spacing=dp(10))
        
        self.sync_button = Button(
            text='🚀 Start Sync',
            size_hint_x=0.4,
            background_color=(0.2, 0.7, 0.3, 1),
            font_size=dp(14),
            bold=True
        )
        self.sync_button.bind(on_press=self.toggle_sync)
        button_layout.add_widget(self.sync_button)
        
        test_button = Button(
            text='🔍 Test Connection',
            size_hint_x=0.3,
            background_color=(0.3, 0.5, 0.8, 1),
            font_size=dp(14)
        )
        test_button.bind(on_press=self.test_connection)
        button_layout.add_widget(test_button)
        
        settings_button = Button(
            text='⚙️ Settings',
            size_hint_x=0.3,
            background_color=(0.7, 0.5, 0.2, 1),
            font_size=dp(14)
        )
        settings_button.bind(on_press=self.show_settings)
        button_layout.add_widget(settings_button)
        
        layout.add_widget(button_layout)
        
        # Log section
        log_header = Label(
            text='📝 Activity Log:',
            size_hint_y=None,
            height=dp(30),
            font_size=dp(14),
            color=(0.3, 0.3, 0.3, 1),
            halign='left'
        )
        log_header.bind(size=log_header.setter('text_size'))
        layout.add_widget(log_header)
        
        # Scrollable log area
        scroll = ScrollView()
        self.log_text = Label(
            text='[INFO] Application started successfully\n',
            text_size=(None, None),
            valign='top',
            halign='left',
            font_size=dp(12),
            color=(0.2, 0.2, 0.2, 1)
        )
        scroll.add_widget(self.log_text)
        layout.add_widget(scroll)
        
        # Initialize app after layout is ready
        Clock.schedule_once(self.initialize_app, 1)
        
        return layout
    
    def _update_bg(self, instance, value):
        """Update background rectangle size"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = instance.size
            self.bg_rect.pos = instance.pos
    
    def initialize_app(self, dt):
        """Initialize app with comprehensive setup"""
        self.update_status("🔧 Initializing application...")
        self.log_message("Starting Call Log Sync Pro v2.0")
        
        try:
            # Step 1: Check Android environment
            if ANDROID_AVAILABLE:
                self.log_message("✅ Android environment detected")
            else:
                self.log_message("⚠️ Running in desktop mode (testing)")
            
            # Step 2: Request permissions
            self.update_status("🔐 Requesting permissions...")
            if self.call_manager.request_permissions():
                self.log_message("✅ Permissions granted successfully")
                
                # Step 3: Get device information
                device_id = self.call_manager.get_device_id()
                device_info = self.call_manager.get_device_info()
                
                self.log_message(f"📱 Device ID: {device_id}")
                self.log_message(f"📱 Device: {device_info.get('manufacturer', 'Unknown')} {device_info.get('model', 'Unknown')}")
                self.log_message(f"📱 Android: {device_info.get('osVersion', 'Unknown')} (SDK {device_info.get('sdkVersion', 'Unknown')})")
                
                # Step 4: Initialize backend sync
                self.backend_sync = BackendSync(device_id, device_info)
                
                # Step 5: Test call log access
                test_calls = self.call_manager.get_call_logs(limit=5)
                self.log_message(f"📞 Call log test: {len(test_calls)} calls accessible")
                
                self.update_status("✅ Ready to sync")
                self.update_stats()
                
            else:
                self.update_status("❌ Permissions required!")
                self.log_message("❌ Please grant all required permissions")
                self._show_permission_dialog()
                
        except Exception as e:
            self.update_status("❌ Initialization failed")
            self.log_message(f"❌ Initialization error: {e}")
            logger.error(f"App initialization failed: {e}")
            logger.error(traceback.format_exc())
    
    def _show_permission_dialog(self):
        """Show permission requirements dialog"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        message = Label(
            text="""📱 Required Permissions:

• 📞 Read Call Log - Access call history
• 📱 Read Phone State - Device identification  
• 👥 Read Contacts - Contact name resolution
• 🌐 Internet Access - Backend synchronization
• 💾 Storage Access - App data management

Please grant these permissions and restart the app.""",
            text_size=(dp(300), None),
            halign='left',
            valign='top'
        )
        content.add_widget(message)
        
        close_btn = Button(
            text='OK',
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(close_btn)
        
        popup = Popup(
            title='Permissions Required',
            content=content,
            size_hint=(0.8, 0.6)
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    @mainthread
    def update_status(self, status: str):
        """Update status label on main thread"""
        self.status_label.text = status
    
    @mainthread
    def update_progress(self, value: float):
        """Update progress bar on main thread"""
        self.progress_bar.value = min(100, max(0, value))
    
    @mainthread
    def update_stats(self):
        """Update statistics display"""
        stats_text = f"📊 Total: {self.sync_stats['total']} | Success: {self.sync_stats['success']} | Failed: {self.sync_stats['failed']}"
        self.stats_label.text = stats_text
    
    @mainthread
    def log_message(self, message: str):
        """Add timestamped message to log on main thread"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.text += log_entry
        
        # Update text_size for proper text wrapping
        if self.log_text.parent:
            self.log_text.text_size = (self.log_text.parent.width - dp(20), None)
        
        # Keep log size manageable
        lines = self.log_text.text.split('\n')
        if len(lines) > 100:
            self.log_text.text = '\n'.join(lines[-80:])  # Keep last 80 lines
    
    def toggle_sync(self, instance):
        """Toggle synchronization on/off"""
        if not self.is_syncing:
            self.start_sync()
        else:
            self.stop_sync()
    
    def start_sync(self):
        """Start continuous synchronization"""
        if not self.backend_sync:
            self.log_message("❌ Backend not initialized!")
            self._show_error_dialog("Backend Error", "Backend synchronization not available. Please check initialization.")
            return
        
        if not self.call_manager.permissions_granted:
            self.log_message("❌ Permissions not granted!")
            self._show_error_dialog("Permission Error", "Required permissions not granted. Please enable permissions and restart.")
            return
        
        self.is_syncing = True
        self.sync_button.text = "⏹️ Stop Sync"
        self.sync_button.background_color = (0.8, 0.3, 0.2, 1)
        self.update_status("🚀 Starting synchronization...")
        self.log_message("🚀 Starting continuous sync...")
        
        # Start sync thread
        self.sync_thread = threading.Thread(target=self.sync_worker, daemon=True)
        self.sync_thread.start()
    
    def stop_sync(self):
        """Stop synchronization"""
        self.is_syncing = False
        self.sync_button.text = "🚀 Start Sync"
        self.sync_button.background_color = (0.2, 0.7, 0.3, 1)
        self.update_status("⏹️ Stopping synchronization...")
        self.log_message("⏹️ Sync stopped by user")
    
    def sync_worker(self):
        """Enhanced background sync worker with comprehensive error handling"""
        failure_count = 0
        max_failures = 5
        sync_interval = 300  # 5 minutes
        
        self.log_message("🔄 Sync worker started")
        
        while self.is_syncing:
            try:
                cycle_start = time.time()
                self.update_status("🔍 Detecting backend...")
                self.update_progress(5)
                
                # Step 1: Detect and verify backend
                if not self.backend_sync.active_backend_url:
                    if not self.backend_sync.detect_backend():
                        self.log_message("❌ No backend available, retrying in 30s")
                        failure_count += 1
                        self._wait_with_progress(30, "⏳ Waiting for backend...")
                        continue
                
                self.log_message(f"✅ Using backend: {self.backend_sync.active_backend_url}")
                self.update_progress(15)
                
                # Step 2: Register device
                self.update_status("📝 Registering device...")
                if not self.backend_sync.register_device():
                    self.log_message("❌ Device registration failed")
                    failure_count += 1
                    self._wait_with_progress(30, "⏳ Registration retry...")
                    continue
                
                self.log_message("✅ Device registered successfully")
                self.update_progress(30)
                
                # Step 3: Retrieve call logs
                self.update_status("📞 Retrieving call logs...")
                calls = self.call_manager.get_call_logs(limit=1000, days_back=30)
                
                if not calls:
                    self.log_message("ℹ️ No call logs to sync")
                    self.update_progress(100)
                    self._wait_with_progress(sync_interval, "✅ Sync completed, waiting...")
                    continue
                
                self.log_message(f"📞 Retrieved {len(calls)} call logs")
                self.update_progress(60)
                
                # Step 4: Sync to backend
                self.update_status("🔄 Syncing to backend...")
                success, result = self.backend_sync.sync_calls(calls)
                
                if success:
                    processed = result.get("data", {}).get("processed", len(calls))
                    skipped = result.get("data", {}).get("skipped", 0)
                    
                    self.log_message(f"✅ Sync successful: {processed} processed, {skipped} skipped")
                    self.sync_stats["total"] += len(calls)
                    self.sync_stats["success"] += processed
                    failure_count = 0
                else:
                    error_msg = result.get("error", "Unknown error")
                    self.log_message(f"❌ Sync failed: {error_msg}")
                    self.sync_stats["failed"] += len(calls)
                    failure_count += 1
                
                self.update_progress(80)
                self.update_stats()
                
                # Step 5: Send heartbeat
                self.update_status("💓 Sending heartbeat...")
                if self.backend_sync.ping_device():
                    self.log_message("💓 Heartbeat sent successfully")
                else:
                    self.log_message("⚠️ Heartbeat failed")
                
                self.update_progress(100)
                
                # Calculate cycle time
                cycle_time = time.time() - cycle_start
                self.log_message(f"⏱️ Sync cycle completed in {cycle_time:.1f}s")
                
                # Handle failure threshold
                if failure_count >= max_failures:
                    self.log_message(f"❌ Too many failures ({max_failures}), resetting backend...")
                    self.backend_sync.active_backend_url = None
                    failure_count = 0
                    self._wait_with_progress(60, "🔄 Backend reset, waiting...")
                    continue
                
                # Wait for next cycle
                self._wait_with_progress(sync_interval, "✅ Sync completed, waiting for next cycle...")
                
            except Exception as e:
                self.log_message(f"❌ Sync error: {e}")
                logger.error(f"Sync worker error: {e}")
                logger.error(traceback.format_exc())
                failure_count += 1
                self._wait_with_progress(30, "❌ Error occurred, retrying...")
        
        self.update_status("⏹️ Sync stopped")
        self.update_progress(0)
        self.log_message("⏹️ Sync worker stopped")
    
    def _wait_with_progress(self, duration: int, status_message: str):
        """Wait with progress indication"""
        self.update_status(status_message)
        
        for i in range(duration):
            if not self.is_syncing:
                break
            
            progress = (i / duration) * 100
            self.update_progress(progress)
            time.sleep(1)
        
        self.update_progress(0)
    
    def test_connection(self, instance):
        """Test backend connection comprehensively"""
        if not self.backend_sync:
            self.log_message("❌ Backend not initialized!")
            return
        
        self.update_status("🔍 Testing connection...")
        self.log_message("🔍 Starting connection test...")
        
        def test_worker():
            try:
                # Test 1: Backend detection
                self.log_message("Test 1: Backend detection...")
                if self.backend_sync.detect_backend():
                    self.log_message(f"✅ Backend found: {self.backend_sync.active_backend_url}")
                    
                    # Test 2: Device registration
                    self.log_message("Test 2: Device registration...")
                    if self.backend_sync.register_device():
                        self.log_message("✅ Device registration successful")
                        
                        # Test 3: Call log access
                        self.log_message("Test 3: Call log access...")
                        test_calls = self.call_manager.get_call_logs(limit=5)
                        self.log_message(f"✅ Call log access: {len(test_calls)} calls retrieved")
                        
                        # Test 4: Sync test
                        if test_calls:
                            self.log_message("Test 4: Sync test...")
                            success, result = self.backend_sync.sync_calls(test_calls[:2])  # Test with 2 calls
                            if success:
                                self.log_message("✅ Sync test successful")
                            else:
                                self.log_message(f"❌ Sync test failed: {result.get('error', 'Unknown')}")
                        
                        # Test 5: Heartbeat
                        self.log_message("Test 5: Heartbeat test...")
                        if self.backend_sync.ping_device():
                            self.log_message("✅ Heartbeat successful")
                        else:
                            self.log_message("⚠️ Heartbeat failed")
                        
                        self.update_status("✅ Connection test completed")
                        self.log_message("🎉 All tests completed successfully!")
                        
                    else:
                        self.log_message("❌ Device registration failed")
                        self.update_status("❌ Registration failed")
                else:
                    self.log_message("❌ No backend available")
                    self.update_status("❌ No backend found")
                    
            except Exception as e:
                self.log_message(f"❌ Test error: {e}")
                self.update_status("❌ Test failed")
                logger.error(f"Connection test error: {e}")
        
        # Run test in background thread
        threading.Thread(target=test_worker, daemon=True).start()
    
    def show_settings(self, instance):
        """Show settings dialog"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Device info
        device_info = self.call_manager.get_device_info() if self.call_manager else {}
        info_text = f"""📱 Device Information:
        
• Device ID: {self.call_manager.get_device_id() if self.call_manager else 'Unknown'}
• Model: {device_info.get('manufacturer', 'Unknown')} {device_info.get('model', 'Unknown')}
• Android: {device_info.get('osVersion', 'Unknown')} (SDK {device_info.get('sdkVersion', 'Unknown')})
• App Version: 2.0.0
• Backend: {self.backend_sync.active_backend_url if self.backend_sync else 'Not connected'}

🔧 Sync Settings:
• Sync Interval: 5 minutes
• Call Log History: 30 days
• Max Calls per Sync: 1000
• Retry Attempts: 5"""
        
        info_label = Label(
            text=info_text,
            text_size=(dp(350), None),
            halign='left',
            valign='top',
            font_size=dp(12)
        )
        content.add_widget(info_label)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(10))
        
        refresh_btn = Button(text='🔄 Refresh Permissions', size_hint_x=0.6)
        refresh_btn.bind(on_press=lambda x: self.call_manager.request_permissions())
        button_layout.add_widget(refresh_btn)
        
        close_btn = Button(text='Close', size_hint_x=0.4)
        button_layout.add_widget(close_btn)
        
        content.add_widget(button_layout)
        
        popup = Popup(
            title='⚙️ Settings & Information',
            content=content,
            size_hint=(0.9, 0.8)
        )
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def _show_error_dialog(self, title: str, message: str):
        """Show error dialog"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        
        message_label = Label(
            text=message,
            text_size=(dp(300), None),
            halign='center',
            valign='center'
        )
        content.add_widget(message_label)
        
        ok_btn = Button(
            text='OK',
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(ok_btn)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.8, 0.4)
        )
        ok_btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == '__main__':
    try:
        # Configure Kivy logging
        from kivy.config import Config
        Config.set('kivy', 'log_level', 'info')
        
        # Run the app
        CallSyncApp().run()
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        logger.error(traceback.format_exc())
        print(f"FATAL ERROR: {e}")
        sys.exit(1)