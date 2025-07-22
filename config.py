# config.py - Production-ready configuration for cross-platform deployment

import os
import platform
import json
from typing import Dict, List, Optional

class AppConfig:
    """
    Production-ready configuration that works across all environments
    """
    
    # Production API URLs (primary)
    PRODUCTION_APIS = [
        "https://kortahununited.onrender.com/api",
        "https://kortahununited.onrender.com/api/devices",  # Direct device endpoint
    ]
    
    # Fallback/Development URLs (only for local development)
    DEVELOPMENT_APIS = [
        "http://localhost:5001/api",
        "http://127.0.0.1:5001/api",
        "http://192.168.1.100:5001/api",  # Update this to your local IP
    ]
    
    # Network test URLs
    CONNECTIVITY_TEST_URLS = [
        "https://httpbin.org/get",
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://www.google.com",
        "https://kortahununited.onrender.com"  # Test your own server
    ]
    
    @classmethod
    def get_api_urls(cls) -> List[str]:
        """
        Get API URLs based on environment
        Priority: Production URLs first, then development (if available)
        """
        # Always try production first
        api_urls = cls.PRODUCTION_APIS.copy()
        
        # Only add development URLs if we're in a development environment
        if cls.is_development_environment():
            api_urls.extend(cls.DEVELOPMENT_APIS)
        
        return api_urls
    
    @classmethod
    def is_development_environment(cls) -> bool:
        """
        Check if we're in a development environment
        """
        # Check for common development indicators
        is_dev = (
            os.getenv('NODE_ENV', '').lower() in ['development', 'dev'] or
            os.getenv('ENVIRONMENT', '').lower() in ['development', 'dev'] or
            platform.system() == 'Windows' and 'decke' in os.path.expanduser('~') or  # Your dev machine
            os.path.exists('.env') or  # Development environment file
            os.path.exists('venv') or  # Python virtual environment
            'localhost' in os.getenv('API_URL', '') or
            '127.0.0.1' in os.getenv('API_URL', '')
        )
        
        return is_dev
    
    @classmethod
    def get_device_info(cls) -> Dict:
        """
        Get comprehensive device information for registration
        """
        system = platform.system()
        
        # Android detection
        try:
            from jnius import autoclass
            # If jnius works, we're on Android
            Build = autoclass('android.os.Build')
            return {
                "model": Build.MODEL,
                "manufacturer": Build.MANUFACTURER,
                "os": "Android",
                "osVersion": Build.VERSION.RELEASE,
                "appVersion": "2.0.0",
                "platform": "android",
                "api_level": Build.VERSION.SDK_INT
            }
        except ImportError:
            pass
        
        # Desktop/Development environment
        if system == "Windows":
            return {
                "model": "Windows PC",
                "manufacturer": "Microsoft",
                "os": "Windows",
                "osVersion": platform.version(),
                "appVersion": "2.0.0",
                "platform": "windows"
            }
        elif system == "Darwin":  # macOS
            return {
                "model": "Mac",
                "manufacturer": "Apple",
                "os": "macOS",
                "osVersion": platform.mac_ver()[0],
                "appVersion": "2.0.0",
                "platform": "macos"
            }
        elif system == "Linux":
            return {
                "model": "Linux Device",
                "manufacturer": "Linux",
                "os": "Linux",
                "osVersion": platform.release(),
                "appVersion": "2.0.0",
                "platform": "linux"
            }
        else:
            return {
                "model": "Unknown",
                "manufacturer": "Unknown",
                "os": system,
                "osVersion": platform.release(),
                "appVersion": "2.0.0",
                "platform": "unknown"
            }
    
    @classmethod
    def get_user_id(cls) -> str:
        """
        Get user ID with fallback strategies
        """
        # Try environment variable first
        user_id = os.getenv('USER_ID')
        if user_id:
            return user_id
        
        # Try saved user ID from storage
        try:
            from storage_manager import StorageManager
            stored_user_id = StorageManager.load('user_id')
            if stored_user_id:
                return stored_user_id
        except:
            pass
        
        # Generate a consistent user ID based on device
        import hashlib
        device_info = cls.get_device_info()
        unique_string = f"{device_info['platform']}_{device_info['model']}_{device_info['manufacturer']}"
        user_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
        
        # Save for future use
        try:
            from storage_manager import StorageManager
            StorageManager.save('user_id', user_id)
        except:
            pass
        
        return user_id
    
    @classmethod
    def generate_device_id(cls) -> str:
        """
        Generate a unique device ID
        """
        import hashlib
        import time
        
        device_info = cls.get_device_info()
        unique_components = [
            device_info['platform'],
            device_info['model'],
            device_info['manufacturer'],
            str(int(time.time() / 86400))  # Changes daily for uniqueness
        ]
        
        unique_string = '_'.join(unique_components)
        device_hash = hashlib.md5(unique_string.encode()).hexdigest()[:16]
        
        return f"{device_info['platform']}_{device_hash}"

