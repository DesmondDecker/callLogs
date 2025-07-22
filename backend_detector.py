# backend_detector.py - Production-ready backend detection and device registration

import requests
import json
import time
from typing import Optional, Dict, List, Tuple
from urllib.parse import urljoin
from config import AppConfig, StorageManager, is_android, get_platform_name

class BackendDetector:
    """
    Robust backend detection that works in production and development
    """
    
    def __init__(self, timeout: int = 10, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        
        # Set user agent for better server compatibility
        self.session.headers.update({
            'User-Agent': f'KortahunUnited/2.0.0 ({get_platform_name()})',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def test_connectivity(self) -> bool:
        """
        Test basic internet connectivity
        """
        print("🌐 Testing connectivity...")
        
        connectivity_urls = AppConfig.CONNECTIVITY_TEST_URLS
        successful_tests = 0
        
        for url in connectivity_urls:
            try:
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:
                    successful_tests += 1
                    print(f"  ✅ {url}: {response.status_code}")
                else:
                    print(f"  ❌ {url}: {response.status_code}")
            except Exception as e:
                print(f"  ❌ {url}: {str(e)}")
        
        connectivity_ratio = successful_tests / len(connectivity_urls)
        is_connected = connectivity_ratio >= 0.5  # Need at least 50% success
        
        print(f"[Connectivity] {successful_tests}/{len(connectivity_urls)} tests passed")
        
        if is_connected:
            print("✅ Internet connectivity confirmed")
        else:
            print("❌ Poor internet connectivity")
        
        return is_connected
    
    def test_backend_url(self, base_url: str) -> Tuple[bool, Optional[Dict]]:
        """
        Test a specific backend URL
        """
        test_endpoints = [
            "",  # Root API endpoint
            "/devices",  # Device management endpoint
            "/health"  # Health check endpoint
        ]
        
        print(f"Testing backend URL: {base_url}")
        
        for endpoint in test_endpoints:
            test_url = urljoin(base_url.rstrip('/') + '/', endpoint.lstrip('/'))
            print(f"  -> Trying endpoint: {test_url}")
            
            try:
                response = self.session.get(test_url, timeout=self.timeout)
                print(f"  -> Response: {response.status_code} - {response.reason}")
                print(f"  -> Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        print(f"  -> JSON Response: {json.dumps(json_data, indent=2)}")
                        
                        # Check if this looks like our API
                        if self._is_valid_api_response(json_data, endpoint):
                            return True, json_data
                        
                    except ValueError:
                        print("  -> Not JSON response, but server is responding")
                        if endpoint == "":  # Root endpoint might not be JSON
                            continue
                
            except requests.exceptions.Timeout:
                print(f"  -> Timeout after {self.timeout}s")
            except requests.exceptions.ConnectionError:
                print(f"  -> Connection failed")
            except Exception as e:
                print(f"  -> Error: {str(e)}")
        
        return False, None
    
    def _is_valid_api_response(self, json_data: dict, endpoint: str) -> bool:
        """
        Check if the JSON response indicates our API
        """
        # Root endpoint should have API info
        if endpoint == "":
            return (
                "message" in json_data and
                ("Device" in json_data.get("message", "") or 
                 "API" in json_data.get("message", "")) and
                ("version" in json_data or "endpoints" in json_data)
            )
        
        # Device endpoint should have device info
        elif endpoint == "/devices":
            return (
                "message" in json_data and
                "endpoints" in json_data and
                "version" in json_data
            )
        
        # Health endpoint
        elif endpoint == "/health":
            return (
                "status" in json_data and
                json_data.get("status") in ["healthy", "active"]
            )
        
        return False
    
    def detect_backend(self) -> Optional[str]:
        """
        Detect available backend URL
        """
        print("🔍 Detecting backend...")
        print("Starting comprehensive backend URL detection...")
        
        # First test connectivity
        if not self.test_connectivity():
            print("❌ No internet connectivity - cannot detect backend")
            return None
        
        # Get API URLs to test
        api_urls = AppConfig.get_api_urls()
        
        print(f"Testing {len(api_urls)} potential backend URLs...")
        
        for api_url in api_urls:
            print(f"\n🔗 Testing: {api_url}")
            
            is_available, api_info = self.test_backend_url(api_url)
            
            if is_available:
                print(f"✅ Backend found: {api_url}")
                
                # Save successful URL for future use
                StorageManager.save('api_url', api_url)
                
                return api_url
            else:
                print(f"❌ Backend not available: {api_url}")
        
        print("❌ No backend URLs available")
        return None
    
    def register_device(self, api_url: str, user_id: str = None, device_id: str = None) -> bool:
        """
        Register device with the backend
        """
        if not user_id:
            user_id = AppConfig.get_user_id()
        
        if not device_id:
            device_id = AppConfig.generate_device_id()
        
        device_info = AppConfig.get_device_info()
        
        registration_data = {
            "deviceId": device_id,
            "userId": user_id,
            "deviceInfo": device_info,
            "permissions": {
                "readCallLog": True,
                "readPhoneState": True,
                "readContacts": True
            }
        }
        
        print("📱 Registering device...")
        print(f"Registration payload: {json.dumps(registration_data, indent=2)}")
        
        # Try multiple registration endpoints
        registration_endpoints = [
            "/devices/register",
            "/devices/simple-register"
        ]
        
        for endpoint in registration_endpoints:
            registration_url = urljoin(api_url.rstrip('/') + '/', endpoint.lstrip('/'))
            print(f"Attempting registration at: {registration_url}")
            
            try:
                response = self.session.post(
                    registration_url,
                    json=registration_data,
                    timeout=self.timeout
                )
                
                print(f"Registration response: {response.status_code} - {response.reason}")
                print(f"Response headers: {dict(response.headers)}")
                
                if response.status_code in [200, 201]:
                    try:
                        response_data = response.json()
                        print(f"Response JSON: {json.dumps(response_data, indent=2)}")
                        
                        if response_data.get("success"):
                            # Save registration info
                            StorageManager.save('user_id', user_id)
                            StorageManager.save('device_id', device_id)
                            StorageManager.save('api_url', api_url)
                            StorageManager.save('device_registered', 'True')
                            StorageManager.save('last_registration', str(int(time.time())))
                            
                            print("✅ Device registered successfully")
                            return True
                        else:
                            print(f"❌ Registration failed: {response_data.get('message', 'Unknown error')}")
                    
                    except ValueError as e:
                        print(f"❌ Invalid JSON response: {e}")
                
                else:
                    print(f"❌ Registration failed with status: {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"Error details: {json.dumps(error_data, indent=2)}")
                    except:
                        print(f"Error body: {response.text}")
            
            except requests.exceptions.Timeout:
                print(f"❌ Registration timeout at {registration_url}")
            except requests.exceptions.ConnectionError:
                print(f"❌ Connection failed to {registration_url}")
            except Exception as e:
                print(f"❌ Registration error: {str(e)}")
        
        print("❌ All registration attempts failed")
        return False
    
    def ping_device(self, api_url: str, device_id: str = None) -> bool:
        """
        Send ping to maintain device connection
        """
        if not device_id:
            device_id = StorageManager.load('device_id')
            if not device_id:
                print("❌ No device ID available for ping")
                return False
        
        ping_url = urljoin(api_url.rstrip('/') + '/', 'devices/ping')
        ping_data = {"deviceId": device_id}
        
        try:
            response = self.session.post(
                ping_url,
                json=ping_data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("success"):
                    print(f"💓 Ping successful for device: {device_id}")
                    return True
            
            print(f"❌ Ping failed: {response.status_code}")
            return False
        
        except Exception as e:
            print(f"❌ Ping error: {str(e)}")
            return False
    
    def get_saved_config(self) -> Optional[Dict[str, str]]:
        """
        Get saved configuration from storage
        """
        config = {}
        
        # Load saved values
        config['user_id'] = StorageManager.load('user_id')
        config['device_id'] = StorageManager.load('device_id')
        config['api_url'] = StorageManager.load('api_url')
        config['device_registered'] = StorageManager.load('device_registered')
        config['last_registration'] = StorageManager.load('last_registration')
        
        # Check if we have essential config
        if config['api_url'] and config['user_id']:
            return config
        
        return None
    
    def initialize_app(self) -> bool:
        """
        Complete app initialization with backend detection and device registration
        """
        print("🚀 Initializing Kortahun United App...")
        print(f"Platform: {get_platform_name()}")
        print(f"Android: {is_android()}")
        
        # Try to load saved configuration first
        saved_config = self.get_saved_config()
        if saved_config and saved_config['device_registered'] == 'True':
            print("📱 Using saved configuration...")
            
            # Test if saved API still works
            if self.test_backend_url(saved_config['api_url'])[0]:
                print("✅ Saved backend still available")
                
                # Try to ping to confirm device is still registered
                if self.ping_device(saved_config['api_url'], saved_config['device_id']):
                    print("✅ Device still connected")
                    return True
                else:
                    print("⚠️ Device ping failed, re-registering...")
            else:
                print("⚠️ Saved backend not available, detecting new backend...")
        
        # Detect backend
        api_url = self.detect_backend()
        if not api_url:
            print("❌ Backend detection failed")
            return False
        
        print("✅ Backend detected!")
        
        # Register device
        if self.register_device(api_url):
            print("✅ Device registered!")
            return True
        else:
            print("❌ Device registration failed")
            return False

# Convenience function for easy integration
def initialize_backend() -> bool:
    """
    Simple function to initialize backend connection
    """
    detector = BackendDetector(timeout=15, max_retries=3)
    return detector.initialize_app()

# Example usage
if __name__ == "__main__":
    print("🔧 Backend Detector Test")
    
    # Initialize
    success = initialize_backend()
    
    if success:
        print("🎉 App initialization successful!")
    else:
        print("💥 App initialization failed!")
    
    # Show final configuration
    detector = BackendDetector()
    config = detector.get_saved_config()
    if config:
        print("\n📋 Final Configuration:")
        for key, value in config.items():
            if value:
                print(f"  {key}: {value}")