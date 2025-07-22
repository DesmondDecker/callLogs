<<<<<<< HEAD
# main.py - Complete production-ready main application

import os
import sys
import json
import time
import threading
from typing import Optional
=======
import json
import time
import threading
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
>>>>>>> b32e8134d3447a7619a62fdb76754082488545b5

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.core.window import Window

# Import our robust backend system
from config import AppConfig, StorageManager, is_android, get_platform_name
from backend_detector import BackendDetector

# Call log handling imports
try:
<<<<<<< HEAD
    if is_android():
        from jnius import autoclass, cast
        from android.permissions import request_permissions, Permission
        from android import activity
    else:
        # Mock for desktop testing
        class MockJnius:
            @staticmethod
            def autoclass(name):
                return None
        autoclass = MockJnius.autoclass
=======
    from android.permissions import request_permissions, Permission
    from jnius import autoclass

    ANDROID_AVAILABLE = True
    # Request permissions immediately
    request_permissions([
        Permission.READ_CALL_LOG,
        Permission.READ_PHONE_STATE,
        Permission.READ_CONTACTS,
        Permission.INTERNET
    ])
>>>>>>> b32e8134d3447a7619a62fdb76754082488545b5
except ImportError:
    Logger.warning("Android modules not available - running in desktop mode")

<<<<<<< HEAD
class CallLogManager:
    """
    Cross-platform call log manager
    """
    
    def __init__(self):
        self.permissions_granted = False
        self.call_logs = []
    
    def request_permissions(self):
        """Request necessary Android permissions"""
        if not is_android():
            Logger.info("Desktop mode - permissions not needed")
            self.permissions_granted = True
            return True
        
        try:
            Logger.info("Requesting Android permissions...")
            request_permissions([
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ])
            self.permissions_granted = True
            Logger.info("Permissions requested successfully")
            return True
        except Exception as e:
            Logger.error(f"Failed to request permissions: {e}")
            self.permissions_granted = False
            return False
    
    def get_call_logs(self, limit: int = 100):
        """Get call logs from device"""
        if not is_android():
            # Return mock data for desktop testing
            return self._get_mock_call_logs(limit)
        
        if not self.permissions_granted:
            Logger.warning("Permissions not granted for call log access")
            return []
        
        try:
            return self._get_android_call_logs(limit)
=======

