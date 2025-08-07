#!/usr/bin/env python3

import os
import sys
import json
import time
import threading
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from functools import partial
import re
from urllib.parse import urlparse, parse_qs

# Android-specific imports
try:
    from android.permissions import request_permissions, Permission
    from android.storage import primary_external_storage_path
    from jnius import autoclass

    ANDROID_AVAILABLE = True

    # Android system classes
    Context = autoclass('android.content.Context')
    ContentResolver = autoclass('android.content.ContentResolver')
    CallLog = autoclass('android.provider.CallLog')
    Cursor = autoclass('android.database.Cursor')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

except ImportError:
    ANDROID_AVAILABLE = False
    print("⚠️ Android bindings not available - running in desktop mode")

# Kivy imports
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.logger import Logger
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.metrics import dp

# KivyMD imports
from kivymd.app import MDApp
from kivymd.theming import ThemableBehavior
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, ThreeLineListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.card import MDCard
from kivymd.icon_definitions import md_icons


class SimpleNotification:
    """Simple notification system to replace Snackbar"""

    @staticmethod
    def show_message(message: str, color=(0, 1, 0, 1)):
        """Show a simple message using print for now"""
        status = "SUCCESS" if color == (0, 1, 0, 1) else "INFO" if color == (0, 0, 1, 1) else "ERROR"
        print(f"[{status}] {message}")

    @staticmethod
    def show_error(message: str):
        """Show error message"""
        SimpleNotification.show_message(message, (1, 0, 0, 1))


class CallLogManager:
    """Enhanced call log manager with full Android integration"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.permissions_granted = False

    def request_permissions(self) -> bool:
        """Request necessary Android permissions"""
        if not ANDROID_AVAILABLE:
            self.logger.warning("Android not available - skipping permission request")
            return False

        try:
            # Request all necessary permissions
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE
            ]

            self.logger.info("Requesting Android permissions...")
            request_permissions(permissions)

            # Give some time for permissions to be processed
            time.sleep(2)
            self.permissions_granted = True
            return True

        except Exception as e:
            self.logger.error(f"Error requesting permissions: {e}")
            return False

    def get_call_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get call logs from Android system"""
        if not ANDROID_AVAILABLE:
            self.logger.warning("Android not available - cannot retrieve call logs")
            return []

        if not self.permissions_granted:
            self.logger.warning("Permissions not granted - cannot retrieve call logs")
            return []

        try:
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            content_resolver = context.getContentResolver()

            # Query call log
            uri = CallLog.Calls.CONTENT_URI
            projection = [
                CallLog.Calls.NUMBER,
                CallLog.Calls.CACHED_NAME,
                CallLog.Calls.TYPE,
                CallLog.Calls.DATE,
                CallLog.Calls.DURATION,
                CallLog.Calls._ID
            ]

            cursor = content_resolver.query(
                uri,
                projection,
                None,
                None,
                f"{CallLog.Calls.DATE} DESC LIMIT {limit}"
            )

            calls = []
            if cursor and cursor.moveToFirst():
                while not cursor.isAfterLast():
                    call_data = {
                        'phoneNumber': self._safe_get_string(cursor, CallLog.Calls.NUMBER) or "Unknown",
                        'contactName': self._safe_get_string(cursor, CallLog.Calls.CACHED_NAME),
                        'callType': self._get_call_type(cursor.getInt(cursor.getColumnIndex(CallLog.Calls.TYPE))),
                        'timestamp': self._format_timestamp(cursor.getLong(cursor.getColumnIndex(CallLog.Calls.DATE))),
                        'duration': cursor.getInt(cursor.getColumnIndex(CallLog.Calls.DURATION)),
                        'contactId': self._safe_get_string(cursor, CallLog.Calls._ID),
                        'simSlot': 0,  # Default for now

                        # Additional metadata
                        'deviceTimestamp': datetime.now().isoformat(),
                        'extractedAt': datetime.now().isoformat(),
                        'dataSource': 'android_call_log',
                        'appVersion': '1.0.5'
                    }
                    calls.append(call_data)
                    cursor.moveToNext()

                cursor.close()

            self.logger.info(f"Retrieved {len(calls)} call logs from Android")
            return calls

        except Exception as e:
            self.logger.error(f"Error reading call logs: {e}")
            return []

    def _safe_get_string(self, cursor, column_name: str) -> Optional[str]:
        """Safely get string value from cursor"""
        try:
            column_index = cursor.getColumnIndex(column_name)
            if column_index >= 0:
                return cursor.getString(column_index)
        except Exception:
            pass
        return None

    def _get_call_type(self, call_type: int) -> str:
        """Convert Android call type to our format"""
        type_mapping = {
            1: 'incoming',  # CallLog.Calls.INCOMING_TYPE
            2: 'outgoing',  # CallLog.Calls.OUTGOING_TYPE
            3: 'missed',  # CallLog.Calls.MISSED_TYPE
            4: 'voicemail',  # CallLog.Calls.VOICEMAIL_TYPE
            5: 'rejected',  # CallLog.Calls.REJECTED_TYPE
            6: 'blocked'  # CallLog.Calls.BLOCKED_TYPE
        }
        return type_mapping.get(call_type, 'unknown')

    def _format_timestamp(self, timestamp_ms: int) -> str:
        """Format timestamp from milliseconds to ISO format"""
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.isoformat() + 'Z'
        except Exception as e:
            self.logger.error(f"Error formatting timestamp: {e}")
            return datetime.now().isoformat() + 'Z'


