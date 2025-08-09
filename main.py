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
    from jnius import autoclass, PythonJavaClass, java_method
    from android.runnable import run_on_ui_thread

    ANDROID_AVAILABLE = True

    # Android system classes
    Context = autoclass('android.content.Context')
    ContentResolver = autoclass('android.content.ContentResolver')
    CallLog = autoclass('android.provider.CallLog')
    Cursor = autoclass('android.database.Cursor')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Intent = autoclass('android.content.Intent')

    # QR Scanner imports
    try:
        from android import activity
        from android.broadcast import BroadcastReceiver

        SCANNER_AVAILABLE = True
    except ImportError:
        SCANNER_AVAILABLE = False

except ImportError:
    ANDROID_AVAILABLE = False
    SCANNER_AVAILABLE = False
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
from kivymd.uix.snackbar import Snackbar


class SimpleNotification:
    """Enhanced notification system with Snackbar support"""

    @staticmethod
    @mainthread
    def show_message(message: str, color=(0, 1, 0, 1)):
        """Show a message using Snackbar"""
        try:
            snackbar = Snackbar(
                text=message,
                duration=3,
                bg_color=color
            )
            snackbar.open()
        except Exception:
            # Fallback to print
            status = "SUCCESS" if color == (0, 1, 0, 1) else "INFO" if color == (0, 0, 1, 1) else "ERROR"
            print(f"[{status}] {message}")

    @staticmethod
    def show_error(message: str):
        """Show error message"""
        SimpleNotification.show_message(message, (1, 0, 0, 1))

    @staticmethod
    def show_info(message: str):
        """Show info message"""
        SimpleNotification.show_message(message, (0, 0, 1, 1))


class QRScannerManager:
    """Enhanced QR Scanner with camera integration"""

    def __init__(self, app_instance):
        self.app = app_instance
        self.scanning = False
        self.callback = None

    def scan_qr_code(self, callback):
        """Start QR code scanning"""
        self.callback = callback

        if ANDROID_AVAILABLE and SCANNER_AVAILABLE:
            self._start_android_scanner()
        else:
            # Fallback to manual input
            self._show_manual_input_dialog()

    def _start_android_scanner(self):
        """Start Android QR scanner using Zxing"""
        try:
            activity = PythonActivity.mActivity

            # Create intent for QR scanner
            intent = Intent("com.google.zxing.client.android.SCAN")
            intent.putExtra("SCAN_MODE", "QR_CODE_MODE")
            intent.putExtra("SAVE_HISTORY", False)

            # Start activity for result
            activity.startActivityForResult(intent, 0)

            # Set up result handler
            activity.bind(on_activity_result=self._on_scan_result)

        except Exception as e:
            self.app.logger.error(f"Scanner error: {e}")
            self._show_manual_input_dialog()

    def _on_scan_result(self, request_code, result_code, intent):
        """Handle QR scan result"""
        if request_code == 0:  # Our QR scan request
            if result_code == -1:  # RESULT_OK
                contents = intent.getStringExtra("SCAN_RESULT")
                if contents and self.callback:
                    Clock.schedule_once(lambda dt: self.callback(contents), 0)
            else:
                Clock.schedule_once(lambda dt: SimpleNotification.show_error("QR scan cancelled"), 0)

    def _show_manual_input_dialog(self):
        """Show manual QR input dialog as fallback"""
        Clock.schedule_once(lambda dt: self.app.show_qr_input_dialog(self.callback), 0)


