# main.py - Complete production-ready main application

import os
import sys
import json
import time
import threading
from typing import Optional

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
except ImportError:
    Logger.warning("Android modules not available - running in desktop mode")

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
        except Exception as e:
            Logger.error(f"Failed to get call logs: {e}")
            return []
    
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
    main()