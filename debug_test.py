#!/usr/bin/env python3
"""
Debug test to identify specific issues
"""

import requests
import json
import time

def test_auth_flow():
    base_url = "https://edumanage-44.preview.dev.com"
    api_url = f"{base_url}/api"
    
    # Test 1: Health check
    print("Testing health check...")
    try:
        response = requests.get(base_url, timeout=30)
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test 2: Registration with unique user
    print("\nTesting registration...")
    timestamp = int(time.time())
    user_data = {
        "email": f"debugtest{timestamp}@edumanage.com",
        "phone": f"+91{timestamp}",
        "full_name": "Debug Test User",
        "role": "student",
        "password": "DebugTest123!"
    }
    
    try:
        response = requests.post(f"{api_url}/auth/register", json=user_data, timeout=30)
        print(f"Registration: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            # Test 3: Login
            print("\nTesting login...")
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            
            login_response = requests.post(f"{api_url}/auth/login", json=login_data, timeout=30)
            print(f"Login: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                print(f"Token: {token[:50]}...")
                
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # Test 4: Get courses
                print("\nTesting get courses...")
                courses_response = requests.get(f"{api_url}/courses", headers=headers, timeout=30)
                print(f"Get courses: {courses_response.status_code}")
                print(f"Response: {courses_response.text}")

                # Test 5: Get products
                print("\nTesting get products...")
                products_response = requests.get(f"{api_url}/products", headers=headers, timeout=30)
                print(f"Get products: {products_response.status_code}")
                print(f"Response: {products_response.text}")

                # Test 6: Create complaint
                print("\nTesting create complaint...")
                complaint_data = {
                    "subject": "Facility Issue",
                    "description": "The training hall needs better ventilation and lighting for evening sessions.",
                    "category": "facilities",
                    "priority": "medium"
                }
                complaint_response = requests.post(f"{api_url}/complaints", headers=headers, json=complaint_data, timeout=30)
                print(f"Create complaint: {complaint_response.status_code}")
                print(f"Response: {complaint_response.text}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_auth_flow()