class CallLogManager:
    """Enhanced call log manager with aggressive syncing and retry logic"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.permissions_granted = False
        self.last_call_count = 0
        self.sync_lock = threading.Lock()
        self._call_cache = []
        self._last_refresh = None

    def request_permissions(self) -> bool:
        """Request necessary Android permissions with retry logic"""
        if not ANDROID_AVAILABLE:
            self.logger.warning("Android not available - skipping permission request")
            return False

        try:
            # Request all necessary permissions aggressively
            permissions = [
                Permission.READ_CALL_LOG,
                Permission.READ_PHONE_STATE,
                Permission.READ_CONTACTS,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_EXTERNAL_STORAGE,
                Permission.CAMERA  # For QR scanner
            ]

            self.logger.info("🔐 Requesting Android permissions...")

            # Multiple attempts to ensure permissions are granted
            for attempt in range(3):
                try:
                    request_permissions(permissions)
                    time.sleep(2)  # Wait for permission dialog

                    # Check if we can access call logs
                    test_calls = self._test_call_log_access()
                    if test_calls is not None:
                        self.permissions_granted = True
                        self.logger.info(f"✅ Permissions granted successfully (attempt {attempt + 1})")
                        return True

                except Exception as e:
                    self.logger.warning(f"Permission attempt {attempt + 1} failed: {e}")

            self.logger.error("❌ Failed to obtain permissions after 3 attempts")
            return False

        except Exception as e:
            self.logger.error(f"Error requesting permissions: {e}")
            return False

    def _test_call_log_access(self) -> Optional[List]:
        """Test if we can access call logs"""
        try:
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()
            content_resolver = context.getContentResolver()

            uri = CallLog.Calls.CONTENT_URI
            cursor = content_resolver.query(uri, None, None, None, f"{CallLog.Calls.DATE} DESC LIMIT 1")

            if cursor:
                cursor.close()
                return []  # Empty list but accessible
            return None

        except Exception:
            return None

    def get_call_logs(self, limit: int = 1000, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Get call logs with caching and aggressive refresh"""
        with self.sync_lock:
            # Check cache first
            now = datetime.now()
            if (not force_refresh and self._call_cache and self._last_refresh and
                    (now - self._last_refresh).total_seconds() < 30):  # 30 second cache
                return self._call_cache

            if not ANDROID_AVAILABLE:
                self.logger.warning("Android not available - cannot retrieve call logs")
                return []

            if not self.permissions_granted:
                self.logger.warning("Permissions not granted - attempting to request again")
                self.request_permissions()
                if not self.permissions_granted:
                    return []

            try:
                calls = self._fetch_calls_from_android(limit)

                # Update cache
                self._call_cache = calls
                self._last_refresh = now

                # Check for new calls and trigger immediate sync if needed
                if len(calls) != self.last_call_count:
                    self.logger.info(f"📞 Call count changed: {self.last_call_count} -> {len(calls)}")
                    self.last_call_count = len(calls)

                    # Trigger immediate sync in background
                    if hasattr(self, '_app_instance'):
                        threading.Thread(
                            target=self._trigger_immediate_sync,
                            args=(calls,),
                            daemon=True
                        ).start()

                return calls

            except Exception as e:
                self.logger.error(f"Error getting call logs: {e}")
                return self._call_cache if self._call_cache else []

    def _fetch_calls_from_android(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch calls from Android system with retry logic"""
        for attempt in range(3):  # Retry up to 3 times
            try:
                activity = PythonActivity.mActivity
                context = activity.getApplicationContext()
                content_resolver = context.getContentResolver()

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
                        try:
                            call_data = {
                                'phoneNumber': self._safe_get_string(cursor, CallLog.Calls.NUMBER) or "Unknown",
                                'contactName': self._safe_get_string(cursor, CallLog.Calls.CACHED_NAME),
                                'callType': self._get_call_type(
                                    cursor.getInt(cursor.getColumnIndex(CallLog.Calls.TYPE))),
                                'timestamp': self._format_timestamp(
                                    cursor.getLong(cursor.getColumnIndex(CallLog.Calls.DATE))),
                                'duration': cursor.getInt(cursor.getColumnIndex(CallLog.Calls.DURATION)),
                                'contactId': self._safe_get_string(cursor, CallLog.Calls._ID),
                                'simSlot': 0,

                                # Enhanced metadata
                                'deviceTimestamp': datetime.now().isoformat(),
                                'extractedAt': datetime.now().isoformat(),
                                'dataSource': 'android_call_log',
                                'appVersion': '2.0.0',
                                'syncAttempt': attempt + 1
                            }
                            calls.append(call_data)
                        except Exception as row_error:
                            self.logger.warning(f"Error processing call row: {row_error}")

                        cursor.moveToNext()

                    cursor.close()

                self.logger.info(f"📞 Retrieved {len(calls)} call logs (attempt {attempt + 1})")
                return calls

            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < 2:  # Not the last attempt
                    time.sleep(1)  # Wait before retry
                    continue
                raise e

        return []

    def _trigger_immediate_sync(self, calls: List[Dict[str, Any]]):
        """Trigger immediate sync when new calls detected"""
        try:
            if hasattr(self, '_app_instance') and self._app_instance.backend_api.device_id:
                self.logger.info("🚀 Triggering immediate sync for new calls")
                result = self._app_instance.backend_api.sync_calls(calls)

                if result['success']:
                    self.logger.info(f"✅ Immediate sync completed: {result.get('synced_count', 0)} calls")
                    Clock.schedule_once(
                        lambda dt: SimpleNotification.show_message(f"📞 Synced {result.get('synced_count', 0)} calls"),
                        0
                    )
                else:
                    self.logger.error(f"❌ Immediate sync failed: {result.get('message')}")

        except Exception as e:
            self.logger.error(f"Error in immediate sync: {e}")

    def set_app_instance(self, app_instance):
        """Set app instance for callbacks"""
        self._app_instance = app_instance

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
            1: 'incoming',
            2: 'outgoing',
            3: 'missed',
            4: 'voicemail',
            5: 'rejected',
            6: 'blocked'
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
    """Enhanced backend API with aggressive retry and connection management"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or "https://kortahununited.onrender.com"
        self.api_base = f"{self.base_url}/api"
        self.device_id = None
        self.device_name = None
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.connection_healthy = False
        self.last_successful_sync = None

        # Configure session with aggressive timeouts and retries
        self.session.timeout = 45
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-Python-App': 'true',
            'X-Platform': 'Android',
            'X-Client-Type': 'python-app',
            'X-App-Version': '2.0.0',
            'User-Agent': 'KortahunUnited-PythonApp/2.0.0'
        })

    def test_connection(self) -> Dict[str, Any]:
        """Test connection with retry logic"""
        for attempt in range(3):
            try:
                self.logger.info(f"Testing backend connection (attempt {attempt + 1})...")
                response = self.session.get(f"{self.api_base}/health", timeout=20)

                if response.status_code == 200:
                    data = response.json()
                    self.connection_healthy = True
                    self.logger.info("✅ Backend connection successful")
                    return {
                        'success': True,
                        'status': 'connected',
                        'server_status': data.get('status', 'unknown'),
                        'python_app_ready': data.get('pythonAppReady', False),
                        'message': 'Successfully connected to Kortahun United server'
                    }
                else:
                    self.connection_healthy = False

            except Exception as e:
                self.logger.error(f"Connection test attempt {attempt + 1} failed: {e}")
                if attempt < 2:  # Not the last attempt
                    time.sleep(2)  # Wait before retry
                    continue

        self.connection_healthy = False
        return {
            'success': False,
            'status': 'connection_failed',
            'error': 'All connection attempts failed',
            'message': 'Could not connect to server after 3 attempts'
        }

    def register_device_from_qr(self, qr_data: str) -> Dict[str, Any]:
        """Enhanced device registration with validation and retry"""
        for attempt in range(3):  # Retry registration up to 3 times
            try:
                self.logger.info(f"Registering device (attempt {attempt + 1}): {qr_data[:50]}...")

                # Validate QR data format
                if not qr_data or not qr_data.startswith('http'):
                    return {
                        'success': False,
                        'error': 'Invalid QR code format',
                        'message': 'QR code should contain a valid URL starting with http'
                    }

                # Parse the QR URL to extract the token
                parsed_url = urlparse(qr_data)
                path_parts = parsed_url.path.split('/')

                if len(path_parts) < 5 or path_parts[-2] != 'connect':
                    return {
                        'success': False,
                        'error': 'Invalid QR URL format',
                        'message': 'QR code URL does not contain valid connection token path'
                    }

                connection_token = path_parts[-1]

                # Validate token format
                if not re.match(r'^[a-f0-9]{64}$', connection_token, re.IGNORECASE):
                    return {
                        'success': False,
                        'error': 'Invalid connection token',
                        'message': f'Token format is invalid: {connection_token[:16]}...'
                    }

                self.logger.info(f"Extracted token: {connection_token[:16]}...")

                # Make registration request
                headers = {
                    **self.session.headers,
                    'X-Device-Token': connection_token,
                    'X-Registration-Method': 'qr_code_scan',
                    'X-Registration-Attempt': str(attempt + 1)
                }

                response = self.session.get(qr_data, headers=headers, timeout=45)
                self.logger.info(f"Registration response: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()

                    if data.get('success') and data.get('deviceRegistered', False):
                        # Extract device information
                        device_info = data.get('device', {})
                        self.device_id = device_info.get('deviceId')
                        self.device_name = device_info.get('deviceName', f'Device {self.device_id}')

                        # Update session headers
                        self.session.headers.update({'X-Device-ID': self.device_id})

                        self.logger.info(f"✅ Device registered successfully: {self.device_id}")
                        return {
                            'success': True,
                            'device_id': self.device_id,
                            'device_name': self.device_name,
                            'sync_endpoint': f"{self.api_base}/calls/sync/{self.device_id}",
                            'status_endpoint': f"{self.api_base}/devices/device/{self.device_id}",
                            'heartbeat_endpoint': f"{self.api_base}/devices/device/{self.device_id}/heartbeat",
                            'message': f'Device registered successfully as {self.device_name}!'
                        }
                    else:
                        error_msg = data.get('message', 'Registration failed - server rejected request')
                        if attempt < 2:  # Not the last attempt
                            self.logger.warning(f"Registration attempt {attempt + 1} rejected, retrying...")
                            time.sleep(2)
                            continue

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
                    if attempt < 2:  # Not the last attempt
                        self.logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}, retrying...")
                        time.sleep(2)
                        continue

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
                self.logger.error(f"Registration attempt {attempt + 1} error: {e}")
                if attempt < 2:  # Not the last attempt
                    time.sleep(3)  # Wait longer between attempts
                    continue

        return {
            'success': False,
            'error': 'Registration failed after retries',
            'message': 'Device registration failed after 3 attempts'
        }

    def sync_calls(self, calls: List[Dict[str, Any]], force: bool = False) -> Dict[str, Any]:
        """Enhanced call sync with retry logic and aggressive sending"""
        if not self.device_id:
            return {
                'success': False,
                'error': 'Device not registered',
                'message': 'Please register device first using QR code'
            }

        if not calls:
            return {
                'success': True,
                'synced_count': 0,
                'message': 'No calls to sync'
            }

        # Multiple retry attempts for sync
        for attempt in range(5):  # More aggressive retry for sync
            try:
                self.logger.info(f"Syncing {len(calls)} calls (attempt {attempt + 1})...")

                payload = {
                    'calls': calls,
                    'syncMetadata': {
                        'attempt': attempt + 1,
                        'timestamp': datetime.now().isoformat(),
                        'callCount': len(calls),
                        'forced': force,
                        'appVersion': '2.0.0'
                    }
                }

                url = f"{self.api_base}/calls/sync/{self.device_id}"

                headers = {
                    **self.session.headers,
                    'X-Device-ID': self.device_id,
                    'X-Sync-Call-Count': str(len(calls)),
                    'X-Sync-Timestamp': datetime.now().isoformat(),
                    'X-Sync-Attempt': str(attempt + 1)
                }

                response = self.session.post(url, json=payload, headers=headers, timeout=120)

                if response.status_code in [200, 207]:
                    data = response.json()
                    sync_metrics = data.get('syncMetrics', {})

                    self.last_successful_sync = datetime.now()
                    self.connection_healthy = True

                    synced_count = sync_metrics.get('syncedCount', 0)
                    self.logger.info(f"✅ Sync completed (attempt {attempt + 1}): {synced_count} synced")

                    return {
                        'success': True,
                        'synced_count': synced_count,
                        'duplicate_count': sync_metrics.get('duplicateCount', 0),
                        'error_count': sync_metrics.get('errorCount', 0),
                        'success_rate': sync_metrics.get('successRate', 'N/A'),
                        'message': f"Successfully synced {synced_count} calls"
                    }
                else:
                    self.logger.warning(f"Sync attempt {attempt + 1} failed: HTTP {response.status_code}")
                    if attempt < 4:  # Not the last attempt
                        wait_time = (attempt + 1) * 2  # Progressive backoff
                        time.sleep(wait_time)
                        continue

            except Exception as e:
                self.logger.error(f"Sync attempt {attempt + 1} error: {e}")
                if attempt < 4:  # Not the last attempt
                    wait_time = (attempt + 1) * 3  # Progressive backoff
                    time.sleep(wait_time)
                    continue

        # All attempts failed
        self.connection_healthy = False
        return {
            'success': False,
            'error': 'Sync failed after retries',
            'message': 'Call sync failed after 5 attempts'
        }

    def send_heartbeat(self, status_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send heartbeat with retry logic"""
        if not self.device_id:
            return {'success': False, 'message': 'Device not registered'}

        for attempt in range(3):
            try:
                url = f"{self.api_base}/devices/device/{self.device_id}/heartbeat"

                heartbeat_data = {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'active',
                    'appVersion': '2.0.0',
                    'permissions': {
                        'callLog': ANDROID_AVAILABLE,
                        'phone': ANDROID_AVAILABLE,
                        'storage': True,
                        'camera': SCANNER_AVAILABLE
                    },
                    'batteryLevel': self._get_battery_level(),
                    'networkType': self._get_network_type(),
                    'lastCallSync': self.last_successful_sync.isoformat() if self.last_successful_sync else None,
                    'connectionHealthy': self.connection_healthy,
                    'heartbeatAttempt': attempt + 1,
                    **(status_data or {})
                }

                response = self.session.post(url, json=heartbeat_data, timeout=30)

                if response.status_code == 200:
                    self.connection_healthy = True
                    return {
                        'success': True,
                        'message': 'Heartbeat sent successfully',
                        'server_instructions': response.json().get('serverInstructions', {})
                    }
                else:
                    if attempt < 2:
                        time.sleep(2)
                        continue

            except Exception as e:
                self.logger.error(f"Heartbeat attempt {attempt + 1} error: {e}")
                if attempt < 2:
                    time.sleep(2)
                    continue

        self.connection_healthy = False
        return {
            'success': False,
            'error': 'Heartbeat failed after retries',
            'message': 'Heartbeat failed after 3 attempts'
        }

    def _get_battery_level(self) -> int:
        """Get battery level"""
        if ANDROID_AVAILABLE:
            try:
                activity = PythonActivity.mActivity
                context = activity.getApplicationContext()
                battery_manager = context.getSystemService(Context.BATTERY_SERVICE)
                if battery_manager:
                    return int(battery_manager.getIntProperty(4))
            except Exception:
                pass
        return -1

    def _get_network_type(self) -> str:
        """Get network type"""
        if ANDROID_AVAILABLE:
            try:
                activity = PythonActivity.mActivity
                context = activity.getApplicationContext()
                connectivity_manager = context.getSystemService(Context.CONNECTIVITY_SERVICE)
                if connectivity_manager:
                    active_network = connectivity_manager.getActiveNetwork()
                    if active_network:
                        network_capabilities = connectivity_manager.getNetworkCapabilities(active_network)
                        if network_capabilities:
                            if network_capabilities.hasTransport(1):
                                return 'wifi'
                            elif network_capabilities.hasTransport(0):
                                return 'cellular'
            except Exception:
                pass
        return 'unknown'


class CallCard(MDCard):
    """Enhanced call card with better visibility and real-time updates"""

    def __init__(self, call_data: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.call_data = call_data
        self.setup_ui()

    def setup_ui(self):
        """Setup enhanced call card UI"""
        self.size_hint_y = None
        self.height = dp(90)
        self.padding = dp(16)
        self.spacing = dp(8)
        self.elevation = 3
        self.radius = [dp(8)]

        # Color coding based on call type
        call_type = self.call_data.get('callType', 'unknown')

        if call_type == 'missed':
            self.md_bg_color = (1, 0.9, 0.9, 1)  # Light red
        elif call_type == 'incoming':
            self.md_bg_color = (0.9, 1, 0.9, 1)  # Light green
        elif call_type == 'outgoing':
            self.md_bg_color = (0.9, 0.9, 1, 1)  # Light blue
        else:
            self.md_bg_color = (0.95, 0.95, 0.95, 1)  # Light gray

        # Main layout
        main_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(16)
        )

        # Call type icon with better visibility
        icon_name = {
            'incoming': 'phone-incoming',
            'outgoing': 'phone-outgoing',
            'missed': 'phone-missed',
            'rejected': 'phone-hangup',
            'blocked': 'phone-cancel'
        }.get(call_type, 'phone')

        icon_color = {
            'incoming': (0.2, 0.8, 0.2, 1),  # Bright green
            'outgoing': (0.2, 0.2, 0.8, 1),  # Bright blue
            'missed': (0.8, 0.2, 0.2, 1),  # Bright red
            'rejected': (1, 0.5, 0, 1),  # Orange
            'blocked': (0.6, 0.1, 0.1, 1)  # Dark red
        }.get(call_type, (0.5, 0.5, 0.5, 1))

        icon = MDIconButton(
            icon=icon_name,
            theme_icon_color='Custom',
            icon_color=icon_color,
            size_hint=(None, None),
            size=(dp(40), dp(40))
        )

        # Call info layout
        info_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(4)
        )

        # Contact name or phone number (larger text)
        contact_name = self.call_data.get('contactName') or self.call_data.get('phoneNumber', 'Unknown')
        name_label = MDLabel(
            text=contact_name,
            font_style='Subtitle1',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(24),
            bold=True
        )

        # Phone number if different from name
        phone_number = self.call_data.get('phoneNumber', '')
        if self.call_data.get('contactName') and phone_number != contact_name:
            phone_label = MDLabel(
                text=phone_number,
                font_style='Body2',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(16)
            )
            info_layout.add_widget(phone_label)

        # Time and duration info
        timestamp_str = self.call_data.get('timestamp', '')
        try:
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                time_str = dt.strftime('%m/%d %H:%M')
            else:
                time_str = 'Unknown time'
        except Exception:
            time_str = 'Unknown time'

        duration = self.call_data.get('duration', 0)
        if duration > 0:
            if duration >= 3600:  # More than 1 hour
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                seconds = duration % 60
                duration_str = f"{hours}h {minutes}m {seconds}s"
            elif duration >= 60:
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}m {seconds}s"
            else:
                duration_str = f"{duration}s"
        else:
            duration_str = "No answer" if call_type in ['missed', 'rejected'] else "0s"

        # Status indicator
        sync_status = "✅ Synced" if self.call_data.get('synced') else "⏳ Pending"
        time_info = f"{time_str} • {duration_str} • {sync_status}"

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
    """Enhanced status card with real-time updates and better visibility"""

    def __init__(self, title: str, value: str, icon: str = None, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.value = value
        self.icon = icon
        self.value_label = None
        self.setup_ui()

    def setup_ui(self):
        """Setup enhanced status card UI"""
        self.size_hint_y = None
        self.height = dp(80)
        self.padding = dp(12)
        self.elevation = 2
        self.radius = [dp(8)]

        layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(8)
        )

        # Icon if provided
        if self.icon:
            icon_widget = MDIconButton(
                icon=self.icon,
                size_hint=(None, None),
                size=(dp(24), dp(24)),
                pos_hint={'center_y': 0.5}
            )
            layout.add_widget(icon_widget)

        # Text layout
        text_layout = MDBoxLayout(
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
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(28),
            bold=True
        )

        text_layout.add_widget(title_label)
        text_layout.add_widget(self.value_label)
        layout.add_widget(text_layout)

        self.add_widget(layout)

    def update_value(self, new_value: str, color=None):
        """Update card value with optional color"""
        self.value = new_value
        if self.value_label:
            self.value_label.text = str(new_value)
            if color:
                self.value_label.theme_text_color = 'Custom'
                self.value_label.text_color = color


class MainScreen(MDScreen):
    """Enhanced main screen with real-time call log updates and auto-sync"""

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
        self.refresh_button = None
        self.last_displayed_calls = []
        self.setup_ui()

        # Aggressive UI update schedule
        Clock.schedule_interval(self.update_ui, 10)  # Update every 10 seconds
        Clock.schedule_interval(self.check_for_new_calls, 5)  # Check for new calls every 5 seconds

    def setup_ui(self):
        """Setup enhanced main screen UI"""
        main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(8),
            padding=dp(16)
        )

        # Enhanced top app bar
        app_bar = MDTopAppBar(
            title="Kortahun United - Call Tracker",
            elevation=3,
            left_action_items=[["menu", lambda x: self.app.open_settings()]],
            right_action_items=[
                ["refresh", lambda x: self.force_refresh()],
                ["sync", lambda x: self.manual_sync()],
                ["qrcode", lambda x: self.scan_qr()]
            ]
        )

        # Enhanced status cards with icons
        status_layout = MDGridLayout(
            cols=2,
            spacing=dp(8),
            size_hint_y=None,
            height=dp(90)
        )

        self.connection_status_card = StatusCard("Connection", "Checking...", "wifi")
        self.sync_status_card = StatusCard("Last Sync", "Never", "sync")
        self.calls_count_card = StatusCard("Total Calls", "0", "phone-log")
        self.device_status_card = StatusCard("Device Status", "Unknown", "cellphone")

        status_layout.add_widget(self.connection_status_card)
        status_layout.add_widget(self.sync_status_card)
        status_layout.add_widget(self.calls_count_card)
        status_layout.add_widget(self.device_status_card)

        # Enhanced recent calls section with live indicator
        calls_header_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(8)
        )

        calls_label = MDLabel(
            text="Recent Calls (Live)",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_x=0.7
        )

        # Live indicator
        self.live_indicator = MDIconButton(
            icon="circle",
            theme_icon_color='Custom',
            icon_color=(0, 1, 0, 1),
            size_hint=(None, None),
            size=(dp(24), dp(24))
        )

        calls_header_layout.add_widget(calls_label)
        calls_header_layout.add_widget(self.live_indicator)

        # Enhanced scrollable call list
        self.calls_scroll = MDScrollView()
        self.calls_list = MDBoxLayout(
            orientation='vertical',
            spacing=dp(6),
            size_hint_y=None,
            height=dp(0)
        )

        self.calls_scroll.add_widget(self.calls_list)

        # Enhanced action buttons
        buttons_layout = MDBoxLayout(
            orientation='horizontal',
            spacing=dp(8),
            size_hint_y=None,
            height=dp(50),
            padding=[0, dp(8), 0, 0]
        )

        sync_button = MDRaisedButton(
            text="Force Sync",
            on_release=self.manual_sync,
            size_hint_x=0.3,
            md_bg_color=(0.2, 0.7, 0.2, 1)
        )

        self.refresh_button = MDRaisedButton(
            text="Refresh",
            on_release=self.force_refresh,
            size_hint_x=0.25,
            md_bg_color=(0.2, 0.2, 0.7, 1)
        )

        qr_button = MDRaisedButton(
            text="Scan QR",
            on_release=self.scan_qr,
            size_hint_x=0.25,
            md_bg_color=(0.7, 0.2, 0.7, 1)
        )

        auto_sync_button = MDFlatButton(
            text="Auto: ON" if self.app.auto_sync_enabled else "Auto: OFF",
            on_release=self.toggle_auto_sync,
            size_hint_x=0.2
        )

        buttons_layout.add_widget(sync_button)
        buttons_layout.add_widget(self.refresh_button)
        buttons_layout.add_widget(qr_button)
        buttons_layout.add_widget(auto_sync_button)

        # Add all widgets to main layout
        main_layout.add_widget(app_bar)
        main_layout.add_widget(status_layout)
        main_layout.add_widget(calls_header_layout)
        main_layout.add_widget(self.calls_scroll)
        main_layout.add_widget(buttons_layout)

        self.add_widget(main_layout)

        # Initial aggressive data load
        Clock.schedule_once(self.initial_load, 0.2)

    def initial_load(self, dt):
        """Aggressive initial data loading"""
        threading.Thread(target=self._initial_load_thread, daemon=True).start()

    def _initial_load_thread(self):
        """Enhanced initial loading"""
        # Test connection immediately
        connection_result = self.app.backend_api.test_connection()
        Clock.schedule_once(lambda dt: self.update_connection_status(connection_result), 0)

        # Load call logs aggressively
        self.force_refresh()

        # Start auto sync if device is registered
        if self.app.backend_api.device_id:
            Clock.schedule_once(lambda dt: self.app.ensure_auto_sync_running(), 1)

    @mainthread
    def update_connection_status(self, result):
        """Update connection status with color coding"""
        if result['success']:
            self.connection_status_card.update_value("Connected", (0, 0.8, 0, 1))
        else:
            self.connection_status_card.update_value("Failed", (0.8, 0, 0, 1))

    def force_refresh(self, *args):
        """Force refresh with visual feedback"""
        # Visual feedback
        if self.refresh_button:
            self.refresh_button.text = "Refreshing..."
            self.refresh_button.disabled = True

        threading.Thread(target=self._force_refresh_thread, daemon=True).start()

    def _force_refresh_thread(self):
        """Force refresh in background with aggressive data fetching"""
        try:
            # Get fresh call logs
            calls = self.app.call_manager.get_call_logs(limit=50, force_refresh=True)

            # Update UI immediately
            Clock.schedule_once(lambda dt: self.update_calls_display(calls), 0)
            Clock.schedule_once(lambda dt: self.update_status_cards(calls), 0)

            # Trigger sync if auto-sync is enabled and device is registered
            if self.app.auto_sync_enabled and self.app.backend_api.device_id and calls:
                sync_result = self.app.backend_api.sync_calls(calls, force=True)
                if sync_result['success']:
                    Clock.schedule_once(
                        lambda dt: SimpleNotification.show_message(f"Auto-synced {sync_result['synced_count']} calls"),
                        0
                    )

        except Exception as e:
            self.app.logger.error(f"Error in force refresh: {e}")
        finally:
            # Reset button
            Clock.schedule_once(self._reset_refresh_button, 0)

    @mainthread
    def _reset_refresh_button(self, dt):
        """Reset refresh button"""
        if self.refresh_button:
            self.refresh_button.text = "Refresh"
            self.refresh_button.disabled = False

    def check_for_new_calls(self, dt):
        """Check for new calls periodically"""
        if not ANDROID_AVAILABLE:
            return

        threading.Thread(target=self._check_new_calls_thread, daemon=True).start()

    def _check_new_calls_thread(self):
        """Check for new calls in background"""
        try:
            current_calls = self.app.call_manager.get_call_logs(limit=10)

            # Compare with last displayed calls
            if len(current_calls) != len(self.last_displayed_calls):
                # New calls detected
                Clock.schedule_once(lambda dt: self.update_calls_display(current_calls), 0)
                Clock.schedule_once(lambda dt: self.update_status_cards(current_calls), 0)

                # Trigger immediate sync if enabled
                if self.app.auto_sync_enabled and self.app.backend_api.device_id:
                    sync_result = self.app.backend_api.sync_calls(current_calls)
                    if sync_result['success']:
                        Clock.schedule_once(
                            lambda dt: SimpleNotification.show_message(
                                f"📞 New calls synced: {sync_result['synced_count']}"),
                            0
                        )

        except Exception as e:
            self.app.logger.error(f"Error checking for new calls: {e}")

    @mainthread
    def update_calls_display(self, calls):
        """Enhanced calls display with better visibility"""
        # Clear existing calls
        self.calls_list.clear_widgets()
        self.last_displayed_calls = calls.copy()

        if not calls:
            no_calls_card = MDCard(
                size_hint_y=None,
                height=dp(60),
                padding=dp(16),
                elevation=1,
                radius=[dp(8)]
            )

            no_calls_label = MDLabel(
                text="No calls found" if ANDROID_AVAILABLE else "Android not available - cannot access call logs",
                halign='center',
                font_style='Body1',
                theme_text_color='Secondary'
            )

            no_calls_card.add_widget(no_calls_label)
            self.calls_list.add_widget(no_calls_card)
            self.calls_list.height = dp(70)
        else:
            # Show recent calls with enhanced cards
            recent_calls = calls[:15]  # Show more calls

            for call in recent_calls:
                call_card = CallCard(call)
                self.calls_list.add_widget(call_card)

            # Update list height
            self.calls_list.height = len(self.calls_list.children) * dp(96)

        # Update live indicator
        self.live_indicator.icon_color = (0, 1, 0, 1) if calls else (0.5, 0.5, 0.5, 1)

    @mainthread
    def update_status_cards(self, calls):
        """Enhanced status cards update"""
        # Update calls count with color
        count = len(calls)
        color = (0, 0.8, 0, 1) if count > 0 else (0.5, 0.5, 0.5, 1)
        self.calls_count_card.update_value(str(count), color)

        # Enhanced last sync display
        try:
            if self.app.storage.exists('app_settings'):
                settings = self.app.storage.get('app_settings')
                last_sync = settings.get('last_sync_time')
                if last_sync:
                    sync_dt = datetime.fromisoformat(last_sync)
                    time_diff = datetime.now() - sync_dt

                    if time_diff.total_seconds() < 60:
                        sync_text = "Just now"
                        sync_color = (0, 0.8, 0, 1)
                    elif time_diff.total_seconds() < 3600:
                        minutes_ago = int(time_diff.total_seconds() / 60)
                        sync_text = f"{minutes_ago}m ago"
                        sync_color = (0, 0.6, 0, 1) if minutes_ago < 10 else (0.8, 0.6, 0, 1)
                    else:
                        hours_ago = int(time_diff.total_seconds() / 3600)
                        sync_text = f"{hours_ago}h ago"
                        sync_color = (0.8, 0.4, 0, 1)

                    self.sync_status_card.update_value(sync_text, sync_color)
                else:
                    self.sync_status_card.update_value("Never", (0.8, 0, 0, 1))
            else:
                self.sync_status_card.update_value("Never", (0.8, 0, 0, 1))
        except Exception:
            self.sync_status_card.update_value("Error", (0.8, 0, 0, 1))

        # Enhanced device status
        try:
            if self.app.storage.exists('device_info'):
                device_info = self.app.storage.get('device_info')
                device_id = device_info.get('device_id')
                if device_id:
                    self.device_status_card.update_value("Registered", (0, 0.8, 0, 1))
                else:
                    self.device_status_card.update_value("Not Registered", (0.8, 0.6, 0, 1))
            else:
                self.device_status_card.update_value("Not Registered", (0.8, 0.6, 0, 1))
        except Exception:
            self.device_status_card.update_value("Error", (0.8, 0, 0, 1))

    def manual_sync(self, *args):
        """Enhanced manual sync with better feedback"""
        SimpleNotification.show_info("Starting manual sync...")
        threading.Thread(target=self._manual_sync_thread, daemon=True).start()

    def _manual_sync_thread(self):
        """Enhanced manual sync with retry logic"""
        try:
            if not self.app.backend_api.device_id:
                Clock.schedule_once(
                    lambda dt: SimpleNotification.show_error("❌ Device not registered. Scan QR code first."), 0)
                return

            # Get latest calls
            calls = self.app.call_manager.get_call_logs(limit=1000, force_refresh=True)

            if not calls:
                Clock.schedule_once(lambda dt: SimpleNotification.show_info("ℹ️ No calls to sync"), 0)
                return

            # Sync with enhanced retry
            result = self.app.backend_api.sync_calls(calls, force=True)

            if result['success']:
                self.app.update_app_setting('last_sync_time', datetime.now().isoformat())

                sync_msg = f"✅ Synced {result['synced_count']} calls"
                if result['duplicate_count'] > 0:
                    sync_msg += f" ({result['duplicate_count']} duplicates)"

                Clock.schedule_once(lambda dt: SimpleNotification.show_message(sync_msg), 0)
                Clock.schedule_once(lambda dt: self.update_status_cards(calls), 0.5)
            else:
                error_msg = f"❌ Sync failed: {result.get('message', 'Unknown error')}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_msg), 0)

        except Exception as e:
            error_message = f"❌ Sync error: {str(e)}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def scan_qr(self, *args):
        """Enhanced QR scanning"""
        self.app.start_qr_scan()

    def toggle_auto_sync(self, *args):
        """Toggle auto sync"""
        self.app.auto_sync_enabled = not self.app.auto_sync_enabled

        # Update button text
        for child in self.children[0].children[0].children:  # Access button layout
            if isinstance(child, MDFlatButton) and "Auto:" in child.text:
                child.text = "Auto: ON" if self.app.auto_sync_enabled else "Auto: OFF"
                break

        # Start/stop auto sync
        if self.app.auto_sync_enabled:
            self.app.ensure_auto_sync_running()
            SimpleNotification.show_message("✅ Auto-sync enabled")
        else:
            SimpleNotification.show_info("⏸️ Auto-sync disabled")

    def update_ui(self, dt):
        """Enhanced periodic UI updates"""
        # Update connection status
        threading.Thread(target=self._update_connection_status_thread, daemon=True).start()

    def _update_connection_status_thread(self):
        """Update connection status in background"""
        result = self.app.backend_api.test_connection()
        Clock.schedule_once(lambda dt: self.update_connection_status(result), 0)


class QRInputDialog:
    """Enhanced QR input dialog with better validation"""

    def __init__(self, app_instance, callback):
        self.app = app_instance
        self.callback = callback
        self.dialog = None
        self.qr_input = None

    def show(self):
        """Show enhanced QR input dialog"""
        # QR input field
        self.qr_input = MDTextField(
            hint_text="Paste the complete QR code URL here",
            multiline=True,
            size_hint_y=None,
            height=dp(100),
            helper_text="URL should start with https://kortahununited...",
            helper_text_mode="persistent"
        )

        # Content layout
        content = MDBoxLayout(
            orientation='vertical',
            spacing=dp(16),
            size_hint_y=None,
            height=dp(280)
        )

        # Enhanced instructions
        instruction_label = MDLabel(
            text="📱 DEVICE REGISTRATION STEPS:\n\n1. Open web dashboard in browser\n2. Generate new QR code for device\n3. Copy the COMPLETE URL from QR code\n4. Paste URL below (must start with https://)\n5. Click Register to connect device",
            size_hint_y=None,
            height=dp(140),
            font_style='Body2'
        )

        # Test URL button
        test_button = MDFlatButton(
            text="Test Connection First",
            on_release=self.test_connection
        )

        content.add_widget(instruction_label)
        content.add_widget(self.qr_input)
        content.add_widget(test_button)

        self.dialog = MDDialog(
            title="📱 Register Device v2.0",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=self.close_dialog
                ),
                MDRaisedButton(
                    text="REGISTER DEVICE",
                    on_release=self.register_device,
                    md_bg_color=(0.2, 0.7, 0.2, 1)
                ),
            ],
        )

        self.dialog.open()

    def test_connection(self, *args):
        """Test connection before registration"""
        SimpleNotification.show_info("Testing connection...")
        threading.Thread(target=self._test_connection_thread, daemon=True).start()

    def _test_connection_thread(self):
        """Test connection in background"""
        result = self.app.backend_api.test_connection()
        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("✅ Connection successful!"), 0)
        else:
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(f"❌ Connection failed: {result['message']}"),
                                0)

    def close_dialog(self, *args):
        """Close dialog"""
        if self.dialog:
            self.dialog.dismiss()

    def register_device(self, *args):
        """Enhanced device registration with validation"""
        qr_data = self.qr_input.text.strip()

        # Enhanced validation
        if not qr_data:
            SimpleNotification.show_error("❌ Please enter QR code URL")
            return

        if not qr_data.startswith('https://'):
            SimpleNotification.show_error("❌ URL must start with https://")
            return

        if 'kortahununited' not in qr_data.lower():
            SimpleNotification.show_error("❌ Invalid Kortahun United URL")
            return

        if '/api/devices/connect/' not in qr_data:
            SimpleNotification.show_error("❌ Invalid registration URL format")
            return

        # Close dialog and start registration
        self.close_dialog()

        # Enhanced registration feedback
        SimpleNotification.show_info("🔄 Registering device...")

        # Register in background with callback
        threading.Thread(target=self._register_device_thread, args=(qr_data,), daemon=True).start()

    def _register_device_thread(self, qr_data: str):
        """Enhanced device registration in background"""
        try:
            result = self.app.backend_api.register_device_from_qr(qr_data)

            if result['success']:
                device_id = result['device_id']
                device_name = result.get('device_name', f'Device {device_id}')

                # Store device information
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

                # Trigger callback
                if self.callback:
                    Clock.schedule_once(lambda dt: self.callback(result), 0)

                # Start services
                Clock.schedule_once(lambda dt: self.app.start_post_registration_services(), 1)

            else:
                error_msg = result.get('message', 'Registration failed')
                error_message = f"❌ Registration failed: {error_msg}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

        except Exception as e:
            error_message = f"❌ Registration error: {str(e)}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)


class KortahunUnitedApp(MDApp):
    """Enhanced application class - Version 2.0.0 - Full Auto-Sync & QR Scanner"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = "Kortahun United Call Tracker"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.accent_palette = "Green"
        self.theme_cls.theme_style = "Light"

        # Initialize components
        self.logger = self.setup_logging()
        self.storage = None
        self.call_manager = CallLogManager()
        self.backend_api = BackendAPI()
        self.qr_scanner = None

        # Enhanced auto sync settings
        self.auto_sync_enabled = True
        self.sync_interval = 120  # 2 minutes - more aggressive
        self.heartbeat_interval = 45  # 45 seconds
        self.call_check_interval = 10  # Check for new calls every 10 seconds

        # Background threads with better management
        self.auto_sync_thread = None
        self.heartbeat_thread = None
        self.call_monitor_thread = None
        self.running = True

        # Sync statistics
        self.total_synced_calls = 0
        self.last_sync_time = None
        self.sync_failures = 0

    def build(self):
        """Build the enhanced application UI"""
        self.logger.info("🚀 Building Kortahun United app (Version 2.0.0 - Enhanced Auto-Sync)...")

        # Setup storage and load settings
        self.setup_storage()
        self.load_app_settings()
        self.load_device_info()

        # Set call manager app instance for callbacks
        self.call_manager.set_app_instance(self)

        # Initialize QR scanner
        self.qr_scanner = QRScannerManager(self)

        # Create enhanced screen manager
        screen_manager = MDScreenManager()

        # Add screens
        main_screen = MainScreen(self)
        settings_screen = SettingsScreen(self)

        screen_manager.add_widget(main_screen)
        screen_manager.add_widget(settings_screen)
        screen_manager.current = 'main'

        # Request permissions immediately on Android
        if ANDROID_AVAILABLE:
            Clock.schedule_once(self.request_permissions_aggressively, 0.5)

        # Start background services
        Clock.schedule_once(self.start_all_background_services, 1)

        self.logger.info("✅ Enhanced app built successfully!")
        return screen_manager

    def setup_logging(self):
        """Enhanced logging setup"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger('KortahunUnited')

        if ANDROID_AVAILABLE:
            try:
                log_path = os.path.join(primary_external_storage_path(), 'KortahunUnited', 'logs')
                os.makedirs(log_path, exist_ok=True)

                file_handler = logging.FileHandler(os.path.join(log_path, 'app.log'))
                file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(file_handler)

                # Also log sync statistics
                sync_handler = logging.FileHandler(os.path.join(log_path, 'sync.log'))
                sync_handler.setFormatter(logging.Formatter('%(asctime)s - SYNC - %(message)s'))

                sync_logger = logging.getLogger('sync_stats')
                sync_logger.addHandler(sync_handler)

                print(f"📝 Enhanced logging to: {log_path}")
            except Exception as e:
                print(f"⚠️ Could not setup file logging: {e}")

        return logger

    def setup_storage(self):
        """Enhanced storage setup"""
        try:
            if ANDROID_AVAILABLE:
                storage_path = os.path.join(primary_external_storage_path(), 'KortahunUnited')
                os.makedirs(storage_path, exist_ok=True)
                storage_file = os.path.join(storage_path, 'settings.json')
            else:
                storage_file = 'kortahun_settings_v2.json'

            self.storage = JsonStore(storage_file)
            self.logger.info(f"📁 Enhanced storage initialized: {storage_file}")

        except Exception as e:
            self.logger.error(f"Storage setup failed: {e}")
            self.storage = JsonStore('fallback_settings_v2.json')

    def load_app_settings(self):
        """Load enhanced app settings"""
        try:
            if self.storage.exists('app_settings'):
                app_settings = self.storage.get('app_settings')

                saved_url = app_settings.get('server_url')
                if saved_url:
                    self.backend_api.base_url = saved_url
                    self.backend_api.api_base = f"{saved_url}/api"

                # Load sync preferences
                self.auto_sync_enabled = app_settings.get('auto_sync_enabled', True)
                self.sync_interval = app_settings.get('sync_interval', 120)
                self.heartbeat_interval = app_settings.get('heartbeat_interval', 45)

                self.logger.info(
                    f"Loaded settings: auto_sync={self.auto_sync_enabled}, sync_interval={self.sync_interval}s")
        except Exception as e:
            self.logger.error(f"Error loading app settings: {e}")

    def load_device_info(self):
        """Load device info with validation"""
        try:
            if self.storage.exists('device_info'):
                device_info = self.storage.get('device_info')

                device_id = device_info.get('device_id')
                device_name = device_info.get('device_name')

                if device_id and len(device_id) > 10:  # Basic validation
                    self.backend_api.device_id = device_id
                    self.backend_api.session.headers.update({'X-Device-ID': device_id})
                    self.logger.info(f"Loaded device: {device_name} ({device_id[:8]}...)")
                else:
                    self.logger.warning("Invalid device ID found, clearing...")
                    self.storage.delete('device_info')

        except Exception as e:
            self.logger.error(f"Error loading device info: {e}")

    def request_permissions_aggressively(self, dt):
        """Request permissions with multiple attempts"""
        if ANDROID_AVAILABLE:
            self.logger.info("📱 Requesting Android permissions aggressively...")

            def request_in_thread():
                success = self.call_manager.request_permissions()
                if success:
                    self.logger.info("✅ Permissions granted successfully")
                    # Immediately try to load call logs
                    Clock.schedule_once(lambda dt: self.trigger_immediate_data_load(), 1)
                else:
                    self.logger.warning("⚠️ Permission request failed")
                    # Retry after delay
                    Clock.schedule_once(lambda dt: self.request_permissions_aggressively(dt), 5)

            threading.Thread(target=request_in_thread, daemon=True).start()

    def trigger_immediate_data_load(self):
        """Trigger immediate data loading after permissions"""

        def load_data():
            calls = self.call_manager.get_call_logs(limit=50, force_refresh=True)
            self.logger.info(f"📞 Loaded {len(calls)} calls after permission grant")

            # Update main screen if available
            main_screen = self.get_main_screen()
            if main_screen:
                Clock.schedule_once(lambda dt: main_screen.update_calls_display(calls), 0)

        threading.Thread(target=load_data, daemon=True).start()

    def start_all_background_services(self, dt):
        """Start all enhanced background services"""
        self.logger.info("🔄 Starting enhanced background services...")

        # Start services if device is registered
        if self.backend_api.device_id:
            self.ensure_auto_sync_running()
            self.start_heartbeat_service()
            self.start_call_monitor()
        else:
            self.logger.info("ℹ️ Device not registered, services will start after registration")

    def ensure_auto_sync_running(self):
        """Ensure auto sync is running with better management"""
        if not self.auto_sync_enabled:
            return

        if self.auto_sync_thread and self.auto_sync_thread.is_alive():
            return  # Already running

        self.auto_sync_thread = threading.Thread(target=self.enhanced_auto_sync_worker, daemon=True)
        self.auto_sync_thread.start()
        self.logger.info("🔄 Enhanced auto sync started")

    def start_heartbeat_service(self):
        """Start enhanced heartbeat service"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return  # Already running

        self.heartbeat_thread = threading.Thread(target=self.enhanced_heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        self.logger.info("💓 Enhanced heartbeat service started")

    def start_call_monitor(self):
        """Start call monitoring service"""
        if self.call_monitor_thread and self.call_monitor_thread.is_alive():
            return  # Already running

        self.call_monitor_thread = threading.Thread(target=self.call_monitor_worker, daemon=True)
        self.call_monitor_thread.start()
        self.logger.info("📞 Call monitor service started")

    def enhanced_auto_sync_worker(self):
        """Enhanced auto sync worker with better error handling"""
        consecutive_failures = 0

        while self.running and self.auto_sync_enabled:
            try:
                if self.backend_api.device_id:
                    self.logger.info("🔄 Performing enhanced auto sync...")

                    # Get latest calls
                    calls = self.call_manager.get_call_logs(limit=1000, force_refresh=True)

                    if calls:
                        result = self.backend_api.sync_calls(calls)

                        if result['success']:
                            synced_count = result.get('synced_count', 0)
                            self.total_synced_calls += synced_count
                            self.last_sync_time = datetime.now()
                            consecutive_failures = 0

                            # Update app settings
                            self.update_app_setting('last_sync_time', self.last_sync_time.isoformat())
                            self.update_app_setting('total_synced_calls', self.total_synced_calls)

                            self.logger.info(
                                f"✅ Auto sync completed: {synced_count} new calls, {self.total_synced_calls} total")

                            # Show notification for significant syncs
                            if synced_count > 0:
                                Clock.schedule_once(
                                    lambda dt: SimpleNotification.show_message(f"📞 Auto-synced {synced_count} calls"),
                                    0
                                )

                        else:
                            consecutive_failures += 1
                            self.sync_failures += 1
                            self.logger.error(
                                f"❌ Auto sync failed (failure #{consecutive_failures}): {result.get('message')}")

                            # Exponential backoff for failures
                            if consecutive_failures > 3:
                                wait_time = min(self.sync_interval * 2, 600)  # Max 10 minutes
                                self.logger.info(
                                    f"⏳ Backing off for {wait_time}s after {consecutive_failures} failures")
                                time.sleep(wait_time)
                                continue

                    else:
                        self.logger.info("ℹ️ No calls available for auto sync")

            except Exception as e:
                consecutive_failures += 1
                self.sync_failures += 1
                self.logger.error(f"❌ Auto sync error (failure #{consecutive_failures}): {e}")

            # Dynamic sleep interval based on failures
            sleep_time = self.sync_interval
            if consecutive_failures > 0:
                sleep_time = min(self.sync_interval * (1 + consecutive_failures * 0.5), 600)

            time.sleep(sleep_time)

    def enhanced_heartbeat_worker(self):
        """Enhanced heartbeat worker"""
        while self.running:
            try:
                if self.backend_api.device_id:
                    # Enhanced heartbeat data
                    status_data = {
                        'totalSyncedCalls': self.total_synced_calls,
                        'syncFailures': self.sync_failures,
                        'lastSyncTime': self.last_sync_time.isoformat() if self.last_sync_time else None,
                        'autoSyncEnabled': self.auto_sync_enabled,
                        'syncInterval': self.sync_interval,
                        'permissionsGranted': self.call_manager.permissions_granted,
                        'callCacheSize': len(self.call_manager._call_cache) if hasattr(self.call_manager,
                                                                                       '_call_cache') else 0
                    }

                    result = self.backend_api.send_heartbeat(status_data)
                    if result['success']:
                        self.logger.info("💓 Enhanced heartbeat sent successfully")

                        # Process server instructions if any
                        instructions = result.get('server_instructions', {})
                        if instructions:
                            self.process_server_instructions(instructions)
                    else:
                        self.logger.warning(f"💔 Heartbeat failed: {result.get('message')}")

            except Exception as e:
                self.logger.error(f"💔 Heartbeat error: {e}")

            time.sleep(self.heartbeat_interval)

    def call_monitor_worker(self):
        """Monitor for new calls and trigger immediate sync"""
        last_call_count = 0

        while self.running:
            try:
                if ANDROID_AVAILABLE and self.call_manager.permissions_granted:
                    # Check current call count
                    current_calls = self.call_manager.get_call_logs(limit=10, force_refresh=False)
                    current_count = len(current_calls)

                    if current_count != last_call_count and last_call_count > 0:
                        self.logger.info(f"📞 New call detected! Count: {last_call_count} -> {current_count}")

                        # Trigger immediate sync if auto-sync is enabled
                        if self.auto_sync_enabled and self.backend_api.device_id:
                            threading.Thread(target=self.immediate_sync_new_calls, daemon=True).start()

                        # Update UI
                        main_screen = self.get_main_screen()
                        if main_screen:
                            Clock.schedule_once(lambda dt: main_screen.force_refresh(), 0)

                    last_call_count = current_count

            except Exception as e:
                self.logger.error(f"📞 Call monitor error: {e}")

            time.sleep(self.call_check_interval)

    def immediate_sync_new_calls(self):
        """Immediate sync for new calls"""
        try:
            self.logger.info("🚀 Triggering immediate sync for new calls")
            calls = self.call_manager.get_call_logs(limit=100, force_refresh=True)

            if calls:
                result = self.backend_api.sync_calls(calls, force=True)
                if result['success']:
                    synced_count = result.get('synced_count', 0)
                    self.logger.info(f"⚡ Immediate sync completed: {synced_count} calls")

                    if synced_count > 0:
                        Clock.schedule_once(
                            lambda dt: SimpleNotification.show_message(f"⚡ New calls synced: {synced_count}"),
                            0
                        )

        except Exception as e:
            self.logger.error(f"Error in immediate sync: {e}")

    def process_server_instructions(self, instructions):
        """Process instructions from server"""
        try:
            # Handle sync interval changes
            if 'syncInterval' in instructions:
                new_interval = instructions['syncInterval']
                if 60 <= new_interval <= 3600:  # Between 1 minute and 1 hour
                    self.sync_interval = new_interval
                    self.update_app_setting('sync_interval', new_interval)
                    self.logger.info(f"📝 Sync interval updated to {new_interval}s by server")

            # Handle forced sync requests
            if instructions.get('forcedSync'):
                self.logger.info("🔄 Server requested forced sync")
                threading.Thread(target=self.immediate_sync_new_calls, daemon=True).start()

        except Exception as e:
            self.logger.error(f"Error processing server instructions: {e}")

    def start_qr_scan(self):
        """Enhanced QR scanning with multiple methods"""

        def on_qr_result(qr_data):
            """Handle QR scan result"""
            self.logger.info(f"📱 QR scan result received: {qr_data[:50]}...")

            # Process registration
            dialog = QRInputDialog(self, self.on_device_registered)
            dialog.qr_input.text = qr_data
            dialog.register_device()

        if ANDROID_AVAILABLE and SCANNER_AVAILABLE:
            # Try camera scanner first
            try:
                self.qr_scanner.scan_qr_code(on_qr_result)
            except Exception as e:
                self.logger.error(f"Camera scanner failed: {e}")
                self.show_qr_input_dialog(on_qr_result)
        else:
            # Fallback to manual input
            self.show_qr_input_dialog(on_qr_result)

    def show_qr_input_dialog(self, callback):
        """Show manual QR input dialog"""
        dialog = QRInputDialog(self, callback)
        dialog.show()

    def on_device_registered(self, registration_result):
        """Handle successful device registration"""
        self.logger.info("🎉 Device registration completed successfully")

        # Start all background services
        self.start_post_registration_services()

        # Trigger initial sync
        Clock.schedule_once(lambda dt: self.trigger_initial_sync(), 2)

    def start_post_registration_services(self):
        """Start services after device registration"""
        self.logger.info("🚀 Starting post-registration services...")

        # Ensure all services are running
        self.ensure_auto_sync_running()
        self.start_heartbeat_service()
        self.start_call_monitor()

        # Send initial heartbeat
        threading.Thread(target=self.send_initial_heartbeat, daemon=True).start()

    def send_initial_heartbeat(self):
        """Send initial heartbeat after registration"""
        try:
            if self.backend_api.device_id:
                result = self.backend_api.send_heartbeat({
                    'status': 'just_registered',
                    'registrationMethod': 'qr_code_scan',
                    'appVersion': '2.0.0',
                    'servicesStarted': True
                })

                if result['success']:
                    self.logger.info("💓 Initial heartbeat sent successfully")
                else:
                    self.logger.warning(f"💔 Initial heartbeat failed: {result.get('message')}")

        except Exception as e:
            self.logger.error(f"💔 Initial heartbeat error: {e}")

    def trigger_initial_sync(self):
        """Trigger initial sync after registration"""

        def initial_sync():
            try:
                self.logger.info("🔄 Starting initial sync after registration...")

                calls = self.call_manager.get_call_logs(limit=1000, force_refresh=True)
                if calls:
                    result = self.backend_api.sync_calls(calls, force=True)
                    if result['success']:
                        synced_count = result.get('synced_count', 0)
                        self.logger.info(f"✅ Initial sync completed: {synced_count} calls")

                        Clock.schedule_once(
                            lambda dt: SimpleNotification.show_message(f"🎉 Initial sync: {synced_count} calls"),
                            0
                        )

                        # Update statistics
                        self.total_synced_calls = synced_count
                        self.last_sync_time = datetime.now()
                        self.update_app_setting('last_sync_time', self.last_sync_time.isoformat())

            except Exception as e:
                self.logger.error(f"Error in initial sync: {e}")

        threading.Thread(target=initial_sync, daemon=True).start()

    def get_main_screen(self):
        """Get main screen reference"""
        try:
            return self.root.get_screen('main')
        except:
            return None

    def update_app_setting(self, key: str, value):
        """Enhanced app setting update"""
        try:
            if self.storage.exists('app_settings'):
                app_settings = self.storage.get('app_settings')
            else:
                app_settings = {}

            app_settings[key] = value
            self.storage.put('app_settings', **app_settings)

        except Exception as e:
            self.logger.error(f"Error updating app setting {key}: {e}")

    def open_settings(self):
        """Open settings screen"""
        self.root.current = 'settings'

    def go_back(self):
        """Go back to main screen"""
        self.root.current = 'main'

    def on_stop(self):
        """Enhanced app stop with proper cleanup"""
        self.logger.info("🛑 Enhanced app stopping...")
        self.running = False

        # Stop all threads gracefully
        threads_to_wait = [
            (self.auto_sync_thread, "auto_sync"),
            (self.heartbeat_thread, "heartbeat"),
            (self.call_monitor_thread, "call_monitor")
        ]

        for thread, name in threads_to_wait:
            if thread and thread.is_alive():
                self.logger.info(f"⏳ Waiting for {name} thread to finish...")
                thread.join(timeout=5)

        self.logger.info("✅ Enhanced app stopped cleanly")


class SettingsScreen(MDScreen):
    """Enhanced settings screen with sync statistics and controls"""

    def __init__(self, app_instance, **kwargs):
        super().__init__(**kwargs)
        self.app = app_instance
        self.name = 'settings'
        self.setup_ui()

    def setup_ui(self):
        """Setup enhanced settings screen"""
        main_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(16),
            padding=dp(16)
        )

        # Enhanced app bar
        app_bar = MDTopAppBar(
            title="Settings & Statistics",
            elevation=3,
            left_action_items=[["arrow-left", lambda x: self.app.go_back()]]
        )

        # Settings content in scroll view
        scroll = MDScrollView()
        settings_layout = MDBoxLayout(
            orientation='vertical',
            spacing=dp(16),
            size_hint_y=None
        )
        settings_layout.bind(minimum_height=settings_layout.setter('height'))

        # Sync Statistics Card
        stats_card = self.create_stats_card()
        settings_layout.add_widget(stats_card)

        # Device Information Card
        device_card = self.create_device_info_card()
        settings_layout.add_widget(device_card)

        # Sync Settings Card
        sync_settings_card = self.create_sync_settings_card()
        settings_layout.add_widget(sync_settings_card)

        # Server Settings Card
        server_card = self.create_server_settings_card()
        settings_layout.add_widget(server_card)

        # Actions Card
        actions_card = self.create_actions_card()
        settings_layout.add_widget(actions_card)

        scroll.add_widget(settings_layout)
        main_layout.add_widget(app_bar)
        main_layout.add_widget(scroll)
        self.add_widget(main_layout)

        # Load current data
        Clock.schedule_once(self.load_current_data, 0.1)

    def create_stats_card(self):
        """Create sync statistics card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(180),
            padding=dp(16),
            elevation=3,
            radius=[dp(8)]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        title = MDLabel(
            text="📊 Sync Statistics",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        self.stats_layout = MDBoxLayout(orientation='vertical', spacing=dp(4))

        layout.add_widget(title)
        layout.add_widget(self.stats_layout)
        card.add_widget(layout)

        return card

    def create_device_info_card(self):
        """Create device information card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(200),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        title = MDLabel(
            text="📱 Device Information",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        self.device_info_layout = MDBoxLayout(orientation='vertical', spacing=dp(4))

        layout.add_widget(title)
        layout.add_widget(self.device_info_layout)
        card.add_widget(layout)

        return card

    def create_sync_settings_card(self):
        """Create sync settings card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(200),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        title = MDLabel(
            text="⚙️ Sync Settings",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        # Auto sync toggle
        auto_sync_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        auto_sync_label = MDLabel(text="Auto Sync:", size_hint_x=0.7)
        self.auto_sync_button = MDRaisedButton(
            text="ON" if self.app.auto_sync_enabled else "OFF",
            size_hint_x=0.3,
            on_release=self.toggle_auto_sync
        )
        auto_sync_layout.add_widget(auto_sync_label)
        auto_sync_layout.add_widget(self.auto_sync_button)

        # Sync interval
        interval_label = MDLabel(
            text=f"Sync Interval: {self.app.sync_interval}s",
            size_hint_y=None,
            height=dp(30)
        )

        # Manual sync button
        manual_sync_btn = MDRaisedButton(
            text="🔄 Force Sync Now",
            size_hint_y=None,
            height=dp(40),
            on_release=self.manual_sync,
            md_bg_color=(0.2, 0.7, 0.2, 1)
        )

        layout.add_widget(title)
        layout.add_widget(auto_sync_layout)
        layout.add_widget(interval_label)
        layout.add_widget(manual_sync_btn)
        card.add_widget(layout)

        return card

    def create_server_settings_card(self):
        """Create server settings card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(150),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        title = MDLabel(
            text="🌐 Server Configuration",
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

        update_btn = MDRaisedButton(
            text="Update Server URL",
            size_hint_y=None,
            height=dp(40),
            on_release=self.update_server_url
        )

        layout.add_widget(title)
        layout.add_widget(self.server_url_field)
        layout.add_widget(update_btn)
        card.add_widget(layout)

        return card

    def create_actions_card(self):
        """Create actions card"""
        card = MDCard(
            size_hint_y=None,
            height=dp(280),
            padding=dp(16),
            elevation=2,
            radius=[dp(8)]
        )

        layout = MDBoxLayout(orientation='vertical', spacing=dp(8))

        title = MDLabel(
            text="🔧 Actions",
            font_style='H6',
            theme_text_color='Primary',
            size_hint_y=None,
            height=dp(30)
        )

        buttons = [
            ("🔍 Test Connection", self.test_connection, (0.2, 0.2, 0.7, 1)),
            ("📱 Register Device", self.show_qr_scanner, (0.7, 0.2, 0.7, 1)),
            ("💓 Send Heartbeat", self.send_heartbeat, (0.7, 0.5, 0.2, 1)),
            ("🗑️ Clear Data", self.clear_data, (0.7, 0.2, 0.2, 1))
        ]

        for text, callback, color in buttons:
            btn = MDRaisedButton(
                text=text,
                size_hint_y=None,
                height=dp(40),
                on_release=callback,
                md_bg_color=color
            )
            layout.add_widget(btn)

        layout.add_widget(title)
        for text, callback, color in buttons:
            btn = MDRaisedButton(
                text=text,
                size_hint_y=None,
                height=dp(40),
                on_release=callback,
                md_bg_color=color
            )
            layout.add_widget(btn)

        card.add_widget(layout)
        return card

    def load_current_data(self, dt):
        """Load current data into UI"""
        self.update_stats_display()
        self.update_device_info_display()

    def update_stats_display(self):
        """Update statistics display"""
        self.stats_layout.clear_widgets()

        stats_data = [
            f"Total Synced: {self.app.total_synced_calls}",
            f"Sync Failures: {self.app.sync_failures}",
            f"Last Sync: {self.app.last_sync_time.strftime('%H:%M:%S') if self.app.last_sync_time else 'Never'}",
            f"Auto Sync: {'✅ ON' if self.app.auto_sync_enabled else '❌ OFF'}",
            f"Connection: {'✅ Healthy' if self.app.backend_api.connection_healthy else '❌ Poor'}"
        ]

        for stat in stats_data:
            label = MDLabel(
                text=stat,
                font_style='Body2',
                size_hint_y=None,
                height=dp(20)
            )
            self.stats_layout.add_widget(label)

    def update_device_info_display(self):
        """Update device information display"""
        self.device_info_layout.clear_widgets()

        try:
            if self.app.storage.exists('device_info'):
                device_info = self.app.storage.get('device_info')
                device_id = device_info.get('device_id', 'Not registered')
                device_name = device_info.get('device_name', 'Unknown')
                registration_time = device_info.get('registration_time')

                device_data = [
                    f"Device ID: {device_id[:12]}..." if len(device_id) > 12 else f"Device ID: {device_id}",
                    f"Device Name: {device_name}",
                    f"Registered: {datetime.fromisoformat(registration_time).strftime('%Y-%m-%d %H:%M') if registration_time else 'Never'}",
                    f"Permissions: {'✅ Granted' if self.app.call_manager.permissions_granted else '❌ Not Granted'}",
                    f"Platform: {platform} | Android: {'✅' if ANDROID_AVAILABLE else '❌'}",
                    f"QR Scanner: {'✅' if SCANNER_AVAILABLE else '❌'}",
                    f"App Version: 2.0.0 Enhanced"
                ]
            else:
                device_data = [
                    "Device ID: Not registered",
                    "Device Name: Unknown",
                    "Status: Registration required",
                    f"Permissions: {'Checking...' if ANDROID_AVAILABLE else 'N/A (Desktop)'}",
                    f"Platform: {platform} | Android: {'✅' if ANDROID_AVAILABLE else '❌'}",
                    f"App Version: 2.0.0 Enhanced"
                ]

            for data in device_data:
                label = MDLabel(
                    text=data,
                    font_style='Body2',
                    size_hint_y=None,
                    height=dp(18)
                )
                self.device_info_layout.add_widget(label)

        except Exception as e:
            error_label = MDLabel(
                text=f"Error loading device info: {str(e)}",
                font_style='Body2',
                theme_text_color='Secondary',
                size_hint_y=None,
                height=dp(20)
            )
            self.device_info_layout.add_widget(error_label)

    def toggle_auto_sync(self, *args):
        """Toggle auto sync setting"""
        self.app.auto_sync_enabled = not self.app.auto_sync_enabled
        self.app.update_app_setting('auto_sync_enabled', self.app.auto_sync_enabled)

        # Update button text
        self.auto_sync_button.text = "ON" if self.app.auto_sync_enabled else "OFF"
        self.auto_sync_button.md_bg_color = (0.2, 0.7, 0.2, 1) if self.app.auto_sync_enabled else (0.7, 0.2, 0.2, 1)

        # Start or notify about auto sync
        if self.app.auto_sync_enabled:
            self.app.ensure_auto_sync_running()
            SimpleNotification.show_message("✅ Auto-sync enabled")
        else:
            SimpleNotification.show_info("⏸️ Auto-sync disabled")

        # Update stats display
        self.update_stats_display()

    def manual_sync(self, *args):
        """Trigger manual sync"""
        SimpleNotification.show_info("🔄 Starting manual sync...")
        threading.Thread(target=self._manual_sync_thread, daemon=True).start()

    def _manual_sync_thread(self):
        """Manual sync in background"""
        try:
            if not self.app.backend_api.device_id:
                Clock.schedule_once(
                    lambda dt: SimpleNotification.show_error("❌ Device not registered. Scan QR code first."), 0)
                return

            calls = self.app.call_manager.get_call_logs(limit=1000, force_refresh=True)

            if not calls:
                Clock.schedule_once(lambda dt: SimpleNotification.show_info("ℹ️ No calls to sync"), 0)
                return

            result = self.app.backend_api.sync_calls(calls, force=True)

            if result['success']:
                synced_count = result.get('synced_count', 0)
                self.app.total_synced_calls += synced_count
                self.app.last_sync_time = datetime.now()
                self.app.update_app_setting('last_sync_time', self.app.last_sync_time.isoformat())

                sync_msg = f"✅ Manual sync: {synced_count} calls"
                if result.get('duplicate_count', 0) > 0:
                    sync_msg += f" ({result['duplicate_count']} duplicates)"

                Clock.schedule_once(lambda dt: SimpleNotification.show_message(sync_msg), 0)
                Clock.schedule_once(self.update_stats_display, 0.5)
            else:
                self.app.sync_failures += 1
                error_msg = f"❌ Manual sync failed: {result.get('message', 'Unknown error')}"
                Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_msg), 0)

        except Exception as e:
            error_message = f"❌ Manual sync error: {str(e)}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def test_connection(self, *args):
        """Test server connection"""
        SimpleNotification.show_info("🔍 Testing connection...")
        threading.Thread(target=self._test_connection_thread, daemon=True).start()

    def _test_connection_thread(self):
        """Test connection in background"""
        result = self.app.backend_api.test_connection()

        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("✅ Connection successful!"), 0)
        else:
            error_msg = result.get('message', 'Unknown error')
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(f"❌ Connection failed: {error_msg}"), 0)

    def show_qr_scanner(self, *args):
        """Show QR scanner"""
        self.app.start_qr_scan()

    def update_server_url(self, *args):
        """Update server URL"""
        new_url = self.server_url_field.text.strip()

        if not new_url.startswith('http'):
            SimpleNotification.show_error("❌ Invalid URL format")
            return

        self.app.backend_api.base_url = new_url
        self.app.backend_api.api_base = f"{new_url}/api"
        self.app.update_app_setting('server_url', new_url)

        SimpleNotification.show_message("✅ Server URL updated")

    def send_heartbeat(self, *args):
        """Send manual heartbeat"""
        threading.Thread(target=self._send_heartbeat_thread, daemon=True).start()

    def _send_heartbeat_thread(self):
        """Send heartbeat in background"""
        if not self.app.backend_api.device_id:
            Clock.schedule_once(lambda dt: SimpleNotification.show_error("❌ Device not registered"), 0)
            return

        result = self.app.backend_api.send_heartbeat({
            'manualHeartbeat': True,
            'triggeredFrom': 'settings_screen'
        })

        if result['success']:
            Clock.schedule_once(lambda dt: SimpleNotification.show_message("💓 Heartbeat sent successfully"), 0)
        else:
            error_message = f"💔 Heartbeat failed: {result.get('message')}"
            Clock.schedule_once(lambda dt: SimpleNotification.show_error(error_message), 0)

    def clear_data(self, *args):
        """Clear all app data with confirmation"""
        confirm_dialog = MDDialog(
            title="⚠️ Clear All Data",
            text="This will remove:\n• Device registration\n• Sync settings\n• All cached data\n\nAre you sure?",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="CLEAR ALL DATA",
                    on_release=lambda x: self.perform_clear_data(confirm_dialog),
                    md_bg_color=(0.8, 0.2, 0.2, 1)
                ),
            ],
        )
        confirm_dialog.open()

    def perform_clear_data(self, dialog):
        """Actually clear the data"""
        dialog.dismiss()

        try:
            # Clear all storage
            keys_to_delete = []
            for key in self.app.storage.keys():
                keys_to_delete.append(key)

            for key in keys_to_delete:
                if self.app.storage.exists(key):
                    self.app.storage.delete(key)

            # Reset app state
            self.app.backend_api.device_id = None
            self.app.backend_api.device_name = None
            self.app.total_synced_calls = 0
            self.app.last_sync_time = None
            self.app.sync_failures = 0
            self.app.auto_sync_enabled = True

            # Update UI
            self.load_current_data(None)
            SimpleNotification.show_message("✅ All data cleared successfully")

        except Exception as e:
            error_message = f"❌ Error clearing data: {str(e)}"
            SimpleNotification.show_error(error_message)


