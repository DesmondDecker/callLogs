# main.py - Complete production-ready main application

import os
import sys
import json
import time
import threading
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.core.window import Window
from kivy.storage.jsonstore import JsonStore

# Import our robust backend system
try:
    from config import AppConfig, StorageManager, is_android, get_platform_name
    from backend_detector import BackendDetector
except ImportError:
    Logger.warning("Config modules not available - using fallback")
    def is_android():
        return False
    def get_platform_name():
        return "Desktop"

# Call log handling imports
try:
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
except ImportError:
    Logger.warning("Android modules not available - running in desktop mode")
    ANDROID_AVAILABLE = False


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
        except Exception as e:
            Logger.error(f"Failed to get call logs: {e}")
            return []

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


if __name__ == '__main__':
    CallLogApp().run()
