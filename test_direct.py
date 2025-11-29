#!/usr/bin/env python3
"""
Test payment creation directly through app import (no HTTP required)
"""

import os
import sys
sys.path.append('.')

# Set up test environment
os.environ['SECRET_KEY'] = 'test_secret_key_for_testing_only'
os.environ['FIREBASE_API_KEY'] = 'test_firebase_key'

from services.ikhokha_service import IKhokhaPaymentService

def test_direct_service():
    """Test the iKhokha service directly"""
    print("Testing iKhokha service directly...")
    
    # Create service instance 
    service = IKhokhaPaymentService()
    print(f"Service configured: {service.is_configured}")
    print(f"App ID: {service.app_id}")
    
    # Test registration data
    test_data = {
        'user_id': 'direct_test_user',
        'full_name': 'Direct Test User',
        'email': 'directtest@example.com',
        'total_amount': 400.00,
        'conference_name': 'GIIP Direct Test',
        'registration_type': 'Premium'
    }
    
    try:
        result = service.create_payment_request(test_data)
        
        print(f"\nResult: {result}")
        
        if result.get('success'):
            print("✅ Payment creation successful!")
            print(f"Payment URL: {result['payment_url']}")
            print(f"Transaction Ref: {result['transaction_reference']}")
            
            # Test if this is a demo URL
            if 'payment/demo' in result['payment_url']:
                print("🎯 Demo mode active - this is expected for testing")
            else:
                print("🚀 Live mode active - real payment gateway")
                
        else:
            print("❌ Payment creation failed:")
            print(f"Error: {result.get('error')}")
            
        return result
        
    except Exception as e:
        print(f"❌ Exception in payment creation: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_json_parsing():
    """Test potential JSON parsing issues"""
    print("\n" + "="*50)
    print("Testing JSON parsing scenarios...")
    
    # Test the specific error scenario
    test_html_response = '<!DOCTYPE html><html><head><title>Error</title></head></html>'
    
    try:
        import json
        json.loads(test_html_response)
        print("❌ Should have failed to parse HTML as JSON")
    except ValueError as e:
        print("✅ HTML correctly rejected as invalid JSON")
        print(f"Error message: {e}")
    
    # Test valid JSON
    test_json_response = '{"success": true, "payment_url": "https://example.com"}'
    try:
        result = json.loads(test_json_response)
        print("✅ Valid JSON parsed successfully")
        print(f"Parsed: {result}")
    except ValueError as e:
        print(f"❌ Valid JSON failed to parse: {e}")

if __name__ == "__main__":
    test_json_parsing()
    result = test_direct_service()
    
    if result and result.get('success'):
        print("\n🎉 All tests passed! The JSON parsing error should be resolved.")
    else:
        print("\n⚠️  There may still be issues to address.")