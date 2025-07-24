#!/usr/bin/env python3
"""
Call Center Mobile Application
Real-time call log synchronization with backend
"""

import os
import json
import time
import threading
from datetime import datetime
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock, mainthread
from kivy.utils import platform

# Platform-specific imports
if platform == 'android':
    from android.permissions import request_permissions, Permission, check_permission
    from android.storage import primary_external_storage_path
    from jnius import autoclass, cast
    
    # Android Java classes
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')
    CallLog = autoclass('android.provider.CallLog')
    ContentResolver = autoclass('android.content.ContentResolver')
    Uri = autoclass('android.net.Uri')
    Cursor = autoclass('android.database.Cursor')


class CallLogReader:
    """Handles reading call logs from Android system"""
    
    def __init__(self):
        self.context = None
        self.content_resolver = None
        if platform == 'android':
            self.context = PythonActivity.mActivity
            self.content_resolver = self.context.getContentResolver()
    
    def request_permissions(self):
        """Request necessary permissions for call log access"""
        if platform == 'android':
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ]
            request_permissions(permissions)
            return True
        return False
    
    def check_permissions(self):
        """Check if all required permissions are granted"""
        if platform == 'android':
            required_perms = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS
            ]
            return all(check_permission(perm) for perm in required_perms)
        return True  # For desktop testing
    
    def get_call_logs(self, limit=50):
        """Fetch call logs from Android system"""
        if platform != 'android':
            # Mock data for desktop testing
            return self._get_mock_call_logs()
        
        if not self.check_permissions():
            return []
        
        try:
            uri = CallLog.Calls.CONTENT_URI
            projection = [
                CallLog.Calls._ID,
                CallLog.Calls.NUMBER,
                CallLog.Calls.CACHED_NAME,
                CallLog.Calls.TYPE,
                CallLog.Calls.DATE,
                CallLog.Calls.DURATION
            ]
            
            cursor = self.content_resolver.query(
                uri, projection, None, None, 
                f"{CallLog.Calls.DATE} DESC LIMIT {limit}"
            )
            
            calls = []
            if cursor and cursor.moveToFirst():
                while not cursor.isAfterLast():
                    call_data = {
                        'callId': f"android-{cursor.getString(0)}-{int(time.time())}",
                        'phoneNumber': cursor.getString(1) or 'Unknown',
                        'contactName': cursor.getString(2),
                        'type': self._get_call_type(cursor.getInt(3)),
                        'timestamp': datetime.fromtimestamp(cursor.getLong(4) / 1000).isoformat(),
                        'duration': cursor.getInt(5)
                    }
                    calls.append(call_data)
                    cursor.moveToNext()
                
                cursor.close()
            
            return calls
            
        except Exception as e:
            print(f"Error reading call logs: {e}")
            return []
    
    def _get_call_type(self, call_type):
        """Convert Android call type to our format"""
        type_map = {
            1: 'incoming',   # INCOMING_TYPE
            2: 'outgoing',   # OUTGOING_TYPE
            3: 'missed',     # MISSED_TYPE
            4: 'voicemail',  # VOICEMAIL_TYPE
            5: 'rejected',   # REJECTED_TYPE
            6: 'blocked'     # BLOCKED_TYPE
        }
        return type_map.get(call_type, 'unknown')
    
    def _get_mock_call_logs(self):
        """Mock call logs for desktop testing"""
        import random
        mock_calls = []
        contacts = ['John Doe', 'Jane Smith', 'Mike Johnson', 'Sarah Williams']
        numbers = ['+1234567890', '+9876543210', '+1122334455', '+5556667777']
        types = ['incoming', 'outgoing', 'missed']
        
        for i in range(10):
            mock_calls.append({
                'callId': f"mock-{i}-{int(time.time())}",
                'phoneNumber': random.choice(numbers),
                'contactName': random.choice(contacts) if random.random() > 0.3 else None,
                'type': random.choice(types),
                'timestamp': datetime.now().isoformat(),
                'duration': random.randint(0, 300)
            })
        
        return mock_calls