class CallLogMonitor:
    def __init__(self):
        self.possible_urls = [
            "https://kortahununited.onrender.com/api/devices",  # Direct endpoint
            "https://kortahun-center.onrender.com/api/devices",
            "https://kortahununited.onrender.com/api",  # Base URL
            "https://kortahun-center.onrender.com/api",
            "http://localhost:5001/api",
            "http://localhost:3001/api"
        ]
        self.api_base_url = ""
        self.device_id = self._get_device_id()
        self.user_id = ""
        self.is_monitoring = False
        self.last_sync_time = None
        self.device_registered = False
        self.debug_mode = True  # Enable detailed logging

        # Setup session with more robust configuration
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3, 
            backoff_factor=2, 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'CallLogMonitor/2.0.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })

        # Load settings
        self.store = JsonStore('call_monitor_settings.json')
        self._load_settings()

    def _get_device_id(self) -> str:
        """Generate or retrieve device ID"""
        try:
            store = JsonStore('call_monitor_settings.json')
            if store.exists('device_id'):
                return store.get('device_id')['value']
        except:
            pass

        if ANDROID_AVAILABLE:
            try:
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.mActivity
                resolver = context.getContentResolver()
                Settings = autoclass('android.provider.Settings$Secure')
                android_id = Settings.getString(resolver, 'android_id')
                device_id = f"android_{android_id}"
                Logger.info(f"Generated Android device ID: {device_id}")
            except Exception as e:
                Logger.error(f"Error getting Android ID: {e}")
                device_id = f"android_{str(uuid.uuid4()).replace('-', '')[:16]}"
        else:
            device_id = f"desktop_{str(uuid.uuid4()).replace('-', '')[:16]}"

        try:
            store = JsonStore('call_monitor_settings.json')
            store.put('device_id', value=device_id)
        except:
            pass
        return device_id

    def debug_log(self, message):
        """Enhanced debug logging"""
        if self.debug_mode:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            Logger.info(f"[DEBUG {timestamp}] {message}")

    def _load_settings(self):
        """Load settings from storage"""
        try:
            settings = ['user_id', 'api_url', 'last_sync', 'device_registered']
            for setting in settings:
                if self.store.exists(setting):
                    value = self.store.get(setting)['value']
                    if setting == 'api_url':
                        self.api_base_url = value
                    else:
                        setattr(self, setting, value)
                    self.debug_log(f"Loaded {setting}: {value}")
        except Exception as e:
            Logger.error(f"Error loading settings: {e}")

    def _save_settings(self):
        """Save settings to storage"""
        try:
            settings = {
                'user_id': self.user_id,
                'api_url': self.api_base_url,
                'device_registered': self.device_registered
            }
            if self.last_sync_time:
                settings['last_sync'] = self.last_sync_time

            for key, value in settings.items():
                self.store.put(key, value=value)
                self.debug_log(f"Saved {key}: {value}")
        except Exception as e:
            Logger.error(f"Error saving settings: {e}")

    def test_connectivity(self) -> Dict:
        """Test basic internet connectivity"""
        test_urls = [
            "https://httpbin.org/get",
            "https://jsonplaceholder.typicode.com/posts/1",
            "https://www.google.com"
        ]
        
        results = {}
        for url in test_urls:
            try:
                response = self.session.get(url, timeout=10)
                results[url] = {
                    'status': response.status_code,
                    'success': response.status_code == 200,
                    'time': response.elapsed.total_seconds()
                }
                self.debug_log(f"Connectivity test {url}: {response.status_code}")
            except Exception as e:
                results[url] = {'success': False, 'error': str(e)}
                self.debug_log(f"Connectivity test {url} failed: {e}")
        return results

    def detect_backend_url(self) -> bool:
        """Auto-detect working backend URL with detailed testing"""
        Logger.info("Starting comprehensive backend URL detection...")
        
        # First test basic connectivity
        connectivity = self.test_connectivity()
        has_internet = any(result.get('success', False) for result in connectivity.values())
        
        if not has_internet:
            Logger.error("No internet connectivity detected!")
            return False
        
        Logger.info("Internet connectivity confirmed")
        
        for url in self.possible_urls:
            try:
                self.debug_log(f"Testing backend URL: {url}")
                
                # Test different endpoints
                test_endpoints = [
                    f"{url}",  # Base URL
                    f"{url}/health" if not url.endswith('/devices') else f"{url.replace('/devices', '')}/health",
                    f"{url}/" if not url.endswith('/') else url[:-1]
                ]
                
                for endpoint in test_endpoints:
                    try:
                        self.debug_log(f"  -> Trying endpoint: {endpoint}")
                        response = self.session.get(endpoint, timeout=15)
                        
                        self.debug_log(f"  -> Response: {response.status_code} - {response.reason}")
                        self.debug_log(f"  -> Headers: {dict(response.headers)}")
                        
                        if response.status_code == 200:
                            try:
                                data = response.json()
                                self.debug_log(f"  -> JSON Response: {json.dumps(data, indent=2)}")
                            except:
                                self.debug_log(f"  -> Text Response: {response.text[:200]}")
                            
                            # Set the base URL (remove specific endpoints)
                            if url.endswith('/devices'):
                                self.api_base_url = url.replace('/devices', '')
                            else:
                                self.api_base_url = url
                            
                            Logger.info(f"✅ Backend found: {self.api_base_url}")
                            self._save_settings()
                            return True
                            
                    except Exception as e:
                        self.debug_log(f"  -> Endpoint failed: {e}")
                        continue
                        
            except Exception as e:
                Logger.info(f"❌ Failed: {url} - {e}")
                
        Logger.error("No working backend URL found")
        return False

    def get_device_info(self) -> Dict:
        """Get comprehensive device information"""
        device_info = {
            'model': 'Desktop',
            'manufacturer': 'Python',
            'os': 'Desktop',
            'osVersion': '1.0',
            'appVersion': '2.0.0'
        }

        if ANDROID_AVAILABLE:
            try:
                Build = autoclass('android.os.Build')
                device_info.update({
                    'model': str(Build.MODEL or 'Unknown'),
                    'manufacturer': str(Build.MANUFACTURER or 'Unknown'),
                    'os': 'Android',
                    'osVersion': str(Build.VERSION.RELEASE or 'Unknown'),
                    'sdk': str(Build.VERSION.SDK_INT or 'Unknown'),
                    'brand': str(Build.BRAND or 'Unknown'),
                    'product': str(Build.PRODUCT or 'Unknown')
                })
                self.debug_log(f"Android device info: {device_info}")
            except Exception as e:
                Logger.error(f"Error getting device info: {e}")

        # Ensure all values are strings
        return {k: str(v or 'Unknown') for k, v in device_info.items()}

    def register_device(self) -> bool:
        """Register device with comprehensive error handling"""
        if not self.api_base_url and not self.detect_backend_url():
            Logger.error("No backend URL available for registration")
            return False

        if not self.user_id.strip():
            Logger.error("User ID is required for registration")
            return False

        try:
            # Prepare registration payload
            payload = {
                'deviceId': self.device_id.strip(),
                'userId': self.user_id.strip(),
                'deviceInfo': self.get_device_info(),
                'permissions': {
                    'readCallLog': True,
                    'readPhoneState': True,
                    'readContacts': True
                }
            }

            self.debug_log(f"Registration payload: {json.dumps(payload, indent=2)}")
            
            # Try multiple registration endpoints
            endpoints = [
                f"{self.api_base_url}/devices/register",
                f"{self.api_base_url}/devices/simple-register",
                f"{self.api_base_url}/register"
            ]
            
            for endpoint in endpoints:
                try:
                    self.debug_log(f"Attempting registration at: {endpoint}")
                    Logger.info(f"Registering device: {self.device_id} for user: {self.user_id}")
                    
                    response = self.session.post(
                        endpoint,
                        json=payload,
                        timeout=30
                    )
                    
                    self.debug_log(f"Registration response: {response.status_code} - {response.reason}")
                    self.debug_log(f"Response headers: {dict(response.headers)}")
                    
                    # Log response content
                    try:
                        response_data = response.json()
                        self.debug_log(f"Response JSON: {json.dumps(response_data, indent=2)}")
                    except:
                        self.debug_log(f"Response text: {response.text}")

                    if response.status_code in [200, 201]:
                        try:
                            data = response.json()
                            if data.get('success', True):  # Default to True if 'success' not present
                                self.device_registered = True
                                self._save_settings()
                                Logger.info("✅ Device registered successfully")
                                return True
                            else:
                                Logger.error(f"Registration failed: {data.get('message', 'Unknown error')}")
                        except:
                            # If we can't parse JSON but got 200/201, assume success
                            self.device_registered = True
                            self._save_settings()
                            Logger.info("✅ Device registered successfully (assumed from status code)")
                            return True
                    else:
                        Logger.error(f"Registration failed with status {response.status_code}: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    Logger.error(f"Registration request failed for {endpoint}: {e}")
                    continue
                except Exception as e:
                    Logger.error(f"Unexpected error during registration at {endpoint}: {e}")
                    continue

            Logger.error("All registration endpoints failed")
            return False

        except Exception as e:
            Logger.error(f"Registration error: {e}")
            return False

    def get_call_logs(self) -> List[Dict]:
        """Get call logs from device"""
        if not ANDROID_AVAILABLE:
            Logger.warning("Android not available - no call logs to retrieve")
            return []

        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            resolver = context.getContentResolver()
            CallLog = autoclass('android.provider.CallLog$Calls')

            cursor = resolver.query(CallLog.CONTENT_URI, None, None, None, f"{CallLog.DATE} DESC LIMIT 50")
            calls = []

            if cursor and cursor.moveToFirst():
                type_map = {1: 'incoming', 2: 'outgoing', 3: 'missed'}
                while True:
                    try:
                        number = cursor.getString(cursor.getColumnIndex(CallLog.NUMBER)) or "Unknown"
                        name = cursor.getString(cursor.getColumnIndex(CallLog.CACHED_NAME))
                        call_type = cursor.getInt(cursor.getColumnIndex(CallLog.TYPE))
                        duration = cursor.getInt(cursor.getColumnIndex(CallLog.DURATION))
                        date = cursor.getLong(cursor.getColumnIndex(CallLog.DATE))

                        call_data = {
                            'number': number,
                            'name': name,
                            'type': type_map.get(call_type, 'unknown'),
                            'duration': duration,
                            'timestamp': datetime.fromtimestamp(date / 1000).isoformat(),
                            'deviceId': self.device_id,
                            'callId': hashlib.md5(f"{self.device_id}_{number}_{date}".encode()).hexdigest()
                        }
                        calls.append(call_data)
                    except Exception as e:
                        Logger.error(f"Error processing call: {e}")
                        continue
                    if not cursor.moveToNext():
                        break

            if cursor:
                cursor.close()
            Logger.info(f"Retrieved {len(calls)} call logs")
            return calls
>>>>>>> b32e8134d3447a7619a62fdb76754082488545b5
        except Exception as e:
            Logger.error(f"Failed to get call logs: {e}")
            return []
<<<<<<< HEAD
    
    def _get_mock_call_logs(self, limit: int):
        """Generate mock call logs for testing"""
        import random
        
        mock_logs = []
        for i in range(min(limit, 20)):
            mock_logs.append({
                'number': f'+1555000{i:04d}',
                'name': f'Contact {i}',
                'type': random.choice(['incoming', 'outgoing', 'missed']),
                'duration': random.randint(0, 600),
                'timestamp': int(time.time()) - random.randint(0, 86400 * 7),
                'id': str(i)
            })
        
        Logger.info(f"Generated {len(mock_logs)} mock call logs")
        return mock_logs
    
    def _get_android_call_logs(self, limit: int):
        """Get actual call logs from Android device"""
        try:
            # Android call log access
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            ContentResolver = context.getContentResolver()
            
            # Call log URI
            CallLog = autoclass('android.provider.CallLog$Calls')
            uri = CallLog.CONTENT_URI
            
            # Query columns
            projection = [
                CallLog.NUMBER,
                CallLog.CACHED_NAME,
                CallLog.TYPE,
                CallLog.DURATION,
                CallLog.DATE,
                CallLog._ID
            ]
            
            # Query call logs
            cursor = ContentResolver.query(
                uri,
                projection,
                None,
                None,
                f"{CallLog.DATE} DESC LIMIT {limit}"
            )
            
            call_logs = []
            if cursor and cursor.moveToFirst():
                while not cursor.isAfterLast():
                    call_log = {
                        'number': cursor.getString(0) or 'Unknown',
                        'name': cursor.getString(1) or 'Unknown',
                        'type': self._get_call_type(cursor.getInt(2)),
                        'duration': cursor.getInt(3),
                        'timestamp': cursor.getLong(4) // 1000,  # Convert to seconds
                        'id': cursor.getString(5)
                    }
                    call_logs.append(call_log)
                    cursor.moveToNext()
                
                cursor.close()
            
            Logger.info(f"Retrieved {len(call_logs)} call logs")
            return call_logs
            
        except Exception as e:
            Logger.error(f"Failed to get Android call logs: {e}")
            return []
    
    def _get_call_type(self, call_type_int):
        """Convert Android call type int to string"""
        call_types = {
            1: 'incoming',
            2: 'outgoing',
            3: 'missed'
        }
        return call_types.get(call_type_int, 'unknown')

class KortahunApp(App):
    """
    Main application with robust backend connectivity
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.backend_detector = BackendDetector(timeout=15, max_retries=3)
        self.call_log_manager = CallLogManager()
        
        # Backend connection info
        self.api_url = None
        self.user_id = None
        self.device_id = None
        self.is_initialized = False
        
        # UI references
        self.main_layout = None
        self.status_label = None
        self.progress_bar = None
        self.init_button = None
        self.sync_button = None
        self.test_button = None
        self.info_label = None
        self.log_display = None
        self.manual_url_input = None
    
    def build(self):
        """
        Build the main UI
        """
        # Set window size for desktop testing
        if not is_android():
            Window.size = (400, 700)
        
        # Main layout
        self.main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Title
        title = Label(
            text='Kortahun United\nCall Logger',
            font_size='20sp',
            size_hint_y=0.08,
            color=(0.2, 0.6, 1, 1),  # Blue color
            halign='center'
        )
        title.bind(size=title.setter('text_size'))
        self.main_layout.add_widget(title)
        
        # Status label
        self.status_label = Label(
            text='Starting application...',
            font_size='14sp',
            size_hint_y=0.12,
            text_size=(None, None),
            halign='center'
        )
        self.main_layout.add_widget(self.status_label)
        
        # Progress bar
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=0.05
        )
        self.main_layout.add_widget(self.progress_bar)
        
        # Button layout
        button_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=0.25)
        
        # Initialize button
        self.init_button = Button(
            text='Initialize Backend',
            size_hint_y=0.33,
            background_color=(0.2, 0.8, 0.2, 1)  # Green
        )
        self.init_button.bind(on_press=self.initialize_backend)
        button_layout.add_widget(self.init_button)
        
        # Sync button (initially disabled)
        self.sync_button = Button(
            text='Sync Call Logs',
            size_hint_y=0.33,
            background_color=(0.2, 0.6, 1, 1),  # Blue
            disabled=True
        )
        self.sync_button.bind(on_press=self.sync_call_logs)
        button_layout.add_widget(self.sync_button)
        
        # Test connectivity button
        self.test_button = Button(
            text='Test Connectivity',
            size_hint_y=0.34,
            background_color=(1, 0.6, 0.2, 1)  # Orange
        )
        self.test_button.bind(on_press=self.test_connectivity)
        button_layout.add_widget(self.test_button)
        
        self.main_layout.add_widget(button_layout)
        
        # Manual URL input section
        url_layout = BoxLayout(orientation='horizontal', size_hint_y=0.08, spacing=5)
        
        self.manual_url_input = TextInput(
            text='https://kortahununited.onrender.com/api',
            size_hint_x=0.7,
            multiline=False,
            font_size='12sp'
        )
        url_layout.add_widget(self.manual_url_input)
        
        manual_test_button = Button(
            text='Test URL',
            size_hint_x=0.3,
            background_color=(0.8, 0.2, 0.8, 1)  # Purple
        )
        manual_test_button.bind(on_press=self.test_manual_url)
        url_layout.add_widget(manual_test_button)
        
        self.main_layout.add_widget(url_layout)
        
        # Info display with scroll
        scroll = ScrollView(size_hint_y=0.42)
        
        self.info_label = Label(
            text=self.get_initial_info(),
            font_size='12sp',
            text_size=(Window.width - 60, None),
            halign='left',
            valign='top',
            size_hint_y=None
        )
        self.info_label.bind(texture_size=self.info_label.setter('size'))
        
        scroll.add_widget(self.info_label)
        self.main_layout.add_widget(scroll)
        
        # Start initialization automatically
        Clock.schedule_once(self.auto_initialize, 2)
        
        return self.main_layout
    
    def get_initial_info(self):
        """Get initial app information"""
        device_info = AppConfig.get_device_info()
        api_urls = AppConfig.get_api_urls()
        
        info_text = f"""Platform: {get_platform_name()}
Android: {is_android()}
Environment: {"Development" if AppConfig.is_development_environment() else "Production"}
=======

    def sync_call_logs(self) -> bool:
        """Sync call logs to backend"""
        try:
            if not self.device_registered and not self.register_device():
                Logger.error("Device not registered, cannot sync")
                return False

            calls = self.get_call_logs()
            if not calls:
                Logger.info("No call logs to sync")
                return True

            # Format for backend API
            formatted_calls = [{
                'callId': call.get('callId'),
                'phoneNumber': call.get('number'),
                'contactName': call.get('name'),
                'type': call.get('type'),
                'duration': call.get('duration', 0),
                'timestamp': call.get('timestamp')
            } for call in calls[:20]]

            payload = {
                'deviceId': self.device_id,
                'userId': self.user_id,
                'calls': formatted_calls
            }

            self.debug_log(f"Sync payload: {json.dumps(payload, indent=2)}")

            response = self.session.post(f"{self.api_base_url}/calls/sync", json=payload, timeout=60)
            
            self.debug_log(f"Sync response: {response.status_code}")
            if response.status_code == 200:
                self.last_sync_time = datetime.now().isoformat()
                self._save_settings()
                Logger.info(f"Synced {len(formatted_calls)} calls")
                return True
            else:
                Logger.error(f"Sync failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            Logger.error(f"Sync error: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """Send heartbeat to backend"""
        try:
            response = self.session.post(
                f"{self.api_base_url}/devices/ping",
                json={'deviceId': self.device_id},
                timeout=10
            )
            success = response.status_code == 200
            self.debug_log(f"Heartbeat: {response.status_code} - {'Success' if success else 'Failed'}")
            return success
        except Exception as e:
            self.debug_log(f"Heartbeat failed: {e}")
            return False


class CallLogApp(App):
    def __init__(self):
        super().__init__()
        self.monitor = CallLogMonitor()
        self.is_running = False

    def build(self):
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title
        title_label = Label(text='Call Log Monitor v2.1\nDebug Enhanced',
                            size_hint_y=None, height=80, font_size='20sp')
        main_layout.add_widget(title_label)

        # Settings grid
        settings_layout = GridLayout(cols=2, size_hint_y=None, height=250, spacing=10)

        # User ID input
        settings_layout.add_widget(Label(text='User ID:', size_hint_x=0.3))
        self.user_id_input = TextInput(
            text=self.monitor.user_id or f"user_{str(uuid.uuid4())[:8]}",
            multiline=False, size_hint_x=0.7
        )
        self.user_id_input.bind(text=self.on_user_id_change)
        settings_layout.add_widget(self.user_id_input)

        # Device ID display
        settings_layout.add_widget(Label(text='Device ID:', size_hint_x=0.3))
        device_id_label = Label(text=self.monitor.device_id[:20] + "...", size_hint_x=0.7)
        device_id_label.text_size = (None, None)
        settings_layout.add_widget(device_id_label)

        # Backend URL display
        settings_layout.add_widget(Label(text='Backend:', size_hint_x=0.3))
        self.api_url_display = Label(text=self.monitor.api_base_url or 'Not detected', size_hint_x=0.7)
        self.api_url_display.text_size = (None, None)
        settings_layout.add_widget(self.api_url_display)

        # Status display
        settings_layout.add_widget(Label(text='Status:', size_hint_x=0.3))
        self.status_label = Label(
            text='✅ Registered' if self.monitor.device_registered else '❌ Not Registered',
            size_hint_x=0.7
        )
        settings_layout.add_widget(self.status_label)

        # Debug mode switch
        settings_layout.add_widget(Label(text='Debug Mode:', size_hint_x=0.3))
        self.debug_switch = Switch(active=True, size_hint_x=0.7)
        self.debug_switch.bind(active=self.on_debug_toggle)
        settings_layout.add_widget(self.debug_switch)

        # Auto sync switch
        settings_layout.add_widget(Label(text='Auto Sync:', size_hint_x=0.3))
        self.auto_sync_switch = Switch(active=True, size_hint_x=0.7)
        settings_layout.add_widget(self.auto_sync_switch)

        main_layout.add_widget(settings_layout)

        # Control buttons
        button_layout = GridLayout(cols=3, size_hint_y=None, height=100, spacing=5)

        detect_btn = Button(text='🔍 Detect\nBackend')
        detect_btn.bind(on_press=self.detect_backend)
        button_layout.add_widget(detect_btn)

        register_btn = Button(text='📱 Register\nDevice')
        register_btn.bind(on_press=self.register_device)
        button_layout.add_widget(register_btn)

        sync_btn = Button(text='🔄 Sync\nNow')
        sync_btn.bind(on_press=self.sync_now)
        button_layout.add_widget(sync_btn)

        # Additional debug buttons
        test_btn = Button(text='🌐 Test\nConnectivity')
        test_btn.bind(on_press=self.test_connectivity)
        button_layout.add_widget(test_btn)

        debug_btn = Button(text='🐛 Show\nDebug Info')
        debug_btn.bind(on_press=self.show_debug_info)
        button_layout.add_widget(debug_btn)

        clear_btn = Button(text='🧹 Clear\nLogs')
        clear_btn.bind(on_press=self.clear_logs)
        button_layout.add_widget(clear_btn)

        main_layout.add_widget(button_layout)

        # Start/Stop button
        self.start_stop_btn = Button(text='▶️ Start Monitoring', size_hint_y=None, height=50, font_size='16sp')
        self.start_stop_btn.bind(on_press=self.toggle_monitoring)
        main_layout.add_widget(self.start_stop_btn)

        # Log display
        self.log_display = Label(
            text=f'📱 Call Log Monitor v2.1 Started\nDevice ID: {self.monitor.device_id}\nDebug Mode: ON\nReady to connect...',
            text_size=(None, None), halign='left', valign='top'
        )
        scroll = ScrollView()
        scroll.add_widget(self.log_display)
        main_layout.add_widget(scroll)

        # Schedule UI updates and auto-detect
        Clock.schedule_interval(self.update_ui, 3)
        Clock.schedule_once(lambda dt: self.detect_backend(None), 2)
        return main_layout

    def on_user_id_change(self, instance, value):
        self.monitor.user_id = value.strip()
        self.monitor._save_settings()

    def on_debug_toggle(self, instance, value):
        self.monitor.debug_mode = value
        self.log_message(f"Debug mode: {'ON' if value else 'OFF'}")

    def test_connectivity(self, instance):
        self.log_message("🌐 Testing connectivity...")
        threading.Thread(target=self._test_connectivity_thread, daemon=True).start()

    def _test_connectivity_thread(self):
        results = self.monitor.test_connectivity()
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_count = len(results)
        message = f"Connectivity: {success_count}/{total_count} tests passed"
        Clock.schedule_once(lambda dt: self.log_message(message), 0)

    def show_debug_info(self, instance):
        """Show detailed debug information"""
        debug_info = f"""
DEBUG INFO:
Device ID: {self.monitor.device_id}
User ID: {self.monitor.user_id}
Backend URL: {self.monitor.api_base_url}
Registered: {self.monitor.device_registered}
Android Available: {ANDROID_AVAILABLE}
Monitor Running: {self.is_running}
        """.strip()
        
        popup = Popup(
            title='Debug Information',
            content=Label(text=debug_info, text_size=(400, None)),
            size_hint=(0.9, 0.7)
        )
        popup.open()

    def clear_logs(self, instance):
        self.log_display.text = "📱 Logs cleared"

    def detect_backend(self, instance):
        self.log_message("🔍 Detecting backend...")
        threading.Thread(target=self._detect_backend_thread, daemon=True).start()

    def _detect_backend_thread(self):
        success = self.monitor.detect_backend_url()
        message = "✅ Backend detected!" if success else "❌ No backend found"
        Clock.schedule_once(lambda dt: self._update_backend_result(success, message), 0)

    def _update_backend_result(self, success, message):
        self.log_message(message)
        self.api_url_display.text = self.monitor.api_base_url or 'Not detected'

    def register_device(self, instance):
        if not self.monitor.user_id.strip():
            self.show_popup("Error", "Please enter User ID")
            return
        if not self.monitor.api_base_url:
            self.show_popup("Error", "Please detect backend first")
            return
        self.log_message("📱 Registering device...")
        threading.Thread(target=self._register_thread, daemon=True).start()

    def _register_thread(self):
        success = self.monitor.register_device()
        message = "✅ Device registered!" if success else "❌ Registration failed"
        Clock.schedule_once(lambda dt: self.log_message(message), 0)

    def sync_now(self, instance):
        self.log_message("🔄 Starting sync...")
        threading.Thread(target=self._sync_thread, daemon=True).start()

    def _sync_thread(self):
        success = self.monitor.sync_call_logs()
        message = "✅ Sync completed!" if success else "❌ Sync failed"
        Clock.schedule_once(lambda dt: self.log_message(message), 0)

    def toggle_monitoring(self, instance):
        if self.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()

    def start_monitoring(self):
        if not self.monitor.user_id.strip():
            self.show_popup("Error", "Please enter User ID")
            return
        if not self.monitor.device_registered:
            self.show_popup("Error", "Please register device first")
            return

        self.is_running = True
        self.start_stop_btn.text = '⏹️ Stop Monitoring'
        self.log_message("▶️ Monitoring started")
        threading.Thread(target=self._monitoring_loop, daemon=True).start()

    def stop_monitoring(self):
        self.is_running = False
        self.start_stop_btn.text = '▶️ Start Monitoring'
        self.log_message("⏹️ Monitoring stopped")

    def _monitoring_loop(self):
        while self.is_running:
            try:
                # Send heartbeat
                heartbeat_success = self.monitor.send_heartbeat()
                if not heartbeat_success:
                    Clock.schedule_once(lambda dt: self.log_message("❌ Heartbeat failed"), 0)

                # Auto-sync if enabled
                if self.auto_sync_switch.active:
                    success = self.monitor.sync_call_logs()
                    status = "✅" if success else "❌"
                    Clock.schedule_once(lambda dt: self.log_message(f"{status} Auto-sync"), 0)

                time.sleep(300)  # 5 minute intervals
            except Exception as e:
                Logger.error(f"Monitoring error: {e}")
                Clock.schedule_once(lambda dt: self.log_message(f"❌ Monitor error: {str(e)[:50]}"), 0)
                time.sleep(60)

    def update_ui(self, dt):
        """Update UI status"""
        status = '✅ Registered' if self.monitor.device_registered else '❌ Not Registered'
        if self.is_running:
            status += ' (Active)'
        self.status_label.text = status

    def log_message(self, message):
        """Add timestamped message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"

        lines = self.log_display.text.split('\n')
        lines.append(log_entry)
        if len(lines) > 15:
            lines = lines[-15:]

        self.log_display.text = '\n'.join(lines)
        Logger.info(message)

    def show_popup(self, title, message):
        """Show popup dialog"""
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()
>>>>>>> b32e8134d3447a7619a62fdb76754082488545b5

Device Info:
• Model: {device_info.get('model', 'Unknown')}
• OS: {device_info.get('os', 'Unknown')} {device_info.get('osVersion', '')}
• Platform: {device_info.get('platform', 'Unknown')}

API URLs to test:
{chr(10).join(['• ' + url for url in api_urls[:3]])}

Status: Ready to initialize...
"""
        return info_text
    
    def update_status(self, message: str, progress: int = None):
        """Update status label and progress bar"""
        Logger.info(f"[Status] {message}")
        def update_ui(dt):
            self.status_label.text = message
            if progress is not None:
                self.progress_bar.value = progress
        Clock.schedule_once(update_ui, 0)
    
    def update_info_display(self, additional_info: str = None):
        """Update the info display"""
        config = self.backend_detector.get_saved_config()
        
        base_info = self.get_initial_info()
        
        if config:
            config_info = f"""
Current Configuration:
• API URL: {config.get('api_url', 'Not set')}
• User ID: {config.get('user_id', 'Not set')[:12]}...
• Device ID: {config.get('device_id', 'Not set')[:16]}...
• Registered: {config.get('device_registered', 'No')}
• Last Registration: {time.ctime(int(config.get('last_registration', 0))) if config.get('last_registration') else 'Never'}
"""
            base_info += config_info
        
        if additional_info:
            base_info += f"\n{additional_info}"
        
        def update_ui(dt):
            self.info_label.text = base_info
            self.info_label.text_size = (Window.width - 60, None)
        Clock.schedule_once(update_ui, 0)
    
    def auto_initialize(self, dt):
        """Auto-initialize the backend on app start"""
        self.update_status("🚀 Auto-initializing...", 10)
        
        # Request permissions first on Android
        if is_android():
            self.call_log_manager.request_permissions()
        
        # Start initialization in a separate thread
        threading.Thread(target=self.do_initialize, daemon=True).start()
    
    def initialize_backend(self, instance):
        """Initialize backend connection (button handler)"""
        self.init_button.disabled = True
        threading.Thread(target=self.do_initialize, daemon=True).start()
    
    def do_initialize(self):
        """Perform initialization in background thread"""
        try:
            self.update_status("🔍 Detecting backend...", 20)
            self.update_info_display()
            
            self.update_status("🌐 Testing connectivity...", 30)
            
            # Test connectivity first
            if not self.backend_detector.test_connectivity():
                self.update_status("❌ No internet connectivity", 0)
                self.show_error_popup("No Internet", "Please check your internet connection and try again.")
                Clock.schedule_once(lambda dt: setattr(self.init_button, 'disabled', False), 0)
                return
            
            self.update_status("🔍 Detecting backend servers...", 50)
            
            # Detect backend
            self.api_url = self.backend_detector.detect_backend()
            if not self.api_url:
                self.update_status("❌ Backend detection failed", 0)
                self.show_error_popup("Backend Error", 
                    "Could not connect to any backend servers.\n\n"
                    "Please check:\n"
                    "• Internet connection\n"
                    "• Server availability\n"
                    "• Try the manual URL option")
                Clock.schedule_once(lambda dt: setattr(self.init_button, 'disabled', False), 0)
                return
            
            self.update_status("📱 Registering device...", 70)
            
            # Register device
            if not self.backend_detector.register_device(self.api_url):
                self.update_status("❌ Device registration failed", 0)
                self.show_error_popup("Registration Error", 
                    f"Failed to register device with backend.\n\n"
                    f"Backend URL: {self.api_url}\n"
                    f"Please check server logs or try manual URL.")
                Clock.schedule_once(lambda dt: setattr(self.init_button, 'disabled', False), 0)
                return
            
            # Success!
            self.update_status("✅ Initialization successful!", 100)
            
            # Load configuration
            config = self.backend_detector.get_saved_config()
            if config:
                self.user_id = config['user_id']
                self.device_id = config['device_id']
                self.is_initialized = True
                
                # Enable sync button
                Clock.schedule_once(lambda dt: setattr(self.sync_button, 'disabled', False), 0)
                
                self.update_info_display("🎉 Device successfully registered and ready!")
                
                # Show success popup
                self.show_success_popup("Success!", 
                    f"✅ Backend connected: {self.api_url}\n"
                    f"📱 Device registered successfully\n"
                    f"🔄 Ready to sync call logs!")
            
        except Exception as e:
            Logger.error(f"Initialization error: {e}")
            self.update_status(f"❌ Initialization error: {str(e)}", 0)
            self.show_error_popup("Initialization Error", f"An error occurred during initialization:\n\n{str(e)}")
        
        finally:
            Clock.schedule_once(lambda dt: setattr(self.init_button, 'disabled', False), 0)
    
    def test_connectivity(self, instance):
        """Test connectivity (button handler)"""
        self.test_button.disabled = True
        threading.Thread(target=self.do_test_connectivity, daemon=True).start()
    
    def do_test_connectivity(self):
        """Test connectivity in background thread"""
        try:
            self.update_status("🧪 Testing connectivity...", 20)
            
            if self.backend_detector.test_connectivity():
                self.update_status("✅ Connectivity test passed", 100)
                self.show_success_popup("Connectivity Test", "✅ Internet connectivity is working!")
            else:
                self.update_status("❌ Connectivity test failed", 0)
                self.show_error_popup("Connectivity Test", "❌ Internet connectivity issues detected.")
        
        except Exception as e:
            Logger.error(f"Connectivity test error: {e}")
            self.update_status(f"❌ Connectivity test error", 0)
            self.show_error_popup("Test Error", f"Connectivity test failed:\n\n{str(e)}")
        
        finally:
            Clock.schedule_once(lambda dt: setattr(self.test_button, 'disabled', False), 0)
    
    def test_manual_url(self, instance):
        """Test manually entered URL"""
        manual_url = self.manual_url_input.text.strip()
        if not manual_url:
            self.show_error_popup("Invalid URL", "Please enter a valid URL")
            return
        
        instance.disabled = True
        threading.Thread(target=lambda: self.do_test_manual_url(manual_url, instance), daemon=True).start()
    
    def do_test_manual_url(self, test_url: str, button_instance):
        """Test manual URL in background thread"""
        try:
            self.update_status(f"🧪 Testing manual URL...", 50)
            
            is_available, api_info = self.backend_detector.test_backend_url(test_url)
            
            if is_available:
                self.update_status("✅ Manual URL test passed", 100)
                
                # Ask if user wants to use this URL
                def use_url(dt):
                    popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)
                    popup_layout.add_widget(Label(text=f"✅ URL is working!\n\n{test_url}\n\nUse this URL for backend?", 
                                                text_size=(300, None), halign='center'))
                    
                    button_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=0.3)
                    
                    yes_button = Button(text='Yes, Use This URL', background_color=(0.2, 0.8, 0.2, 1))
                    no_button = Button(text='Cancel', background_color=(0.8, 0.2, 0.2, 1))
                    
                    button_layout.add_widget(yes_button)
                    button_layout.add_widget(no_button)
                    popup_layout.add_widget(button_layout)
                    
                    popup = Popup(title='Manual URL Test Success', content=popup_layout, size_hint=(0.9, 0.4))
                    
                    def use_manual_url(btn):
                        popup.dismiss()
                        # Save manual URL and register
                        StorageManager.save('api_url', test_url)
                        self.api_url = test_url
                        threading.Thread(target=lambda: self.backend_detector.register_device(test_url), daemon=True).start()
                    
                    def cancel(btn):
                        popup.dismiss()
                    
                    yes_button.bind(on_press=use_manual_url)
                    no_button.bind(on_press=cancel)
                    popup.open()
                
                Clock.schedule_once(use_url, 0)
                
            else:
                self.update_status("❌ Manual URL test failed", 0)
                self.show_error_popup("Manual URL Test", f"❌ URL is not responding or not our API:\n\n{test_url}")
        
        except Exception as e:
            Logger.error(f"Manual URL test error: {e}")
            self.update_status("❌ Manual URL test error", 0)
            self.show_error_popup("Test Error", f"Manual URL test failed:\n\n{str(e)}")
        
        finally:
            Clock.schedule_once(lambda dt: setattr(button_instance, 'disabled', False), 0)
    
    def sync_call_logs(self, instance):
        """Sync call logs to backend"""
        if not self.is_initialized or not self.api_url:
            self.show_error_popup("Not Initialized", "Please initialize backend connection first.")
            return
        
        self.sync_button.disabled = True
        threading.Thread(target=self.do_sync_call_logs, daemon=True).start()
    
    def do_sync_call_logs(self):
        """Sync call logs in background thread"""
        try:
            self.update_status("📞 Reading call logs...", 20)
            
            # Get call logs
            call_logs = self.call_log_manager.get_call_logs(100)
            
            if not call_logs:
                self.update_status("⚠️ No call logs found", 50)
                self.show_error_popup("No Call Logs", "No call logs found or permission denied.")
                return
            
            self.update_status(f"📤 Uploading {len(call_logs)} call logs...", 60)
            
            # Prepare sync data
            sync_data = {
                'deviceId': self.device_id,
                'userId': self.user_id,
                'callLogs': call_logs,
                'timestamp': int(time.time())
            }
            
            # Send to backend
            import requests
            from urllib.parse import urljoin
            
            sync_url = urljoin(self.api_url.rstrip('/') + '/', 'calllogs/sync')
            
            response = requests.post(
                sync_url,
                json=sync_data,
                timeout=30,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': f'KortahunUnited/2.0.0 ({get_platform_name()})'
                }
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('success'):
                    self.update_status(f"✅ Synced {len(call_logs)} call logs", 100)
                    self.show_success_popup("Sync Success", 
                        f"✅ Successfully synced {len(call_logs)} call logs!\n\n"
                        f"Uploaded at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Save last sync time
                    StorageManager.save('last_sync', str(int(time.time())))
                    self.update_info_display(f"Last sync: {len(call_logs)} logs at {time.strftime('%H:%M:%S')}")
                else:
                    raise Exception(response_data.get('message', 'Sync failed'))
            else:
                raise Exception(f"Server error: {response.status_code}")
        
        except Exception as e:
            Logger.error(f"Sync error: {e}")
            self.update_status("❌ Call log sync failed", 0)
            self.show_error_popup("Sync Error", f"Failed to sync call logs:\n\n{str(e)}")
        
        finally:
            Clock.schedule_once(lambda dt: setattr(self.sync_button, 'disabled', False), 0)
    
    def show_error_popup(self, title: str, message: str):
        """Show error popup"""
        def show_popup(dt):
            popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)
            popup_layout.add_widget(Label(text=message, text_size=(300, None), halign='center'))
            
            close_button = Button(text='Close', size_hint_y=0.3, background_color=(0.8, 0.2, 0.2, 1))
            popup_layout.add_widget(close_button)
            
            popup = Popup(title=title, content=popup_layout, size_hint=(0.9, 0.5))
            close_button.bind(on_press=popup.dismiss)
            popup.open()
        
        Clock.schedule_once(show_popup, 0)
    
    def show_success_popup(self, title: str, message: str):
        """Show success popup"""
        def show_popup(dt):
            popup_layout = BoxLayout(orientation='vertical', spacing=10, padding=20)
            popup_layout.add_widget(Label(text=message, text_size=(300, None), halign='center'))
            
            close_button = Button(text='Great!', size_hint_y=0.3, background_color=(0.2, 0.8, 0.2, 1))
            popup_layout.add_widget(close_button)
            
            popup = Popup(title=title, content=popup_layout, size_hint=(0.9, 0.5))
            close_button.bind(on_press=popup.dismiss)
            popup.open()
        
        Clock.schedule_once(show_popup, 0)

# Main app execution
def main():
    """Main application entry point"""
    try:
        # Set up logging
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        Logger.info("🚀 Starting Kortahun United Call Logger")
        Logger.info(f"Platform: {get_platform_name()}")
        Logger.info(f"Android: {is_android()}")
        Logger.info(f"Environment: {'Development' if AppConfig.is_development_environment() else 'Production'}")
        
        # Create and run app
        app = KortahunApp()
        app.run()
        
    except Exception as e:
        Logger.error(f"App startup error: {e}")
        print(f"❌ Failed to start app: {e}")
        sys.exit(1)

if __name__ == '__main__':
<<<<<<< HEAD
    main()
=======
    CallLogApp().run()
>>>>>>> b32e8134d3447a7619a62fdb76754082488545b5