class BackendAPI:
    """Enhanced backend API client with robust error handling and fixed registration"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or "https://kortahununited.onrender.com"
        self.api_base = f"{self.base_url}/api"
        self.device_id = None
        self.device_name = None
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Configure session with timeouts and retries
        self.session.timeout = 30
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Python-App': 'true',
            'X-Platform': 'Android',
            'X-Client-Type': 'python-app',
            'X-App-Version': '1.0.5',
            'User-Agent': 'KortahunUnited-PythonApp/1.0.5'
        })

    def test_connection(self) -> Dict[str, Any]:
        """Test connection to the backend"""
        try:
            self.logger.info("Testing backend connection...")
            response = self.session.get(f"{self.api_base}/health", timeout=15)

            if response.status_code == 200:
                data = response.json()
                self.logger.info("✅ Backend connection successful")
                return {
                    'success': True,
                    'status': 'connected',
                    'server_status': data.get('status', 'unknown'),
                    'python_app_ready': data.get('pythonAppReady', False),
                    'message': 'Successfully connected to Kortahun United server'
                }
            else:
                return {
                    'success': False,
                    'status': 'error',
                    'error': f'HTTP {response.status_code}',
                    'message': 'Server responded with error status'
                }

        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'status': 'connection_failed',
                'error': 'Connection failed',
                'message': 'Could not connect to server. Check internet connection.'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'status': 'timeout',
                'error': 'Request timeout',
                'message': 'Server did not respond in time'
            }
        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return {
                'success': False,
                'status': 'error',
                'error': str(e),
                'message': 'Unexpected error during connection test'
            }

    def register_device_from_qr(self, qr_data: str) -> Dict[str, Any]:
        """Fixed device registration using QR code data"""
        try:
            self.logger.info(f"Registering device from QR: {qr_data[:50]}...")

            # Validate QR data format
            if not qr_data.startswith('http'):
                return {
                    'success': False,
                    'error': 'Invalid QR code format',
                    'message': 'QR code should contain a valid URL'
                }

            # Parse the QR URL to extract the token
            parsed_url = urlparse(qr_data)

            # The URL should be like: https://domain.com/api/devices/connect/TOKEN
            path_parts = parsed_url.path.split('/')

            if len(path_parts) < 5 or path_parts[-2] != 'connect':
                return {
                    'success': False,
                    'error': 'Invalid QR URL format',
                    'message': 'QR code URL does not contain valid connection token'
                }

            connection_token = path_parts[-1]

            # Validate token format (should be 64 character hex string)
            if not re.match(r'^[a-f0-9]{64}$', connection_token, re.IGNORECASE):
                return {
                    'success': False,
                    'error': 'Invalid connection token',
                    'message': f'Token format is invalid: {connection_token[:16]}...'
                }

            self.logger.info(f"Extracted token: {connection_token[:16]}...")

            # Make request to connection URL with proper headers
            headers = {
                **self.session.headers,
                'X-Device-Token': connection_token,
                'X-Registration-Method': 'qr_code_scan'
            }

            self.logger.info(f"Making registration request to: {qr_data}")
            response = self.session.get(qr_data, headers=headers, timeout=30)

            self.logger.info(f"Registration response: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                self.logger.info(f"Registration response data: {json.dumps(data, indent=2)}")

                if data.get('success') and data.get('deviceRegistered', False):
                    # Extract device information
                    device_info = data.get('device', {})
                    self.device_id = device_info.get('deviceId')
                    self.device_name = device_info.get('deviceName', f'Device {self.device_id}')

                    # Update session headers with device ID
                    self.session.headers.update({
                        'X-Device-ID': self.device_id
                    })

                    self.logger.info(f"✅ Device registered successfully: {self.device_id}")
                    return {
                        'success': True,
                        'device_id': self.device_id,
                        'device_name': self.device_name,
                        'sync_endpoint': f"{self.api_base}/calls/sync/{self.device_id}",
                        'status_endpoint': f"{self.api_base}/devices/device/{self.device_id}",
                        'heartbeat_endpoint': f"{self.api_base}/devices/device/{self.device_id}/heartbeat",
                        'message': 'Device registered successfully!'
                    }
                else:
                    error_msg = data.get('message', 'Registration failed - unknown error')
                    return {
                        'success': False,
                        'error': 'Registration failed',
                        'message': error_msg,
                        'response_data': data
                    }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Token not found',
                    'message': 'Connection token not found or expired. Please generate a new QR code.',
                    'token': connection_token[:16] + '...'
                }
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}'

                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': error_msg,
                    'token': connection_token[:16] + '...'
                }

        except Exception as e:
            self.logger.error(f"Device registration error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Unexpected error during device registration'
            }

    def sync_calls(self, calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sync call logs to backend"""
        if not self.device_id:
            return {
                'success': False,
                'error': 'Device not registered',
                'message': 'Please register device first using QR code'
            }

        try:
            self.logger.info(f"Syncing {len(calls)} calls to backend...")

            payload = {'calls': calls}
            url = f"{self.api_base}/calls/sync/{self.device_id}"

            # Add device info to headers
            headers = {
                **self.session.headers,
                'X-Device-ID': self.device_id,
                'X-Sync-Call-Count': str(len(calls)),
                'X-Sync-Timestamp': datetime.now().isoformat()
            }

            response = self.session.post(url, json=payload, headers=headers, timeout=90)

            if response.status_code in [200, 207]:  # 207 is partial success
                data = response.json()
                sync_metrics = data.get('syncMetrics', {})

                self.logger.info(f"✅ Sync completed: {sync_metrics.get('syncedCount', 0)} synced")
                return {
                    'success': True,
                    'synced_count': sync_metrics.get('syncedCount', 0),
                    'duplicate_count': sync_metrics.get('duplicateCount', 0),
                    'error_count': sync_metrics.get('errorCount', 0),
                    'success_rate': sync_metrics.get('successRate', 'N/A'),
                    'message': f"Successfully synced {sync_metrics.get('syncedCount', 0)} calls"
                }
            else:
                try:
                    error_data = response.json()
                except:
                    error_data = {}

                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': error_data.get('message', 'Sync failed'),
                    'details': error_data.get('error', 'Unknown error')
                }

        except Exception as e:
            self.logger.error(f"Call sync error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Unexpected error during call sync'
            }

    def send_heartbeat(self, status_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send heartbeat to maintain connection"""
        if not self.device_id:
            return {'success': False, 'message': 'Device not registered'}

        try:
            url = f"{self.api_base}/devices/device/{self.device_id}/heartbeat"

            heartbeat_data = {
                'timestamp': datetime.now().isoformat(),
                'status': 'active',
                'appVersion': '1.0.5',
                'permissions': {
                    'callLog': ANDROID_AVAILABLE and self.get_call_manager().permissions_granted,
                    'phone': ANDROID_AVAILABLE,
                    'storage': True
                },
                'batteryLevel': self._get_battery_level(),
                'networkType': self._get_network_type(),
                'lastCallSync': datetime.now().isoformat(),
                **(status_data or {})
            }

            response = self.session.post(url, json=heartbeat_data, timeout=30)

            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Heartbeat sent successfully',
                    'server_instructions': response.json().get('serverInstructions', {})
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'message': 'Heartbeat failed'
                }

        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Heartbeat request failed'
            }

    def _get_battery_level(self) -> int:
        """Get actual battery level if possible, otherwise return unknown"""
        if ANDROID_AVAILABLE:
            try:
                # Try to get actual battery level from Android
                activity = PythonActivity.mActivity
                context = activity.getApplicationContext()
                battery_manager = context.getSystemService(Context.BATTERY_SERVICE)
                if battery_manager:
                    return int(battery_manager.getIntProperty(4))  # BATTERY_PROPERTY_CAPACITY
            except Exception:
                pass
        return -1  # Unknown battery level

    def _get_network_type(self) -> str:
        """Get actual network type if possible, otherwise return unknown"""
        if ANDROID_AVAILABLE:
            try:
                # Try to get actual network type from Android
                activity = PythonActivity.mActivity
                context = activity.getApplicationContext()
                connectivity_manager = context.getSystemService(Context.CONNECTIVITY_SERVICE)
                if connectivity_manager:
                    active_network = connectivity_manager.getActiveNetwork()
                    if active_network:
                        network_capabilities = connectivity_manager.getNetworkCapabilities(active_network)
                        if network_capabilities:
                            if network_capabilities.hasTransport(1):  # TRANSPORT_WIFI
                                return 'wifi'
                            elif network_capabilities.hasTransport(0):  # TRANSPORT_CELLULAR
                                return 'cellular'
            except Exception:
                pass
        return 'unknown'


class CallCard(MDCard):
    """Custom card widget for displaying call information"""

    def __init__(self, call_data: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.call_data = call_data
        self.setup_ui()

    def setup_ui(self):
        """Setup the call card UI"""
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = dp(12)
        self.spacing = dp(8)
        self.elevation = 1
        self.radius = [dp(4)]

        # Main layout
        main_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(12)
        )

        # Call type icon
        call_type = self.call_data.get('callType', 'unknown')
        icon_name = {
            'incoming': 'phone-incoming',
            'outgoing': 'phone-outgoing',
            'missed': 'phone-missed',
            'rejected': 'phone-hangup',
            'blocked': 'phone-cancel'
        }.get(call_type, 'phone')

        icon_color = {
            'incoming': (0, 1, 0, 1),  # Green
            'outgoing': (0, 0, 1, 1),  # Blue
            'missed': (1, 0, 0, 1),  # Red
            'rejected': (1, 0.5, 0, 1),  # Orange
            'blocked': (1, 0, 0, 1)  # Red
        }.get(call_type, (0.5, 0.5, 0.5, 1))

        icon = MDIconButton(
            icon=icon_name,
            theme_icon_color='Custom',
            icon_color=icon_color,
            size_hint=(None, None),
            size=(dp(32), dp(32))
        )

        # Call info layout
        info_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(2)
        )

        # Contact name or phone number
        contact_name = self.call_data.get('contactName') or self.call_data.get('phoneNumber', 'Unknown')
        name_label = MDLabel(
            text=contact_name,
            font_style='Subtitle2',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(20)
        )

        # Time and duration info
        timestamp_str = self.call_data.get('timestamp', '')
        try:
            if timestamp_str:
                # Parse ISO timestamp
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_str = dt.strftime('%m/%d %H:%M')
            else:
                time_str = 'Unknown time'
        except Exception:
            time_str = 'Unknown time'

        duration = self.call_data.get('duration', 0)
        if duration > 0:
            if duration >= 60:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}m {seconds}s"
            else:
                duration_str = f"{duration}s"
        else:
            duration_str = "No answer" if call_type in ['missed', 'rejected'] else "0s"

        time_info = f"{time_str} • {duration_str}"
        time_label = MDLabel(
            text=time_info,
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(16)
        )

        # Add widgets to layouts
        info_layout.add_widget(name_label)
        info_layout.add_widget(time_label)

        main_layout.add_widget(icon)
        main_layout.add_widget(info_layout)

        self.add_widget(main_layout)


class StatusCard(MDCard):
    """Custom card widget for displaying app status"""

    def __init__(self, title: str, value: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.value_label = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the status card UI"""
        self.size_hint_y = None
        self.height = dp(70)
        self.padding = dp(12)
        self.elevation = 1
        self.radius = [dp(4)]

        layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(4)
        )

        title_label = MDLabel(
            text=self.title,
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(16)
        )

        self.value_label = MDLabel(
            text=str(self.value),
            font_style='Subtitle1',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(24)
        )

        layout.add_widget(title_label)
        layout.add_widget(self.value_label)
        self.add_widget(layout)

    def update_value(self, new_value: str):
        """Update the card value"""
        self.value = new_value
        if self.value_label:
            self.value_label.text = str(new_value)


