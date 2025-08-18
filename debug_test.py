#!/usr/bin/env python3
"""
Debug test to identify specific issues
"""

import requests
import json
import time

def test_auth_flow():
    base_url = "https://edumanage-44.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Test 1: Health check
    print("Testing health check...")
    try:
        response = requests.get(base_url, timeout=10)
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test 2: Registration with unique user
    print("\nTesting registration...")
    timestamp = int(time.time())
    user_data = {
        "email": f"debugtest{timestamp}@edumanage.com",
        "phone": f"+9198765432{timestamp % 100:02d}",
        "full_name": "Debug Test User",
        "role": "student",
        "password": "DebugTest123!"
    }
    
    try:
        response = requests.post(f"{api_url}/auth/register", json=user_data, timeout=10)
        print(f"Registration: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            # Test 3: Login
            print("\nTesting login...")
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            login_response = requests.post(f"{api_url}/auth/login", json=login_data, timeout=10)
            print(f"Login: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                print(f"Token: {token[:50]}...")
                
                # Test 4: Get current user
                print("\nTesting get current user...")
                headers = {"Authorization": f"Bearer {token}"}
                me_response = requests.get(f"{api_url}/auth/me", headers=headers, timeout=10)
                print(f"Get me: {me_response.status_code}")
                print(f"Response: {me_response.text}")
                
                # Test 5: Get branches (to check 500 error)
                print("\nTesting get branches...")
                branches_response = requests.get(f"{api_url}/branches", headers=headers, timeout=10)
                print(f"Get branches: {branches_response.status_code}")
                print(f"Response: {branches_response.text}")
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_auth_flow()