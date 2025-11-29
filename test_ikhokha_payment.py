#!/usr/bin/env python3
"""
Test script for iKhokha payment integration

This script tests the payment creation functionality to ensure
the integration is working properly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.ikhokha_service import create_payment_session

def test_payment_creation():
    """Test creating a payment session with iKhokha"""
    
    # Sample registration data
    registration_data = {
        'user_id': 'test_user_123',
        'full_name': 'John Doe',
        'email': 'john.doe@example.com',
        'phone': '+27123456789',
        'total_amount': 150.00,
        'conference_name': 'GIIP Test Conference',
        'registration_type': 'regular_author',
        'registration_period': 'early',
        'additional_items': {
            'extra_paper': False,
            'workshop': True,
            'banquet': False
        }
    }
    
    print("🧪 Testing iKhokha Payment Integration")
    print("=" * 50)
    
    print(f"📝 Test Data:")
    print(f"   User: {registration_data['full_name']} ({registration_data['email']})")
    print(f"   Amount: R{registration_data['total_amount']:.2f}")
    print(f"   Conference: {registration_data['conference_name']}")
    
    print(f"\n🔄 Creating payment session...")
    
    try:
        result = create_payment_session(registration_data)
        
        print(f"\n📊 Result:")
        print(f"   Success: {result.get('success', False)}")
        
        if result.get('success'):
            print(f"   ✅ Payment URL: {result.get('payment_url', 'Not provided')}")
            print(f"   🆔 Transaction Ref: {result.get('transaction_reference', 'Not provided')}")
            print(f"   💳 Payment ID: {result.get('payment_id', 'Not provided')}")
            print(f"\n🎉 Payment integration test PASSED!")
            print(f"\n🔗 Next steps:")
            print(f"   1. User would be redirected to: {result.get('payment_url', 'N/A')}")
            print(f"   2. After payment, callback will be sent to: /payment/callback")
            print(f"   3. Registration will be completed automatically")
        else:
            error = result.get('error', 'Unknown error')
            print(f"   ❌ Error: {error}")
            
            if 'not configured' in error.lower():
                print(f"\n💡 Setup Required:")
                print(f"   1. Get iKhokha credentials from https://www.ikhokha.com/")
                print(f"   2. Update your .env file with:")
                print(f"      IKHOKHA_APP_ID=your_app_id")
                print(f"      IKHOKHA_SECRET_KEY=your_secret_key")
                print(f"   3. Restart the application")
            else:
                print(f"\n🔍 Payment integration test FAILED!")
                
    except Exception as e:
        print(f"   ❌ Exception: {str(e)}")
        print(f"\n🔍 Payment integration test FAILED!")
    
    print(f"\n" + "=" * 50)

if __name__ == '__main__':
    test_payment_creation()