class MainScreen(MDScreen):
    """Main application screen with call log display"""

    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'main'
        self.connection_status_card = None
        self.sync_status_card = None
        self.calls_count_card = None
        self.device_status_card = None
        self.calls_scroll = None
        self.calls_list = None
        self.setup_ui()

        # Schedule UI updates
        Clock.schedule_interval(self.update_ui, 30)  # Update every 30 seconds

    def setup_ui(self):
        """Setup the main screen UI"""
        # Main layout
        main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=dp(16)
        )

        # Top app bar
        app_bar = MDTopAppBar(
            title="Kortahun United",
            elevation=2,
            left_action_items=[["menu", lambda x: self.app.open_settings()]],
            right_action_items=[
                ["refresh", lambda x: self.refresh_data()],
                ["sync", lambda x: self.manual_sync()]
            ]
        )

        # Status cards container
        status_layout = MDGridLayout(
            cols=2,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(80)
        )

        # Status cards
        self.connection_status_card = StatusCard("Connection", "Checking...")
        self.sync_status_card = StatusCard("Last Sync", "Never")
        self.calls_count_card = StatusCard("Total Calls", "0")
        self.device_status_card = StatusCard("Device Status", "Unknown")

        status_layout.add_widget(self.connection_status_card)
        status_layout.add_widget(self.sync_status_card)
        status_layout.add_widget(self.calls_count_card)
        status_layout.add_widget(self.device_status_card)

        # Recent calls section
        calls_label = MDLabel(
            text="Recent Calls",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(40)
        )

        # Scrollable call list
        self.calls_scroll = MDScrollView()
        self.calls_list = MDBoxLayout(
            orientation='vertical',
            spacing=dp(4),
            size_hint_y=None,
            height=dp(0)  # Will be updated based on content
        )

        self.calls_scroll.add_widget(self.calls_list)

        # Action buttons
        buttons_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(8),
            size_hint_y=None,
            height=dp(40),
            padding=[0, dp(8), 0, 0]
        )

        sync_button = MDRaisedButton(
            text="Sync Now",
            on_release=self.manual_sync,
            size_hint_x=0.4
        )

        test_button = MDFlatButton(
            text="Test Connection",
            on_release=self.test_connection,
            size_hint_x=0.3
        )

        qr_button = MDFlatButton(
            text="Scan QR",
            on_release=self.show_qr_scanner,
            size_hint_x=0.3
        )

        buttons_layout.add_widget(sync_button)
        buttons_layout.add_widget(test_button)
        buttons_layout.add_widget(qr_button)

        # Add all widgets to main layout
        main_layout.add_widget(app_bar)
        main_layout.add_widget(status_layout)
        main_layout.add_widget(calls_label)
        main_layout.add_widget(self.calls_scroll)
        main_layout.add_widget(buttons_layout)

        self.add_widget(main_layout)

        # Initial data load
        Clock.schedule_once(self.initial_load, 0.5)

    def initial_load(self, dt):
        """Initial data loading"""
        threading.Thread(target=self._initial_load_thread, daemon=True).start()

    def _initial_load_thread(self):
        """Initial loading in background thread"""
        # Test connection
        connection_result = self.app.backend_api.test_connection()
        Clock.schedule_once(lambda dt: self.update_connection_status(connection_result), 0)

        # Load call logs
        self.refresh_data()

    @mainthread
    def update_connection_status(self, result):
        """Update connection status on main thread"""
        if result['success']:
            self.connection_status_card.update_value("Connected")
        else:
            self.connection_status_card.update_value("Failed")

    def refresh_data(self):
        """Refresh call log data"""
        threading.Thread(target=self._refresh_data_thread, daemon=True).start()

    def _refresh_data_thread(self):
        """Refresh data in background thread"""
        try:
            # Get call logs
            calls = self.app.call_manager.get_call_logs(limit=20)

            # Update UI on main thread
            Clock.schedule_once(lambda dt: self.update_calls_display(calls), 0)

            # Update counts
            Clock.schedule_once(lambda dt: self.update_status_cards(calls), 0)

        except Exception as e:
            self.app.logger.error(f"Error refreshing data: {e}")

    @mainthread
    def update_calls_display(self, calls):
        """Update calls display on main thread"""
        # Clear existing calls
        self.calls_list.clear_widgets()

        # Show recent calls
        recent_calls = calls[:10]  # Show only 10 calls

        if not recent_calls:
            no_calls_label = MDLabel(
                text="No calls found. Please ensure permissions are granted." if ANDROID_AVAILABLE else "Android not available - cannot access call logs",
                halign='center',
                font_style='Body1',
                theme_text_color='Secondary'
            )
            self.calls_list.add_widget(no_calls_label)
            self.calls_list.height = dp(40)
        else:
            for call in recent_calls:
                call_card = CallCard(call)
                self.calls_list.add_widget(call_card)

            # Update list height
            self.calls_list.height = len(self.calls_list.children) * dp(84)

    @mainthread
    def update_status_cards(self, calls):
        """Update status cards"""
        # Update calls count
        self.calls_count_card.update_value(str(len(calls)))

        # Check last sync from storage
        try:
            if self.app.storage.exists('app_settings'):
                settings = self.app.storage.get('app_settings')
                last_sync = settings.get('last_sync_time')
                if last_sync:
                    sync_dt = datetime.fromisoformat(last_sync)
                    time_diff = datetime.now() - sync_dt
                    if time_diff.total_seconds() < 3600:  # Less than 1 hour
                        minutes_ago = int(time_diff.total_seconds() / 60)
                        self.sync_status_card.update_value(f"{minutes_ago}m ago")
                    else:
                        hours_ago = int(time_diff.total_seconds() / 3600)
                        self.sync_status_card.update_value(f"{hours_ago}h ago")
                else:
                    self.sync_status_card.update_value("Never")
            else:
                self.sync_status_card.update_value("Never")
        except Exception:
            self.sync_status_card.update_value("Unknown")

        # Update device status
        try:
            if self.app.storage.exists('device_info'):
                device_info = self.app.storage.get('device_info')
                device_id = device_info.get('device_id')
                if device_id:
                    self.device_status_card.update_value("Registered")
                else:
                    self.device_status_card.update_value("Not Registered")
            else:
                self.device_status_card.update_value("Not Registered")
        except Exception:
            self.device_status_card.update_value("Unknown")

    def manual_sync(self, *args):
        """Manual sync trigger"""
        threading.Thread(target=self._manual_sync_thread, daemon=True).start()

    def _manual_sync_thread(self):
        """Manual sync in background thread"""
        try:
            # Check if device is registered
            if not self.app.backend_api.device_id:
                Clock.schedule_once(
                    lambda dt: SimpleNotification.show_error("Device not registered. Please scan QR code first."), 0)
                return

            # Show sync in progress
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("Syncing calls...", (0, 0, 1, 1)), 0)

            # Get call logs
            calls = self.app.call_manager.get_call_logs(limit=1000)

            if not calls:
                Clock.schedule_once(lambda dt: SimpleNotification.show_message("No calls to sync", (0, 0, 1, 1)), 0)
                return

            # Sync with backend
            result = self.app.backend_api.sync_calls(calls)

            if result['success']:
                # Update last sync time
                self.app.update_app_setting('last_sync_time', datetime.now().isoformat())

                sync_msg = f"Synced {result['synced_count']} calls"
                if result['duplicate_count'] > 0:
                    sync_msg += f" ({result['duplicate_count']} duplicates skipped)"

                Clock.schedule_once(lambda dt: SimpleNotification.show_message(sync_msg), 0)
                Clock.schedule_once(lambda dt: self.update_status_cards(calls), 0.5)
            else:
                error_msg = f"Sync failed: {result.get('message', 'Unknown error')}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_msg), 0)

        except Exception as e:
            error_message = f"Sync error: {str(e)}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def test_connection(self, *args):
        """Test backend connection"""
        threading.Thread(target=self._test_connection_thread, daemon=True).start()

    def _test_connection_thread(self):
        """Test connection in background thread"""
        result = self.app.backend_api.test_connection()
        Clock.schedule_once(lambda dt: self.update_connection_status(result), 0)

        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("Connection successful!"), 0)
        else:
            error_message = f"Connection failed: {result.get('message', 'Unknown error')}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def show_qr_scanner(self, *args):
        """Show QR code scanner"""
        self.app.show_qr_scanner_dialog()

    def update_ui(self, dt):
        """Periodic UI updates"""
        # Update connection status
        threading.Thread(target=self._update_connection_status_thread, daemon=True).start()

    def _update_connection_status_thread(self):
        """Update connection status in background"""
        result = self.app.backend_api.test_connection()
        Clock.schedule_once(lambda dt: self.update_connection_status(result), 0)


