#!/usr/bin/env python3
"""
Test the Flask app payment creation endpoint directly
"""

import requests
import json

def test_payment_endpoint():
    """Test the /payment/create endpoint"""
    
    url = "http://localhost:5000/payment/create"
    
    # Test payment data
    payment_data = {
        'user_id': 'test_endpoint_user',
        'full_name': 'Endpoint Test User',
        'email': 'endpointtest@example.com', 
        'registration_type': 'Standard',
        'total_amount': 300.00,
        'conference_name': 'GIIP Endpoint Test'
    }
    
    print(f"Testing payment endpoint: {url}")
    print(f"Payment data: {json.dumps(payment_data, indent=2)}")
    
    try:
        response = requests.post(url, json=payment_data, timeout=10)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        # Try to parse response as JSON
        try:
            response_data = response.json()
            print(f"Response JSON: {json.dumps(response_data, indent=2)}")
            
            if response_data.get('success'):
                print("✅ Payment endpoint working correctly!")
                print(f"Payment URL: {response_data.get('payment_url')}")
            else:
                print("❌ Payment endpoint returned error:")
                print(f"Error: {response_data.get('error')}")
                
        except ValueError as e:
            print(f"❌ Response is not valid JSON: {e}")
            print(f"Response text: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_payment_endpoint()