if __name__ == '__main__':
    # Enhanced startup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=" * 80)
    print("🚀 KORTAHUN UNITED CALL TRACKING APP - VERSION 2.0.0 ENHANCED")
    print("=" * 80)
    print(f"📱 Platform: {platform}")
    print(f"🤖 Android Available: {'✅ YES' if ANDROID_AVAILABLE else '❌ NO'}")
    print(f"📷 QR Scanner Available: {'✅ YES' if SCANNER_AVAILABLE else '❌ NO'}")
    print()
    print("🔥 VERSION 2.0.0 ENHANCED FEATURES:")
    print("   ✅ AUTOMATIC CALL LOG VISIBILITY - Real-time display")
    print("   ✅ AUTOMATIC SYNC - Runs every 2 minutes when registered")
    print("   ✅ INSTANT SYNC - New calls detected and synced immediately")
    print("   ✅ REAL QR SCANNER - Camera-based QR code scanning")
    print("   ✅ ENHANCED UI - Better visibility, colors, and real-time updates")
    print("   ✅ AGGRESSIVE RETRY LOGIC - Multiple attempts for all operations")
    print("   ✅ BACKGROUND MONITORING - Continuous call monitoring")
    print("   ✅ SYNC STATISTICS - Track sync performance and failures")
    print("   ✅ SMART NOTIFICATIONS - Immediate feedback for all actions")
    print("   ✅ CONNECTION HEALTH - Monitor and display connection status")
    print("   ✅ ENHANCED HEARTBEAT - Detailed device status reporting")
    print("   ✅ BRUTE FORCE SYNC - Ensures data reaches server")
    print()
    print("🛡️  RELIABILITY FEATURES:")
    print("   • 5 retry attempts for sync operations")
    print("   • 3 retry attempts for registration")
    print("   • Exponential backoff on failures")
    print("   • Automatic service restart on errors")
    print("   • Real-time call monitoring every 10 seconds")
    print("   • Immediate sync on new call detection")
    print("   • Connection health monitoring")
    print("   • Comprehensive error logging")
    print()

    if not ANDROID_AVAILABLE:
        print("⚠️  WARNING: Android not available")
        print("   • Call logs cannot be retrieved")
        print("   • QR scanner will use manual input")
        print("   • App will work for testing server connection only")
        print()
    else:
        print("✅ Android available - Full functionality enabled")
        if not SCANNER_AVAILABLE:
            print("⚠️  QR Scanner will use manual input fallback")
        print()

    print("🎯 AUTO-SYNC WORKFLOW:")
    print("   1. Register device using QR code scanner")
    print("   2. App automatically requests call log permissions")
    print("   3. Auto-sync starts immediately after registration")
    print("   4. Call logs are monitored every 10 seconds")
    print("   5. New calls trigger immediate sync")
    print("   6. Regular sync runs every 2 minutes")
    print("   7. All sync operations have 5 retry attempts")
    print("   8. Heartbeat maintains connection every 45 seconds")
    print()
    print("📞 CALL LOG FEATURES:")
    print("   • Real-time display of recent calls")
    print("   • Color-coded call types (missed=red, incoming=green, etc.)")
    print("   • Sync status indicators")
    print("   • Live update notifications")
    print("   • Support for large call volumes (1000+ calls)")
    print()

    # Create and run the enhanced app
    try:
        print("🔧 Initializing enhanced app...")
        app = KortahunUnitedApp()
        print("🚀 Starting enhanced app...")
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 App interrupted by user")
    except Exception as e:
        print(f"💥 App crashed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("👋 Enhanced app terminated")
        print("=" * 80)