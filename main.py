#!/usr/bin/env python3
"""
Android Call Log Monitor
Captures call logs from Android device and sends them to web platform
"""

import json
import time
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.storage.jsonstore import JsonStore

# Android-specific imports
try:
    from android.permissions import request_permissions, Permission
    from android.runnable import run_on_ui_thread
    from jnius import autoclass, cast
    from android.broadcast import BroadcastReceiver
    ANDROID_AVAILABLE = True
except ImportError:
    ANDROID_AVAILABLE = False
    Logger.info("Android imports not available - running in desktop mode")

class CallLogMonitor:
    def __init__(self):
        self.api_base_url = "https://kortahununited.onrender.com/api"
        self.device_id = self._get_device_id()
        self.user_id = ""
        self.is_monitoring = False
        self.last_sync_time = None
        self.call_cache = []
        self.device_registered = False
        
        # Setup requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Load settings
        self.store = JsonStore('call_monitor_settings.json')
        self._load_settings()
        
    def _get_device_id(self) -> str:
        """Generate or retrieve device ID"""
        if ANDROID_AVAILABLE:
            try:
                # Try to get Android ID
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                context = PythonActivity.mActivity
                resolver = context.getContentResolver()
                Settings = autoclass('android.provider.Settings$Secure')
                android_id = Settings.getString(resolver, 'android_id')
                return f"android_{android_id}"
            except Exception as e:
                Logger.error(f"Error getting Android ID: {e}")
        
        # Fallback to UUID
        return f"device_{str(uuid.uuid4())[:8]}"
    
    def _load_settings(self):
        """Load settings from storage"""
        try:
            if self.store.exists('user_id'):
                self.user_id = self.store.get('user_id')['value']
            if self.store.exists('api_url'):
                self.api_base_url = self.store.get('api_url')['value']
            if self.store.exists('last_sync'):
                self.last_sync_time = self.store.get('last_sync')['value']
        except Exception as e:
            Logger.error(f"Error loading settings: {e}")
    
    def _save_settings(self):
        """Save settings to storage"""
        try:
            self.store.put('user_id', value=self.user_id)
            self.store.put('api_url', value=self.api_base_url)
            if self.last_sync_time:
                self.store.put('last_sync', value=self.last_sync_time)
        except Exception as e:
            Logger.error(f"Error saving settings: {e}")
    
    def get_device_info(self) -> Dict:
        """Get device information"""
        device_info = {
            'model': 'Unknown',
            'manufacturer': 'Unknown',
            'os': 'Android',
            'osVersion': 'Unknown',
            'appVersion': '1.0.0'
        }
        
        if ANDROID_AVAILABLE:
            try:
                Build = autoclass('android.os.Build')
                device_info.update({
                    'model': Build.MODEL,
                    'manufacturer': Build.MANUFACTURER,
                    'osVersion': Build.VERSION.RELEASE,
                })
            except Exception as e:
                Logger.error(f"Error getting device info: {e}")
        
        return device_info
    
    def request_permissions(self) -> bool:
        """Request necessary permissions"""
        if not ANDROID_AVAILABLE:
            return True
        
        try:
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ]
            
            request_permissions(permissions)
            Logger.info("Permissions requested")
            return True
        except Exception as e:
            Logger.error(f"Error requesting permissions: {e}")
            return False
    
    def register_device(self) -> bool:
        """Register device with the backend"""
        try:
            device_info = self.get_device_info()
            
            payload = {
                'deviceId': self.device_id,
                'userId': self.user_id,
                'deviceInfo': device_info,
                'permissions': {
                    'readCallLog': True,
                    'readPhoneState': True,
                    'readContacts': True
                }
            }
            
            response = self.session.post(
                f"{self.api_base_url}/devices/register",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.device_registered = True
                    Logger.info("Device registered successfully")
                    return True
            
            Logger.error(f"Device registration failed: {response.text}")
            return False
            
        except Exception as e:
            Logger.error(f"Error registering device: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat to keep device active"""
        try:
            payload = {'deviceId': self.device_id}
            
            response = self.session.post(
                f"{self.api_base_url}/devices/heartbeat",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            Logger.error(f"Error sending heartbeat: {e}")
            return False
    
    def get_call_logs(self) -> List[Dict]:
        """Get call logs from Android device"""
        if not ANDROID_AVAILABLE:
            # Return dummy data for testing
            return [{
                'number': '+1234567890',
                'name': 'Test Contact',
                'type': 'incoming',
                'timestamp': datetime.now().isoformat(),
                'duration': 120,
                'date': datetime.now().isoformat()
            }]
        
        try:
            # Get call log cursor
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            resolver = context.getContentResolver()
            
            # Call log columns
            CallLog = autoclass('android.provider.CallLog$Calls')
            
            # Query call log
            cursor = resolver.query(
                CallLog.CONTENT_URI,
                None,  # All columns
                None,  # No selection
                None,  # No selection args
                f"{CallLog.DATE} DESC"  # Order by date descending
            )
            
            calls = []
            if cursor and cursor.moveToFirst():
                while True:
                    try:
                        # Get call details
                        number = cursor.getString(cursor.getColumnIndex(CallLog.NUMBER)) or "Unknown"
                        name = cursor.getString(cursor.getColumnIndex(CallLog.CACHED_NAME)) or "Unknown"
                        call_type = cursor.getInt(cursor.getColumnIndex(CallLog.TYPE))
                        duration = cursor.getInt(cursor.getColumnIndex(CallLog.DURATION))
                        date = cursor.getLong(cursor.getColumnIndex(CallLog.DATE))
                        
                        # Convert call type to string
                        type_map = {
                            1: 'incoming',
                            2: 'outgoing',
                            3: 'missed',
                            4: 'voicemail',
                            5: 'rejected',
                            6: 'blocked'
                        }
                        
                        call_type_str = type_map.get(call_type, 'unknown')
                        
                        # Convert timestamp
                        timestamp = datetime.fromtimestamp(date / 1000).isoformat()
                        
                        call_data = {
                            'number': number,
                            'name': name,
                            'type': call_type_str,
                            'duration': duration,
                            'timestamp': timestamp,
                            'date': timestamp,
                            'deviceId': self.device_id
                        }
                        
                        calls.append(call_data)
                        
                    except Exception as e:
                        Logger.error(f"Error processing call log entry: {e}")
                        continue
                    
                    if not cursor.moveToNext():
                        break
            
            if cursor:
                cursor.close()
            
            Logger.info(f"Retrieved {len(calls)} call log entries")
            return calls
            
        except Exception as e:
            Logger.error(f"Error getting call logs: {e}")
            return []
    
    def filter_new_calls(self, calls: List[Dict]) -> List[Dict]:
        """Filter calls that haven't been synced yet"""
        if not self.last_sync_time:
            return calls
        
        try:
            last_sync = datetime.fromisoformat(self.last_sync_time)
            new_calls = []
            
            for call in calls:
                call_time = datetime.fromisoformat(call['timestamp'])
                if call_time > last_sync:
                    new_calls.append(call)
            
            Logger.info(f"Found {len(new_calls)} new calls since last sync")
            return new_calls
            
        except Exception as e:
            Logger.error(f"Error filtering new calls: {e}")
            return calls
    
    def send_call_logs(self, calls: List[Dict]) -> bool:
        """Send call logs to the backend"""
        if not calls:
            return True
        
        try:
            payload = {
                'deviceId': self.device_id,
                'userId': self.user_id,
                'calls': calls
            }
            
            response = self.session.post(
                f"{self.api_base_url}/calls/sync",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.last_sync_time = datetime.now().isoformat()
                    self._save_settings()
                    Logger.info(f"Successfully synced {len(calls)} calls")
                    return True
            
            Logger.error(f"Failed to sync calls: {response.text}")
            return False
            
        except Exception as e:
            Logger.error(f"Error sending call logs: {e}")
            return False
    
    def sync_call_logs(self) -> bool:
        """Main sync function"""
        try:
            Logger.info("Starting call log sync...")
            
            # Get all call logs
            all_calls = self.get_call_logs()
            
            # Filter new calls
            new_calls = self.filter_new_calls(all_calls)
            
            if not new_calls:
                Logger.info("No new calls to sync")
                return True
            
            # Send to backend
            success = self.send_call_logs(new_calls)
            
            if success:
                Logger.info("Call log sync completed successfully")
            else:
                Logger.error("Call log sync failed")
            
            return success
            
        except Exception as e:
            Logger.error(f"Error in sync_call_logs: {e}")
            return False


class CallLogApp(App):
    def __init__(self):
        super().__init__()
        self.monitor = CallLogMonitor()
        self.monitoring_thread = None
        self.heartbeat_thread = None
        self.is_running = False
        
    def build(self):
        """Build the UI"""
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Call Log Monitor',
            size_hint_y=None,
            height=50,
            font_size='24sp'
        )
        main_layout.add_widget(title)
        
        # Settings section
        settings_layout = GridLayout(cols=2, size_hint_y=None, height=200, spacing=10)
        
        # User ID input
        settings_layout.add_widget(Label(text='User ID:', size_hint_x=0.3))
        self.user_id_input = TextInput(
            text=self.monitor.user_id,
            multiline=False,
            size_hint_x=0.7
        )
        self.user_id_input.bind(text=self.on_user_id_change)
        settings_layout.add_widget(self.user_id_input)
        
        # API URL input
        settings_layout.add_widget(Label(text='API URL:', size_hint_x=0.3))
        self.api_url_input = TextInput(
            text=self.monitor.api_base_url,
            multiline=False,
            size_hint_x=0.7
        )
        self.api_url_input.bind(text=self.on_api_url_change)
        settings_layout.add_widget(self.api_url_input)
        
        # Auto-sync switch
        settings_layout.add_widget(Label(text='Auto Sync:', size_hint_x=0.3))
        self.auto_sync_switch = Switch(active=True, size_hint_x=0.7)
        settings_layout.add_widget(self.auto_sync_switch)
        
        # Device ID display
        settings_layout.add_widget(Label(text='Device ID:', size_hint_x=0.3))
        settings_layout.add_widget(Label(text=self.monitor.device_id, size_hint_x=0.7))
        
        main_layout.add_widget(settings_layout)
        
        # Control buttons
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        self.permissions_btn = Button(text='Request Permissions')
        self.permissions_btn.bind(on_press=self.request_permissions)
        button_layout.add_widget(self.permissions_btn)
        
        self.register_btn = Button(text='Register Device')
        self.register_btn.bind(on_press=self.register_device)
        button_layout.add_widget(self.register_btn)
        
        self.sync_btn = Button(text='Sync Now')
        self.sync_btn.bind(on_press=self.sync_now)
        button_layout.add_widget(self.sync_btn)
        
        main_layout.add_widget(button_layout)
        
        # Start/Stop button
        self.start_stop_btn = Button(
            text='Start Monitoring',
            size_hint_y=None,
            height=50
        )
        self.start_stop_btn.bind(on_press=self.toggle_monitoring)
        main_layout.add_widget(self.start_stop_btn)
        
        # Status display
        self.status_label = Label(
            text='Status: Stopped',
            size_hint_y=None,
            height=30
        )
        main_layout.add_widget(self.status_label)
        
        # Log display
        log_layout = BoxLayout(orientation='vertical', spacing=5)
        log_layout.add_widget(Label(text='Log:', size_hint_y=None, height=30))
        
        self.log_display = Label(
            text='App started. Configure settings and request permissions.',
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        
        scroll = ScrollView()
        scroll.add_widget(self.log_display)
        log_layout.add_widget(scroll)
        
        main_layout.add_widget(log_layout)
        
        # Schedule status updates
        Clock.schedule_interval(self.update_status, 1)
        
        return main_layout
    
    def on_user_id_change(self, instance, value):
        """Handle user ID change"""
        self.monitor.user_id = value
        self.monitor._save_settings()
    
    def on_api_url_change(self, instance, value):
        """Handle API URL change"""
        self.monitor.api_base_url = value
        self.monitor._save_settings()
    
    def request_permissions(self, instance):
        """Request Android permissions"""
        self.log_message("Requesting permissions...")
        success = self.monitor.request_permissions()
        if success:
            self.log_message("Permissions requested successfully")
        else:
            self.log_message("Failed to request permissions")
    
    def register_device(self, instance):
        """Register device with backend"""
        if not self.monitor.user_id:
            self.show_popup("Error", "Please enter a User ID first")
            return
        
        self.log_message("Registering device...")
        success = self.monitor.register_device()
        if success:
            self.log_message("Device registered successfully")
        else:
            self.log_message("Failed to register device")
    
    def sync_now(self, instance):
        """Trigger immediate sync"""
        self.log_message("Starting manual sync...")
        threading.Thread(target=self._sync_thread, daemon=True).start()
    
    def _sync_thread(self):
        """Sync in background thread"""
        success = self.monitor.sync_call_logs()
        message = "Sync completed successfully" if success else "Sync failed"
        Clock.schedule_once(lambda dt: self.log_message(message), 0)
    
    def toggle_monitoring(self, instance):
        """Start/stop monitoring"""
        if self.is_running:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        """Start background monitoring"""
        if not self.monitor.user_id:
            self.show_popup("Error", "Please enter a User ID first")
            return
        
        if not self.monitor.device_registered:
            self.show_popup("Error", "Please register device first")
            return
        
        self.is_running = True
        self.start_stop_btn.text = 'Stop Monitoring'
        self.log_message("Starting monitoring...")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.is_running = False
        self.start_stop_btn.text = 'Start Monitoring'
        self.log_message("Monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                if self.auto_sync_switch.active:
                    self.monitor.sync_call_logs()
                time.sleep(300)  # 5 minutes
            except Exception as e:
                Logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _heartbeat_loop(self):
        """Heartbeat loop to keep device active"""
        while self.is_running:
            try:
                self.monitor.send_heartbeat()
                time.sleep(60)  # 1 minute
            except Exception as e:
                Logger.error(f"Error in heartbeat loop: {e}")
                time.sleep(60)
    
    def update_status(self, dt):
        """Update status display"""
        if self.is_running:
            self.status_label.text = f'Status: Running (Device: {self.monitor.device_id})'
        else:
            self.status_label.text = 'Status: Stopped'
    
    def log_message(self, message):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        current_text = self.log_display.text
        new_text = f"{current_text}\n{log_entry}"
        
        # Keep only last 20 lines
        lines = new_text.split('\n')
        if len(lines) > 20:
            lines = lines[-20:]
        
        self.log_display.text = '\n'.join(lines)
        Logger.info(message)
    
    def show_popup(self, title, message):
        """Show popup message"""
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        )
        popup.open()


if __name__ == '__main__':
    CallLogApp().run()