# Storage manager for cross-platform data persistence
class StorageManager:
    """
    Cross-platform storage manager
    """
    
    @staticmethod
    def get_storage_path() -> str:
        """Get platform-appropriate storage path"""
        try:
            # Try Android storage first
            from jnius import autoclass
            Environment = autoclass('android.os.Environment')
            context = autoclass('org.kivy.android.PythonActivity').mActivity
            storage_path = str(context.getFilesDir().getAbsolutePath())
            return storage_path
        except ImportError:
            pass
        
        # Desktop storage
        import os
        home_dir = os.path.expanduser('~')
        storage_dir = os.path.join(home_dir, '.kortahun_united')
        os.makedirs(storage_dir, exist_ok=True)
        return storage_dir
    
    @staticmethod
    def save(key: str, value: str) -> bool:
        """Save data to persistent storage"""
        try:
            storage_path = StorageManager.get_storage_path()
            file_path = os.path.join(storage_path, f"{key}.txt")
            
            with open(file_path, 'w') as f:
                f.write(str(value))
            
            return True
        except Exception as e:
            print(f"Failed to save {key}: {e}")
            return False
    
    @staticmethod
    def load(key: str) -> Optional[str]:
        """Load data from persistent storage"""
        try:
            storage_path = StorageManager.get_storage_path()
            file_path = os.path.join(storage_path, f"{key}.txt")
            
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read().strip()
            
            return None
        except Exception as e:
            print(f"Failed to load {key}: {e}")
            return None
    
    @staticmethod
    def save_json(key: str, data: dict) -> bool:
        """Save JSON data to persistent storage"""
        try:
            json_str = json.dumps(data)
            return StorageManager.save(key, json_str)
        except Exception as e:
            print(f"Failed to save JSON {key}: {e}")
            return False
    
    @staticmethod
    def load_json(key: str) -> Optional[dict]:
        """Load JSON data from persistent storage"""
        try:
            json_str = StorageManager.load(key)
            if json_str:
                return json.loads(json_str)
            return None
        except Exception as e:
            print(f"Failed to load JSON {key}: {e}")
            return None

# Environment detection utilities
def is_android() -> bool:
    """Check if running on Android"""
    try:
        from jnius import autoclass
        return True
    except ImportError:
        return False

def is_desktop() -> bool:
    """Check if running on desktop"""
    return not is_android()

def get_platform_name() -> str:
    """Get human-readable platform name"""
    if is_android():
        return "Android"
    else:
        return platform.system()

# Example usage and testing
if __name__ == "__main__":
    print("🔧 Configuration Test")
    print(f"Platform: {get_platform_name()}")
    print(f"Development Environment: {AppConfig.is_development_environment()}")
    print(f"API URLs: {AppConfig.get_api_urls()}")
    print(f"Device Info: {json.dumps(AppConfig.get_device_info(), indent=2)}")
    print(f"User ID: {AppConfig.get_user_id()}")
    print(f"Device ID: {AppConfig.generate_device_id()}")
    
    # Test storage
    test_key = "test_config"
    test_value = "configuration_works"
    
    if StorageManager.save(test_key, test_value):
        loaded_value = StorageManager.load(test_key)
        print(f"Storage Test: {loaded_value == test_value}")
    else:
        print("Storage Test: Failed")