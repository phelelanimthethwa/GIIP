#!/usr/bin/env python3
"""
Quick test script to verify iKhokha integration fixes
"""

import os
import sys
sys.path.append('.')

from services.ikhokha_service import IKhokhaPaymentService

def test_payment_creation():
    """Test payment creation with demo credentials"""
    print("Testing iKhokha payment service...")
    
    # Test with demo credentials
    service = IKhokhaPaymentService(app_id="demo", secret_key="demo_secret")
    
    # Sample registration data
    test_registration = {
        'user_id': 'test_user_123',
        'full_name': 'Test User',
        'email': 'test@example.com',
        'total_amount': 500.00,
        'conference_name': 'GIIP Test Conference',
        'registration_type': 'Standard'
    }
    
    print(f"Creating payment request for R{test_registration['total_amount']}")
    
    try:
        result = service.create_payment_request(test_registration)
        
        if result['success']:
            print("✅ Payment creation successful!")
            print(f"Payment URL: {result['payment_url']}")
            print(f"Transaction Reference: {result['transaction_reference']}")
        else:
            print("❌ Payment creation failed:")
            print(f"Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()

def test_live_service():
    """Test with live service configuration (should use demo mode if no real credentials)"""
    print("\nTesting with config credentials...")
    
    try:
        from config import Config
        service = IKhokhaPaymentService()
        
        print(f"Service configured: {service.is_configured}")
        print(f"App ID: {service.app_id}")
        print(f"Has Secret: {'Yes' if service.secret_key else 'No'}")
        
        test_registration = {
            'user_id': 'config_test_123',
            'full_name': 'Config Test User', 
            'email': 'configtest@example.com',
            'total_amount': 250.00,
            'conference_name': 'GIIP Live Test',
            'registration_type': 'Early Bird'
        }
        
        result = service.create_payment_request(test_registration)
        
        if result['success']:
            print("✅ Config-based payment creation successful!")
            print(f"Payment URL: {result['payment_url']}")
        else:
            print("❌ Config-based payment creation failed:")
            print(f"Error: {result['error']}")
            
    except Exception as e:
        print(f"❌ Config test exception: {str(e)}")

if __name__ == "__main__":
    test_payment_creation()
    test_live_service()
    print("\nTest completed!")