class BackendSync:
    """Handles synchronization with backend API"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.device_id = f"android-{int(time.time())}"
        self.user_id = "12345"
        self.registered = False
        self.session = requests.Session()
        self.session.timeout = 10
    
    def register_device(self, user_id):
        """Register device with backend"""
        self.user_id = user_id
        device_data = {
            'deviceId': self.device_id,
            'userId': self.user_id,
            'deviceInfo': {
                'model': 'Android Device',
                'manufacturer': 'Generic',
                'os': 'Android',
                'osVersion': '10.0',
                'appVersion': '1.0.0'
            },
            'permissions': {
                'readCallLog': True,
                'readPhoneState': True,
                'readContacts': True
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/devices/register",
                json=device_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                self.registered = result.get('success', False)
                return self.registered, result.get('message', 'Success')
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def sync_calls(self, calls):
        """Sync call logs with backend"""
        if not self.registered:
            return False, "Device not registered"
        
        try:
            sync_data = {
                'deviceId': self.device_id,
                'userId': self.user_id,
                'calls': calls
            }
            
            response = self.session.post(
                f"{self.base_url}/calls/sync",
                json=sync_data,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('success', False), result.get('message', 'Success')
            else:
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            return False, str(e)
    
    def ping_device(self):
        """Send ping to backend"""
        if not self.registered:
            return False, "Device not registered"
        
        try:
            response = self.session.post(
                f"{self.base_url}/devices/ping",
                json={'deviceId': self.device_id},
                headers={'Content-Type': 'application/json'}
            )
            
            return response.status_code == 200, "Ping successful"
            
        except Exception as e:
            return False, str(e)
    
    def health_check(self):
        """Check backend health"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                result = response.json()
                return True, f"Healthy (uptime: {result.get('uptime', 0):.1f}s)"
            else:
                return False, f"HTTP {response.status_code}"
        except Exception as e:
            return False, str(e)