class QRScannerDialog:
    """QR Code scanner dialog for device registration"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.dialog = None
        self.qr_input = None

    def show(self):
        """Show QR scanner dialog"""
        if not self.dialog:
            # QR input field
            self.qr_input = MDTextField(
                hint_text="Paste QR code URL here",
                multiline=True,
                size_hint_y=None,
                height=dp(120)
            )

            # Buttons
            content = MDBoxLayout(
                orientation='vertical',
                spacing=dp(16),
                size_hint_y=None,
                height=dp(250)
            )

            instruction_label = MDLabel(
                text="STEPS TO REGISTER DEVICE:\n\n1. Generate QR code from web dashboard\n2. Paste the COMPLETE URL below\n3. URL should start with 'https://kortahununited...'\n4. Click Register to connect device",
                size_hint_y=None,
                height=dp(120)
            )

            content.add_widget(instruction_label)
            content.add_widget(self.qr_input)

            self.dialog = MDDialog(
                title="Register Device - v1.0.5",
                type="custom",
                content_cls=content,
                buttons=[
                    MDFlatButton(
                        text="CANCEL",
                        on_release=self.close_dialog
                    ),
                    MDRaisedButton(
                        text="REGISTER",
                        on_release=self.register_device
                    ),
                ],
            )

        self.dialog.open()

    def close_dialog(self, *args):
        """Close dialog"""
        if self.dialog:
            self.dialog.dismiss()

    def register_device(self, *args):
        """Register device with QR data"""
        qr_data = self.qr_input.text.strip()

        if not qr_data:
            SimpleNotification.show_error("Please enter QR code URL")
            return

        if not qr_data.startswith('https://'):
            SimpleNotification.show_error("URL must start with https://")
            return

        if 'kortahununited' not in qr_data.lower():
            SimpleNotification.show_error("Invalid Kortahun United URL")
            return

        if '/api/devices/connect/' not in qr_data:
            SimpleNotification.show_error("Invalid registration URL format")
            return

        # Close dialog and start registration
        self.close_dialog()

        # Show progress
        SimpleNotification.show_message("Registering device...", (0, 0, 1, 1))

        # Register in background thread
        threading.Thread(target=self._register_device_thread, args=(qr_data,), daemon=True).start()

    def _register_device_thread(self, qr_data: str):
        """Register device in background thread"""
        try:
            self.app.logger.info(f"[Registering device from QR] {qr_data[:50]}...")

            result = self.app.backend_api.register_device_from_qr(qr_data)

            if result['success']:
                # Store device information
                device_id = result['device_id']
                device_name = result.get('device_name', f'Device {device_id}')

                # Use proper storage methods
                device_info = {
                    'device_id': device_id,
                    'device_name': device_name,
                    'registration_time': datetime.now().isoformat(),
                    'sync_endpoint': result.get('sync_endpoint'),
                    'status_endpoint': result.get('status_endpoint'),
                    'heartbeat_endpoint': result.get('heartbeat_endpoint')
                }

                self.app.storage.put('device_info', **device_info)

                success_message = f"✅ Device registered: {device_name}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_message(success_message), 0)

                # Send initial heartbeat
                Clock.schedule_once(lambda dt: self.app.send_initial_heartbeat(), 2)

                # Start automatic sync
                Clock.schedule_once(lambda dt: self.app.start_auto_sync(), 3)

            else:
                error_msg = result.get('message', 'Registration failed')
                self.app.logger.error(f"Registration failed: {error_msg}")
                error_message = f"❌ Registration failed: {error_msg}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

        except Exception as registration_error:
            self.app.logger.error(f"Registration error: {str(registration_error)}")
            error_message = f"❌ Registration error: {str(registration_error)}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)


class SettingsScreen(MDScreen):
    """Settings and configuration screen"""

    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'settings'
        self.device_id_label = None
        self.registration_time_label = None
        self.last_sync_label = None
        self.server_url_field = None
        self.permissions_status_label = None
        self.setup_ui()

    def setup_ui(self):
        """Setup settings screen UI"""
        main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(16),
            padding=dp(16)
        )

        # App bar
        app_bar = MDTopAppBar(
            title="Settings",
            elevation=2,
            left_action_items=[["arrow-left", lambda x: self.app.go_back()]]
        )

        # Settings content
        scroll = MDScrollView()
        settings_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(16),
            size_hint_y=None
        )
        settings_layout.bind(minimum_height=settings_layout.setter('height'))

        # Device information section
        device_card = MDCard(
            size_hint_y=None,
            height=dp(240),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        device_layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        device_title = MDLabel(
            text="Device Information",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        # Device info labels (will be updated)
        self.device_id_label = MDLabel(
            text="Device ID: Not registered",
            font_style='Body2',
            size_hint_y=None,
            height=dp(20)
        )

        self.registration_time_label = MDLabel(
            text="Registered: Never",
            font_style='Body2',
            size_hint_y=None,
            height=dp(20)
        )

        self.last_sync_label = MDLabel(
            text="Last Sync: Never",
            font_style='Body2',
            size_hint_y=None,
            height=dp(20)
        )

        # Permissions status
        self.permissions_status_label = MDLabel(
            text="Permissions: Unknown",
            font_style='Body2',
            size_hint_y=None,
            height=dp(20)
        )

        # Add version info
        version_label = MDLabel(
            text="App Version: 1.0.5 (No Mock Data)",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(20)
        )

        platform_label = MDLabel(
            text=f"Platform: {platform} | Android: {'Yes' if ANDROID_AVAILABLE else 'No'}",
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(20)
        )

        device_layout.add_widget(device_title)
        device_layout.add_widget(self.device_id_label)
        device_layout.add_widget(self.registration_time_label)
        device_layout.add_widget(self.last_sync_label)
        device_layout.add_widget(self.permissions_status_label)
        device_layout.add_widget(version_label)
        device_layout.add_widget(platform_label)
        device_card.add_widget(device_layout)

        # Server settings section
        server_card = MDCard(
            size_hint_y=None,
            height=dp(150),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        server_layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        server_title = MDLabel(
            text="Server Configuration",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        self.server_url_field = MDTextField(
            hint_text="Server URL",
            text=self.app.backend_api.base_url,
            size_hint_y=None,
            height=dp(50)
        )

        update_server_btn = MDRaisedButton(
            text="Update Server URL",
            size_hint_y=None,
            height=dp(40),
            on_release=self.update_server_url
        )

        server_layout.add_widget(server_title)
        server_layout.add_widget(self.server_url_field)
        server_layout.add_widget(update_server_btn)
        server_card.add_widget(server_layout)

        # Permissions section (Android only)
        if ANDROID_AVAILABLE:
            permissions_card = MDCard(
                size_hint_y=None,
                height=dp(120),
                padding=dp(16),
                elevation=2,
                radius=[dp(8)]
            )

            permissions_layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

            permissions_title = MDLabel(
                text="Permissions",
                font_style='H6',
                theme_text_color='Primary',
                size_hint_y=None,
                height=dp(30)
            )

            request_permissions_btn = MDRaisedButton(
                text="Request Permissions",
                size_hint_y=None,
                height=dp(40),
                on_release=self.request_permissions
            )

            permissions_layout.add_widget(permissions_title)
            permissions_layout.add_widget(request_permissions_btn)
            permissions_card.add_widget(permissions_layout)

        # Actions section
        actions_card = MDCard(
            size_hint_y=None,
            height=dp(320),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        actions_layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        actions_title = MDLabel(
            text="Actions",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        test_connection_btn = MDRaisedButton(
            text="Test Connection",
            size_hint_y=None,
            height=dp(40),
            on_release=self.test_connection
        )

        register_device_btn = MDRaisedButton(
            text="Register Device",
            size_hint_y=None,
            height=dp(40),
            on_release=self.show_qr_scanner
        )

        sync_now_btn = MDRaisedButton(
            text="Sync Now",
            size_hint_y=None,
            height=dp(40),
            on_release=self.manual_sync
        )

        send_heartbeat_btn = MDFlatButton(
            text="Send Heartbeat",
            size_hint_y=None,
            height=dp(40),
            on_release=self.send_heartbeat
        )

        clear_data_btn = MDFlatButton(
            text="Clear Data",
            size_hint_y=None,
            height=dp(40),
            on_release=self.clear_data
        )

        actions_layout.add_widget(actions_title)
        actions_layout.add_widget(test_connection_btn)
        actions_layout.add_widget(register_device_btn)
        actions_layout.add_widget(sync_now_btn)
        actions_layout.add_widget(send_heartbeat_btn)
        actions_layout.add_widget(clear_data_btn)
        actions_card.add_widget(actions_layout)

        # Add all cards to settings layout
        settings_layout.add_widget(device_card)
        settings_layout.add_widget(server_card)
        if ANDROID_AVAILABLE:
            settings_layout.add_widget(permissions_card)
        settings_layout.add_widget(actions_card)

        scroll.add_widget(settings_layout)

        main_layout.add_widget(app_bar)
        main_layout.add_widget(scroll)

        self.add_widget(main_layout)

        # Load current settings
        Clock.schedule_once(self.load_settings, 0.1)

    def load_settings(self, dt):
        """Load current settings"""
        # Load device info
        try:
            if self.app.storage.exists('device_info'):
                device_info = self.app.storage.get('device_info')
                device_id = device_info.get('device_id')
                if device_id:
                    self.device_id_label.text = f"Device ID: {device_id}"

                registration_time = device_info.get('registration_time')
                if registration_time:
                    reg_dt = datetime.fromisoformat(registration_time)
                    self.registration_time_label.text = f"Registered: {reg_dt.strftime('%Y-%m-%d %H:%M')}"
        except Exception as e:
            self.app.logger.error(f"Error loading device info: {e}")

        try:
            if self.app.storage.exists('app_settings'):
                app_settings = self.app.storage.get('app_settings')
                last_sync = app_settings.get('last_sync_time')
                if last_sync:
                    sync_dt = datetime.fromisoformat(last_sync)
                    self.last_sync_label.text = f"Last Sync: {sync_dt.strftime('%Y-%m-%d %H:%M')}"
        except Exception as e:
            self.app.logger.error(f"Error loading app settings: {e}")

        # Update permissions status
        if ANDROID_AVAILABLE:
            permissions_granted = self.app.call_manager.permissions_granted
            self.permissions_status_label.text = f"Permissions: {'Granted' if permissions_granted else 'Not Granted'}"
        else:
            self.permissions_status_label.text = "Permissions: N/A (Desktop mode)"

    def request_permissions(self, *args):
        """Request Android permissions"""
        if ANDROID_AVAILABLE:
            threading.Thread(target=self._request_permissions_thread, daemon=True).start()

    def _request_permissions_thread(self):
        """Request permissions in background"""
        success = self.app.call_manager.request_permissions()

        if success:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("✅ Permissions requested"), 0)
            Clock.schedule_once(self.load_settings, 1)  # Refresh settings after delay
        else:
            Clock.schedule_once(lambda dt: SimpleNotification.show_error("❌ Permission request failed"), 0)

    def update_server_url(self, *args):
        """Update server URL"""
        new_url = self.server_url_field.text.strip()

        if not new_url.startswith('http'):
            SimpleNotification.show_error("Invalid URL format")
            return

        # Update backend API
        self.app.backend_api.base_url = new_url
        self.app.backend_api.api_base = f"{new_url}/api"

        # Store in settings
        self.app.update_app_setting('server_url', new_url)

        SimpleNotification.show_message("Server URL updated")

    def test_connection(self, *args):
        """Test backend connection"""
        threading.Thread(target=self._test_connection_thread, daemon=True).start()

    def _test_connection_thread(self):
        """Test connection in background"""
        result = self.app.backend_api.test_connection()

        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("✅ Connection successful!"), 0)
        else:
            error_msg = result.get('message', 'Unknown error')
            error_message = f"❌ Connection failed: {error_msg}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def show_qr_scanner(self, *args):
        """Show QR scanner"""
        self.app.show_qr_scanner_dialog()

    def manual_sync(self, *args):
        """Manual sync"""
        # Navigate back to main screen and trigger sync
        self.app.go_back()
        Clock.schedule_once(lambda dt: self.app.root.get_screen('main').manual_sync(), 0.5)

    def send_heartbeat(self, *args):
        """Manual heartbeat"""
        threading.Thread(target=self._send_heartbeat_thread, daemon=True).start()

    def _send_heartbeat_thread(self):
        """Send heartbeat in background"""
        if not self.app.backend_api.device_id:
            Clock.schedule_once(lambda dt: SimpleNotification.show_error("Device not registered"), 0)
            return

        result = self.app.backend_api.send_heartbeat()
        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("❤️ Heartbeat sent successfully"), 0)
        else:
            error_message = f"💔 Heartbeat failed: {result.get('message')}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def clear_data(self, *args):
        """Clear all app data"""
        confirm_dialog = MDDialog(
            title="Clear Data",
            text="This will remove all stored data including device registration. Are you sure?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="CLEAR",
                    on_release=lambda x: self.perform_clear_data(confirm_dialog)
                ),
            ],
        )
        confirm_dialog.open()

    def perform_clear_data(self, dialog):
        """Actually clear the data"""
        dialog.dismiss()

        try:
            # Clear storage using proper JsonStore methods
            if self.app.storage.exists('device_info'):
                self.app.storage.delete('device_info')

            if self.app.storage.exists('app_settings'):
                self.app.storage.delete('app_settings')

            # Reset backend API
            self.app.backend_api.device_id = None
            self.app.backend_api.device_name = None

            # Update UI
            self.load_settings(None)

            SimpleNotification.show_message("✅ Data cleared successfully")

        except Exception as e:
            error_message = f"❌ Error clearing data: {str(e)}"
            SimpleNotification.show_error(error_message)


class KortahunUnitedApp(MDApp):
    """Main application class - Version 1.0.5 - No Mock Data"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Kortahun United"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"

        # Initialize components
        self.logger = self.setup_logging()
        self.storage = None
        self.call_manager = CallLogManager()
        self.backend_api = BackendAPI()
        self.qr_scanner = None

        # Auto sync settings
        self.auto_sync_enabled = True
        self.sync_interval = 300  # 5 minutes
        self.heartbeat_interval = 60  # 1 minute

        # Background threads
        self.auto_sync_thread = None
        self.heartbeat_thread = None
        self.running = True

    def build(self):
        """Build the application UI"""
        self.logger.info("🚀 Building Kortahun United app (Version 1.0.5 - No Mock Data)...")

        # Setup storage
        self.setup_storage()

        # Load saved server URL
        self.load_app_settings()

        # Load device info if exists
        self.load_device_info()

        # Create screen manager
        screen_manager = MDScreenManager()

        # Add screens
        main_screen = MainScreen(self)
        settings_screen = SettingsScreen(self)

        screen_manager.add_widget(main_screen)
        screen_manager.add_widget(settings_screen)

        # Set current screen
        screen_manager.current = 'main'

        # Initialize QR scanner
        self.qr_scanner = QRScannerDialog(self)

        # Request permissions on Android
        if ANDROID_AVAILABLE:
            Clock.schedule_once(self.request_permissions, 1)

        # Start background services
        Clock.schedule_once(self.start_background_services, 2)

        self.logger.info("✅ App built successfully (Version 1.0.5 - No Mock Data)!")
        return screen_manager

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger('KortahunUnited')

        if ANDROID_AVAILABLE:
            try:
                # Log to external storage on Android
                log_path = os.path.join(primary_external_storage_path(), 'KortahunUnited', 'logs')
                os.makedirs(log_path, exist_ok=True)

                file_handler = logging.FileHandler(os.path.join(log_path, 'app.log'))
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(file_handler)

                print(f"📝 Logging to: {log_path}/app.log")
            except Exception as e:
                print(f"⚠️ Could not setup file logging: {e}")

        return logger

    def setup_storage(self):
        """Setup local storage"""
        try:
            if ANDROID_AVAILABLE:
                # Use external storage on Android
                storage_path = os.path.join(primary_external_storage_path(), 'KortahunUnited')
                os.makedirs(storage_path, exist_ok=True)
                storage_file = os.path.join(storage_path, 'settings.json')
            else:
                # Use local directory for desktop testing
                storage_file = 'kortahun_settings.json'

            self.storage = JsonStore(storage_file)
            self.logger.info(f"📁 Storage initialized: {storage_file}")

        except Exception as e:
            # Fallback to memory storage
            self.logger.error(f"Storage setup failed: {e}")
            self.storage = JsonStore('fallback_settings.json')

    def load_app_settings(self):
        """Load app settings from storage"""
        try:
            if self.storage.exists('app_settings'):
                app_settings = self.storage.get('app_settings')

                saved_url = app_settings.get('server_url')
                if saved_url:
                    self.backend_api.base_url = saved_url
                    self.backend_api.api_base = f"{saved_url}/api"
                    self.logger.info(f"Loaded server URL: {saved_url}")
            else:
                self.logger.info("No app settings found, using defaults")
        except Exception as e:
            self.logger.error(f"Error loading app settings: {e}")

    def load_device_info(self):
        """Load device info from storage"""
        try:
            if self.storage.exists('device_info'):
                device_info = self.storage.get('device_info')

                device_id = device_info.get('device_id')
                device_name = device_info.get('device_name')

                if device_id:
                    self.backend_api.device_id = device_id
                    self.backend_api.session.headers.update({'X-Device-ID': device_id})
                    self.logger.info(f"Loaded device ID: {device_id}")

                if device_name:
                    self.backend_api.device_name = device_name
            else:
                self.logger.info("No device info found")
        except Exception as e:
            self.logger.error(f"Error loading device info: {e}")

    def update_app_setting(self, key: str, value):
        """Update app setting in storage - HELPER METHOD"""
        try:
            if self.storage.exists('app_settings'):
                app_settings = self.storage.get('app_settings')
            else:
                app_settings = {}

            app_settings[key] = value
            self.storage.put('app_settings', **app_settings)
            self.logger.info(f"Updated app setting: {key} = {value}")
        except Exception as e:
            self.logger.error(f"Error updating app setting {key}: {e}")

    def request_permissions(self, dt):
        """Request Android permissions"""
        if ANDROID_AVAILABLE:
            self.logger.info("📱 Requesting Android permissions...")
            success = self.call_manager.request_permissions()
            if success:
                self.logger.info("✅ Permissions requested successfully")
            else:
                self.logger.warning("⚠️ Permission request failed")

    def start_background_services(self, dt):
        """Start background sync and heartbeat services"""
        self.logger.info("🔄 Starting background services...")

        # Start auto sync and heartbeat if device is registered
        if self.backend_api.device_id:
            self.start_auto_sync()
            self.start_heartbeat_service()

    def start_auto_sync(self):
        """Start automatic call sync"""
        if self.auto_sync_thread and self.auto_sync_thread.is_alive():
            return  # Already running

        self.auto_sync_enabled = True
        self.auto_sync_thread = threading.Thread(target=self.auto_sync_worker, daemon=True)
        self.auto_sync_thread.start()
        self.logger.info("🔄 Auto sync started")

    def start_heartbeat_service(self):
        """Start heartbeat service"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return  # Already running

        self.heartbeat_thread = threading.Thread(target=self.heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("💓 Heartbeat service started")

    def auto_sync_worker(self):
        """Background auto sync worker"""
        while self.running and self.auto_sync_enabled:
            try:
                if self.backend_api.device_id:
                    self.logger.info("🔄 Performing automatic sync...")

                    # Get call logs
                    calls = self.call_manager.get_call_logs(limit=1000)

                    if calls:
                        # Sync with backend
                        result = self.backend_api.sync_calls(calls)

                        if result['success']:
                            self.update_app_setting('last_sync_time', datetime.now().isoformat())
                            sync_count = result.get('synced_count', 0)
                            self.logger.info(f"✅ Auto sync completed: {sync_count} calls")
                        else:
                            self.logger.error(f"❌ Auto sync failed: {result.get('message', 'Unknown error')}")
                    else:
                        self.logger.info("ℹ️ No calls available for sync")

            except Exception as e:
                self.logger.error(f"❌ Auto sync error: {e}")

            # Wait for next sync interval
            time.sleep(self.sync_interval)

    def heartbeat_worker(self):
        """Background heartbeat worker"""
        while self.running:
            try:
                if self.backend_api.device_id:
                    result = self.backend_api.send_heartbeat()
                    if result['success']:
                        self.logger.info("💓 Heartbeat sent successfully")
                    else:
                        self.logger.warning(f"💔 Heartbeat failed: {result.get('message')}")

            except Exception as e:
                self.logger.error(f"💔 Heartbeat error: {e}")

            # Wait for next heartbeat
            time.sleep(self.heartbeat_interval)

    def send_initial_heartbeat(self):
        """Send initial heartbeat after registration"""
        threading.Thread(target=self._send_initial_heartbeat_thread, daemon=True).start()

    def _send_initial_heartbeat_thread(self):
        """Send initial heartbeat in background"""
        try:
            if self.backend_api.device_id:
                result = self.backend_api.send_heartbeat({
                    'status': 'just_registered',
                    'registrationMethod': 'qr_code_scan',
                    'appVersion': '1.0.5'
                })

                if result['success']:
                    self.logger.info("💓 Initial heartbeat sent successfully")

                    # Start heartbeat service
                    Clock.schedule_once(lambda dt: self.start_heartbeat_service(), 1)
                else:
                    self.logger.warning(f"💔 Initial heartbeat failed: {result.get('message')}")

        except Exception as e:
            self.logger.error(f"💔 Initial heartbeat error: {e}")

    def open_settings(self):
        """Open settings screen"""
        self.root.current = 'settings'

    def go_back(self):
        """Go back to main screen"""
        self.root.current = 'main'

    def show_qr_scanner_dialog(self):
        """Show QR scanner dialog"""
        if self.qr_scanner:
            self.qr_scanner.show()

    def on_stop(self):
        """Called when app is stopping"""
        self.logger.info("🛑 App stopping...")
        self.running = False

        # Wait for threads to finish
        if self.auto_sync_thread and self.auto_sync_thread.is_alive():
            self.auto_sync_thread.join(timeout=5)

        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)

        self.logger.info("✅ App stopped cleanly")


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("🚀 Starting Kortahun United Call Tracking App (Version 1.0.5 - No Mock Data)...")
    print(f"📱 Platform: {platform}")
    print(f"🤖 Android available: {ANDROID_AVAILABLE}")
    print("🔧 VERSION 1.0.5 CHANGES:")
    print("   - REMOVED: All mock data generation functions")
    print("   - REMOVED: Mock data fallbacks and indicators")
    print("   - IMPROVED: Error handling when no calls are available")
    print("   - ENHANCED: Real Android call log integration only")
    print("   - ADDED: Better permission status tracking")
    print("   - ADDED: Clear messaging when Android is not available")
    print("   - IMPROVED: Battery and network detection from actual Android APIs")
    print("   - ENHANCED: Heartbeat data with real device information")
    print("   - FIXED: All storage operations using proper JsonStore methods")
    print("   - ADDED: Platform and Android availability indicators in settings")

    if not ANDROID_AVAILABLE:
        print("⚠️  WARNING: Android not available - app will only work for server connection testing")
        print("   - Call logs cannot be retrieved without Android")
        print("   - Permissions cannot be requested")
        print("   - Real device data is not available")

    # Create and run app
    try:
        app = KortahunUnitedApp()
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 App interrupted by user")
    except Exception as e:
        print(f"💥 App crashed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("👋 App terminated")