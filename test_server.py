#!/usr/bin/env python3
"""
Simple test script to verify the WSGI server is working
"""

import requests
import sys
import json

def test_server():
    """Test if the server is responding"""
    try:
        print("🧪 Testing server at http://localhost:5000...")
        response = requests.get("http://localhost:5000", timeout=10)
        
        if response.status_code == 200:
            print("✅ Main page is responding successfully!")
            print(f"📊 Status Code: {response.status_code}")
            print(f"📏 Content Length: {len(response.content)} bytes")
            print(f"🏷️  Content Type: {response.headers.get('content-type', 'Unknown')}")
            
            # Test health endpoint
            print("\n🏥 Testing health endpoint...")
            health_response = requests.get("http://localhost:5000/health", timeout=5)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print("✅ Health check passed!")
                print(f"📊 Health Status: {health_data.get('status', 'Unknown')}")
                print(f"🗄️  Database: {health_data.get('database', 'Unknown')}")
                print(f"🕐 Timestamp: {health_data.get('timestamp', 'Unknown')}")
            else:
                print(f"⚠️  Health check returned status: {health_response.status_code}")
                
            return True
        else:
            print(f"⚠️  Server responded with status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running?")
        print("   Start the server with: python start_production.py")
        return False
    except requests.exceptions.Timeout:
        print("⏰ Server request timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        return False

if __name__ == "__main__":
    success = test_server()
    sys.exit(0 if success else 1)