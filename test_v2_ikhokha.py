#!/usr/bin/env python3
"""
Test updated iKhokha v2 service
"""

import sys
sys.path.append('.')

from services.ikhokha_service import IKhokhaPaymentService

def test_v2_service():
    """Test the updated v2 service"""
    
    # Test with the current config (should use live credentials)
    service = IKhokhaPaymentService()
    
    print(f"Service configured: {service.is_configured}")
    print(f"API endpoint: {service.api_endpoint}")
    print(f"App ID: {service.app_id[:10]}..." if service.app_id else "No App ID")
    
    # Test registration data
    test_registration = {
        'user_id': 'v2_test_user',
        'full_name': 'V2 Test User',
        'email': 'v2test@example.com',
        'total_amount': 150.00,
        'conference_name': 'GIIP V2 Test',
        'registration_type': 'Standard'
    }
    
    print(f"\nTesting payment creation for R{test_registration['total_amount']}")
    
    try:
        result = service.create_payment_request(test_registration)
        
        if result['success']:
            print("✅ V2 Payment creation successful!")
            print(f"Payment URL: {result.get('payment_url', 'No URL')}")
            print(f"Transaction Reference: {result.get('transaction_reference', 'No reference')}")
        else:
            print("❌ V2 Payment creation failed:")
            print(f"Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Exception in V2 test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_v2_service()