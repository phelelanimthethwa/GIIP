"""
Script to add registration fees to the database
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

try:
    if os.environ.get('FIREBASE_CREDENTIALS'):
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.Certificate('serviceAccountKey.json')
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://giir-66ae6-default-rtdb.firebaseio.com')
        })
        print("Firebase initialized successfully")
    else:
        print("Firebase already initialized")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    exit(1)

def add_registration_fees():
    """Add registration fees to the database"""
    try:
        # Define the registration fees structure
        registration_fees = {
            'currency': {
                'code': 'USD',
                'symbol': '$'
            },
            'early_bird': {
                'enabled': True,
                'deadline': '2026-03-27',  # March 27, 2026
                'seats': {
                    'total': 100,
                    'remaining': 100,
                    'show_remaining': True
                },
                'fees': {
                    'student_author': 376,      # Authors (Students) - Early Bird
                    'regular_author': 504,      # Authors (Regular) - Early Bird
                    'physical_delegate': 0,
                    'virtual_delegate': 0,
                    'listener': 187             # Listener/Attendee - Early Bird
                },
                'benefits': []
            },
            'early': {
                'deadline': '',
                'fees': {
                    'student_author': 0,
                    'regular_author': 0,
                    'physical_delegate': 0,
                    'virtual_delegate': 0,
                    'listener': 0
                },
                'benefits': []
            },
            'regular': {
                'deadline': '',
                'fees': {
                    'student_author': 442,      # Authors (Students) - Regular Price
                    'regular_author': 593,       # Authors (Regular) - Regular Price
                    'physical_delegate': 0,
                    'virtual_delegate': 0,
                    'listener': 220              # Listener/Attendee - Regular Price
                },
                'benefits': []
            },
            'late': {
                'deadline': '',
                'fees': {
                    'student_author': 0,
                    'regular_author': 0,
                    'physical_delegate': 0,
                    'virtual_delegate': 0,
                    'listener': 0
                },
                'benefits': []
            },
            'additional_items': {
                'extra_paper': {
                    'enabled': True,
                    'fee': 50,                  # Each Additional Paper - USD 50
                    'description': 'Each Additional Paper (Not applicable for early bird)'
                },
                'workshop': {
                    'enabled': False,
                    'fee': 0,
                    'description': ''
                },
                'banquet': {
                    'enabled': False,
                    'fee': 0,
                    'description': '',
                    'virtual_eligible': False
                }
            }
        }
        
        # Save to Firebase
        db.reference('registration_fees').set(registration_fees)
        
        print("="*60)
        print("REGISTRATION FEES ADDED SUCCESSFULLY")
        print("="*60)
        print("\nEarly Bird Pricing (Deadline: March 27, 2026):")
        print(f"  Authors (Students): ${registration_fees['early_bird']['fees']['student_author']}")
        print(f"  Authors (Regular): ${registration_fees['early_bird']['fees']['regular_author']}")
        print(f"  Listener/Attendee: ${registration_fees['early_bird']['fees']['listener']}")
        print("\nRegular Pricing:")
        print(f"  Authors (Students): ${registration_fees['regular']['fees']['student_author']}")
        print(f"  Authors (Regular): ${registration_fees['regular']['fees']['regular_author']}")
        print(f"  Listener/Attendee: ${registration_fees['regular']['fees']['listener']}")
        print("\nAdditional Items:")
        print(f"  Each Additional Paper: ${registration_fees['additional_items']['extra_paper']['fee']}")
        print("="*60)
        print("\n[SUCCESS] Registration fees have been saved to the database!")
        print("You can now view them at: http://127.0.0.1:5000/admin/registration-fees")
        
    except Exception as e:
        print(f"\n[ERROR] Error adding registration fees: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    print("Adding registration fees to database...")
    print("="*60)
    add_registration_fees()
