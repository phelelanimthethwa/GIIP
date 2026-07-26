"""
One-time/repeatable idempotent migration script for Conference Registration Fees.
Copies root-level 'registration_fees' into 'conferences/{conference_id}/registration_fees'
for all active and upcoming conferences that do not have a registration_fees node yet.
Also initializes 'global_settings/payment_details'.
"""

import os
import sys
import firebase_admin
from firebase_admin import credentials, db

# Ensure project directory is in path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import Config

def init_firebase():
    """Initialize Firebase Admin SDK if not initialized."""
    if not firebase_admin._apps:
        if os.environ.get('FIREBASE_CREDENTIALS'):
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
        elif os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            cred_path = os.environ['GOOGLE_APPLICATION_CREDENTIALS']
            cred = credentials.Certificate(cred_path)
        elif os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH'):
            cred_path = os.environ['FIREBASE_SERVICE_ACCOUNT_PATH']
            cred = credentials.Certificate(cred_path)
        elif os.path.exists('serviceAccountKey.json'):
            cred = credentials.Certificate('serviceAccountKey.json')
        else:
            raise RuntimeError("No Firebase credentials found.")

        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
            'storageBucket': 'giir-66ae6.firebasestorage.app'
        })

def migrate_registration_fees():
    init_firebase()
    print("=" * 60)
    print("Starting Registration Fees Migration...")
    print("=" * 60)

    # 1. Fetch root-level registration_fees
    root_fees_ref = db.reference('registration_fees')
    root_fees = root_fees_ref.get() or {}

    if not root_fees:
        print("[WARNING] No root-level 'registration_fees' node found in Firebase database.")
    else:
        print("[INFO] Found root-level 'registration_fees' node.")

    # 2. Extract payment details to populate global_settings/payment_details if present
    payment_details_ref = db.reference('global_settings/payment_details')
    existing_global_payment = payment_details_ref.get()
    
    if not existing_global_payment and isinstance(root_fees, dict) and 'payment_details' in root_fees:
        print("[INFO] Populating 'global_settings/payment_details' from root fees payment details...")
        payment_details_ref.set(root_fees['payment_details'])
        print("[SUCCESS] 'global_settings/payment_details' updated.")
    elif existing_global_payment:
        print("[INFO] 'global_settings/payment_details' already exists. Skipping global bank details copy.")

    # 3. Get all conferences
    conferences_ref = db.reference('conferences')
    conferences = conferences_ref.get() or {}

    if not conferences:
        print("[WARNING] No conferences found under 'conferences' node.")
        return

    migrated_count = 0
    skipped_count = 0

    for conf_id, conf_data in conferences.items():
        if not isinstance(conf_data, dict):
            continue

        basic_info = conf_data.get('basic_info', {})
        conf_name = basic_info.get('name', conf_id)
        conf_status = basic_info.get('status', 'draft')

        # Check if this conference already has a registration_fees node
        conf_fees_ref = db.reference(f'conferences/{conf_id}/registration_fees')
        existing_conf_fees = conf_fees_ref.get()

        if existing_conf_fees is not None:
            print(f"[SKIP] Conference '{conf_name}' ({conf_id}) already has a 'registration_fees' node. Idempotent skip.")
            skipped_count += 1
            continue

        # Copy root_fees to conference node if available
        if root_fees:
            print(f"[MIGRATE] Copying root registration fees to conference '{conf_name}' ({conf_id})...")
            conf_fees_ref.set(root_fees)
            migrated_count += 1
            print(f"  [OK] Successfully initialized 'conferences/{conf_id}/registration_fees'")
        else:
            print(f"[WARNING] Conference '{conf_name}' ({conf_id}) has no fees node, but root fees were empty.")

    print("=" * 60)
    print(f"Migration Complete: {migrated_count} migrated, {skipped_count} skipped.")
    print("=" * 60)

if __name__ == '__main__':
    migrate_registration_fees()