class CallCenterApp(App):
    """Main Kivy application"""
    
    def build(self):
        self.title = "Call Center Sync"
        
        # Initialize components
        self.call_reader = CallLogReader()
        self.backend_sync = None
        self.auto_sync_running = False
        self.stats = {'sent': 0, 'success': 0, 'error': 0}
        
        # Request permissions on startup
        if platform == 'android':
            Clock.schedule_once(lambda dt: self.call_reader.request_permissions(), 1)
        
        return self.create_ui()
    
    def create_ui(self):
        """Create the user interface"""
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Header
        header = Label(
            text='📱 Call Center Sync\nReal-time Call Log Synchronization',
            size_hint_y=None, height=80,
            halign='center', text_size=(None, None)
        )
        main_layout.add_widget(header)
        
        # Device info section
        device_section = self.create_device_section()
        main_layout.add_widget(device_section)
        
        # Controls section
        controls_section = self.create_controls_section()
        main_layout.add_widget(controls_section)
        
        # Stats section
        stats_section = self.create_stats_section()
        main_layout.add_widget(stats_section)
        
        # Logs section
        logs_section = self.create_logs_section()
        main_layout.add_widget(logs_section)
        
        return main_layout
    
    def create_device_section(self):
        """Create device information section"""
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=120)
        
        title = Label(text='📱 Device Status', size_hint_y=None, height=30)
        layout.add_widget(title)
        
        info_grid = GridLayout(cols=2, size_hint_y=None, height=60)
        
        self.device_status_label = Label(text='Status: Offline')
        self.permissions_label = Label(text='Permissions: Checking...')
        
        info_grid.add_widget(self.device_status_label)
        info_grid.add_widget(self.permissions_label)
        
        layout.add_widget(info_grid)
        
        self.progress_bar = ProgressBar(max=100, size_hint_y=None, height=20)
        layout.add_widget(self.progress_bar)
        
        return layout
    
    def create_controls_section(self):
        """Create control buttons section"""
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=180)
        
        title = Label(text='🔧 Controls', size_hint_y=None, height=30)
        layout.add_widget(title)
        
        # Backend URL selector
        self.backend_spinner = Spinner(
            text='Production Backend',
            values=['Production Backend', 'Local Backend (5001)', 'Local Backend (3001)'],
            size_hint_y=None, height=40
        )
        layout.add_widget(self.backend_spinner)
        
        # User ID input
        user_layout = BoxLayout(size_hint_y=None, height=40)
        user_layout.add_widget(Label(text='User ID:', size_hint_x=0.3))
        self.user_id_input = TextInput(text='12345', multiline=False)
        user_layout.add_widget(self.user_id_input)
        layout.add_widget(user_layout)
        
        # Control buttons
        btn_layout = GridLayout(cols=2, size_hint_y=None, height=70, spacing=5)
        
        self.register_btn = Button(text='📡 Register')
        self.register_btn.bind(on_press=self.register_device)
        btn_layout.add_widget(self.register_btn)
        
        self.sync_btn = Button(text='🔄 Manual Sync')
        self.sync_btn.bind(on_press=self.manual_sync)
        btn_layout.add_widget(self.sync_btn)
        
        self.auto_sync_btn = Button(text='▶️ Start Auto Sync')
        self.auto_sync_btn.bind(on_press=self.toggle_auto_sync)
        btn_layout.add_widget(self.auto_sync_btn)
        
        health_btn = Button(text='🏥 Health Check')
        health_btn.bind(on_press=self.health_check)
        btn_layout.add_widget(health_btn)
        
        layout.add_widget(btn_layout)
        
        return layout
    
    def create_stats_section(self):
        """Create statistics section"""
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=100)
        
        title = Label(text='📊 Statistics', size_hint_y=None, height=30)
        layout.add_widget(title)
        
        stats_grid = GridLayout(cols=3, size_hint_y=None, height=70)
        
        self.sent_label = Label(text='Sent: 0')
        self.success_label = Label(text='Success: 0')
        self.error_label = Label(text='Errors: 0')
        
        stats_grid.add_widget(self.sent_label)
        stats_grid.add_widget(self.success_label)
        stats_grid.add_widget(self.error_label)
        
        layout.add_widget(stats_grid)
        
        return layout
    
    def create_logs_section(self):
        """Create logs section"""
        layout = BoxLayout(orientation='vertical')
        
        title = Label(text='📋 Activity Logs', size_hint_y=None, height=30)
        layout.add_widget(title)
        
        # Scrollable log area
        scroll = ScrollView()
        self.log_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.log_layout.bind(minimum_height=self.log_layout.setter('height'))
        scroll.add_widget(self.log_layout)
        layout.add_widget(scroll)
        
        # Clear logs button
        clear_btn = Button(text='🗑️ Clear Logs', size_hint_y=None, height=40)
        clear_btn.bind(on_press=self.clear_logs)
        layout.add_widget(clear_btn)
        
        # Initial logs
        self.add_log("🚀 Call Center Sync initialized")
        self.add_log("📱 Checking permissions...")
        
        return layout
    
    @mainthread
    def add_log(self, message, log_type='info'):
        """Add log entry to the UI"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_text = f"[{timestamp}] {message}"
        
        log_label = Label(
            text=log_text,
            text_size=(None, None),
            size_hint_y=None,
            height=30,
            halign='left'
        )
        
        self.log_layout.add_widget(log_label)
        
        # Keep only last 50 logs
        if len(self.log_layout.children) > 50:
            self.log_layout.remove_widget(self.log_layout.children[-1])
    
    def get_backend_url(self):
        """Get selected backend URL"""
        selection = self.backend_spinner.text
        if 'Local' in selection and '5001' in selection:
            return 'http://localhost:5001/api'
        elif 'Local' in selection and '3001' in selection:
            return 'http://localhost:3001/api'
        else:
            return 'https://kortahununited.onrender.com/api'
    
    def register_device(self, instance):
        """Register device with backend"""
        def register_worker():
            self.progress_bar.value = 20
            self.add_log("📡 Registering device...")
            
            backend_url = self.get_backend_url()
            self.backend_sync = BackendSync(backend_url)
            
            self.progress_bar.value = 60
            
            success, message = self.backend_sync.register_device(self.user_id_input.text)
            
            self.progress_bar.value = 100
            
            if success:
                self.device_status_label.text = 'Status: Online - Registered'
                self.add_log(f"✅ Device registered: {message}")
                
                # Start periodic ping
                Clock.schedule_interval(self.ping_device, 30)
            else:
                self.device_status_label.text = 'Status: Registration Failed'
                self.add_log(f"❌ Registration failed: {message}")
            
            Clock.schedule_once(lambda dt: setattr(self.progress_bar, 'value', 0), 2)
        
        threading.Thread(target=register_worker, daemon=True).start()
    
    def manual_sync(self, instance):
        """Manually sync call logs"""
        def sync_worker():
            if not self.backend_sync or not self.backend_sync.registered:
                self.add_log("⚠️ Device not registered")
                return
            
            self.add_log("🔄 Fetching call logs...")
            calls = self.call_reader.get_call_logs(20)
            
            if not calls:
                self.add_log("ℹ️ No new call logs found")
                return
            
            self.add_log(f"📞 Found {len(calls)} call logs, syncing...")
            self.stats['sent'] += len(calls)
            
            success, message = self.backend_sync.sync_calls(calls)
            
            if success:
                self.stats['success'] += len(calls)
                self.add_log(f"✅ Sync successful: {len(calls)} calls")
            else:
                self.stats['error'] += len(calls)
                self.add_log(f"❌ Sync failed: {message}")
            
            self.update_stats_ui()
        
        threading.Thread(target=sync_worker, daemon=True).start()
    
    def toggle_auto_sync(self, instance):
        """Toggle automatic sync"""
        if not self.auto_sync_running:
            self.auto_sync_running = True
            self.auto_sync_btn.text = '⏸️ Stop Auto Sync'
            self.add_log("▶️ Auto sync started (30s intervals)")
            Clock.schedule_interval(self.auto_sync_worker, 30)
        else:
            self.auto_sync_running = False
            self.auto_sync_btn.text = '▶️ Start Auto Sync'
            self.add_log("⏸️ Auto sync stopped")
            Clock.unschedule(self.auto_sync_worker)
    
    def auto_sync_worker(self, dt):
        """Auto sync worker function"""
        if self.backend_sync and self.backend_sync.registered:
            threading.Thread(target=self.manual_sync, args=(None,), daemon=True).start()
    
    def ping_device(self, dt=None):
        """Send ping to backend"""
        def ping_worker():
            if self.backend_sync:
                success, message = self.backend_sync.ping_device()
                if success:
                    self.device_status_label.text = 'Status: Online - Active'
                else:
                    self.device_status_label.text = 'Status: Connection Lost'
                    self.add_log(f"💓 Ping failed: {message}")
        
        threading.Thread(target=ping_worker, daemon=True).start()
    
    def health_check(self, instance):
        """Check backend health"""
        def health_worker():
            if not self.backend_sync:
                backend_url = self.get_backend_url()
                self.backend_sync = BackendSync(backend_url)
            
            success, message = self.backend_sync.health_check()
            if success:
                self.add_log(f"🏥 Backend healthy: {message}")
            else:
                self.add_log(f"❌ Health check failed: {message}")
        
        threading.Thread(target=health_worker, daemon=True).start()
    
    @mainthread
    def update_stats_ui(self):
        """Update statistics in UI"""
        self.sent_label.text = f"Sent: {self.stats['sent']}"
        self.success_label.text = f"Success: {self.stats['success']}"
        self.error_label.text = f"Errors: {self.stats['error']}"
    
    def clear_logs(self, instance):
        """Clear all logs"""
        self.log_layout.clear_widgets()
        self.add_log("🧹 Logs cleared")
    
    def on_start(self):
        """Called when app starts"""
        # Check permissions after startup
        Clock.schedule_once(self.check_permissions, 2)
    
    def check_permissions(self, dt):
        """Check if permissions are granted"""
        if self.call_reader.check_permissions():
            self.permissions_label.text = 'Permissions: ✅ Granted'
            self.add_log("✅ All permissions granted")
        else:
            self.permissions_label.text = 'Permissions: ❌ Missing'
            self.add_log("⚠️ Missing permissions - please grant in settings")


if __name__ == '__main__':
    CallCenterApp().run()