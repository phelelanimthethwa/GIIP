#!/usr/bin/env python3
"""
Debug iKhokha v2 API request format
"""

import sys
sys.path.append('.')

from services.ikhokha_service import IKhokhaPaymentService
import json
import requests
import hashlib
import hmac

def debug_api_call():
    """Debug the exact API call being made"""
    
    service = IKhokhaPaymentService()
    
    # Test data
    test_data = {
        'user_id': 'debug_user',
        'total_amount': 100.00,
        'conference_name': 'Debug Test'
    }
    
    # Create the request data manually to see what we're sending
    payment_reference = f"REG_debug_user_123456"
    
    request_data = {
        "amount": test_data['total_amount'],
        "currency": "ZAR", 
        "description": f"Conference Registration - {test_data.get('conference_name', 'GIIP Conference')}",
        "reference": payment_reference,
        "merchantReference": payment_reference,
        "successUrl": "https://globalconference.co.za/payment/callback",
        "failureUrl": "https://globalconference.co.za/payment/cancelled",
        "cancelUrl": "https://globalconference.co.za/payment/cancelled",
        "webhookUrl": "https://globalconference.co.za/payment/webhook"
    }
    
    # Convert to JSON
    request_body_str = json.dumps(request_data, separators=(',', ':'))
    
    # Create signature
    key_bytes = service.secret_key.encode('utf-8')
    payload_bytes = request_body_str.encode('utf-8')
    hmac_obj = hmac.new(key_bytes, payload_bytes, hashlib.sha256)
    signature = hmac_obj.hexdigest()
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {service.app_id}",
        "X-Signature": signature
    }
    
    print("=== DEBUG INFO ===")
    print(f"Endpoint: {service.api_endpoint}")
    print(f"Request Body: {request_body_str}")
    print(f"Signature: {signature}")
    print(f"Headers: {headers}")
    
    print("\n=== MAKING REQUEST ===")
    
    try:
        response = requests.post(
            service.api_endpoint,
            headers=headers,
            data=request_body_str,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            try:
                json_response = response.json()
                print(f"JSON Response: {json.dumps(json_response, indent=2)}")
            except:
                print("Response is not valid JSON")
                
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    debug_api_call()