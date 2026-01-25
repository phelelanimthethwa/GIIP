"""
Database Cleanup Script
This script will clean the entire Firebase database and keep only the admin account.

WARNING: This is a destructive operation. All data except the admin account will be deleted.
"""

import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db, auth
from config import Config
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        # Check if Firebase is already initialized
        try:
            firebase_admin.get_app()
            print("Firebase already initialized")
            return
        except ValueError:
            pass
        
        if os.environ.get('FIREBASE_CREDENTIALS'):
            # In production, use credentials from environment variable
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
            print("Using Firebase credentials from environment variable")
        else:
            # In development, use service account file
            if not os.path.exists('serviceAccountKey.json'):
                raise FileNotFoundError("serviceAccountKey.json not found. Please ensure Firebase credentials are available.")
            cred = credentials.Certificate('serviceAccountKey.json')
            print("Using Firebase credentials from serviceAccountKey.json")
        
        # Initialize Firebase with options
        firebase_options = {
            'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
            'storageBucket': 'giir-66ae6.firebasestorage.app',
        }
        
        firebase_admin.initialize_app(cred, firebase_options)
        print("Firebase initialized successfully")
    except Exception as e:
        print(f"Error initializing Firebase: {str(e)}")
        raise

def get_admin_user():
    """Get the admin user from Firebase Auth"""
    admin_email = Config.ADMIN_EMAIL
    print(f"Looking for admin user with email: {admin_email}")
    
    try:
        admin_user = auth.get_user_by_email(admin_email)
        print(f"Admin user found: {admin_user.uid} ({admin_user.email})")
        return admin_user
    except auth.UserNotFoundError:
        print(f"ERROR: Admin user not found in Firebase Auth!")
        print("Please ensure the admin account exists before running this script.")
        raise
    except Exception as e:
        print(f"Error getting admin user: {str(e)}")
        raise

def delete_all_users_except_admin(admin_uid):
    """Delete all users from Firebase Auth except the admin"""
    print("\n=== Deleting users from Firebase Auth ===")
    
    try:
        # List all users
        users = auth.list_users()
        total_users = 0
        deleted_count = 0
        
        for user in users.iterate_all():
            total_users += 1
            if user.uid != admin_uid:
                try:
                    auth.delete_user(user.uid)
                    deleted_count += 1
                    print(f"Deleted user: {user.email} ({user.uid})")
                except Exception as e:
                    print(f"Error deleting user {user.email}: {str(e)}")
            else:
                print(f"Preserved admin user: {user.email} ({user.uid})")
        
        print(f"\nTotal users: {total_users}")
        print(f"Deleted users: {deleted_count}")
        print(f"Preserved admin user: 1")
        
    except Exception as e:
        print(f"Error deleting users: {str(e)}")
        raise

def clean_realtime_database(admin_uid):
    """Clean all data from Realtime Database except admin user data"""
    print("\n=== Cleaning Realtime Database ===")
    
    # List of all database paths to delete
    paths_to_delete = [
        'registrations',
        'conferences',
        'papers',
        'user_paper_submissions',
        'speakers',
        'site_design',
        'home_content',
        'about_content',
        'call_for_papers_content',
        'paper_submission_settings',
        'author_guidelines',
        'venue_details',
        'registration_fees',
        'schedule',
        'announcements',
        'email_templates',
        'email_settings',
        'contact_submissions',
        'contact_email_settings',
        'contact_page_settings',
        'conference_proceedings',
        'downloads',
        'conference_proceedings_content',
        'guest_speaker_applications',
        'user_registrations',
        'submissions',
        'paper_submissions',
        'test_connection',
    ]
    
    # Delete all specified paths
    deleted_paths = []
    for path in paths_to_delete:
        try:
            ref = db.reference(path)
            data = ref.get()
            if data is not None:
                ref.delete()
                deleted_paths.append(path)
                print(f"Deleted: {path}")
        except Exception as e:
            print(f"Error deleting {path}: {str(e)}")
    
    print(f"\nDeleted {len(deleted_paths)} database paths")
    
    # Clean users collection - keep only admin user
    print("\n=== Cleaning users collection ===")
    try:
        users_ref = db.reference('users')
        all_users = users_ref.get() or {}
        
        deleted_users = 0
        for user_id, user_data in all_users.items():
            if user_id != admin_uid:
                try:
                    user_ref = db.reference(f'users/{user_id}')
                    user_ref.delete()
                    deleted_users += 1
                    email = user_data.get('email', 'unknown')
                    print(f"Deleted user data: {email} ({user_id})")
                except Exception as e:
                    print(f"Error deleting user {user_id}: {str(e)}")
            else:
                print(f"Preserved admin user data: {user_data.get('email', 'unknown')} ({user_id})")
        
        print(f"\nDeleted {deleted_users} user records from database")
        print("Preserved admin user data")
        
    except Exception as e:
        print(f"Error cleaning users collection: {str(e)}")
        raise

def verify_admin_user(admin_uid):
    """Verify that admin user still exists and has correct data"""
    print("\n=== Verifying admin user ===")
    
    try:
        # Check Firebase Auth
        admin_user = auth.get_user(admin_uid)
        print(f"[OK] Admin user exists in Firebase Auth: {admin_user.email}")
        
        # Check Realtime Database
        user_ref = db.reference(f'users/{admin_uid}')
        user_data = user_ref.get()
        
        if user_data:
            print(f"[OK] Admin user data exists in database:")
            print(f"  - Email: {user_data.get('email')}")
            print(f"  - Full Name: {user_data.get('full_name')}")
            print(f"  - Is Admin: {user_data.get('is_admin')}")
        else:
            print("[WARNING] Admin user data not found in database")
            print("Creating admin user data...")
            
            # Create admin user data
            admin_email = Config.ADMIN_EMAIL
            admin_data = {
                'email': admin_email,
                'full_name': 'Conference Admin',
                'created_at': datetime.now().isoformat(),
                'is_admin': True,
                'updated_at': datetime.now().isoformat()
            }
            user_ref.set(admin_data)
            print("[OK] Admin user data created")
        
    except Exception as e:
        print(f"Error verifying admin user: {str(e)}")
        raise

def main():
    """Main cleanup function"""
    import sys
    
    print("=" * 60)
    print("DATABASE CLEANUP SCRIPT")
    print("=" * 60)
    print("\nWARNING: This script will delete ALL data except the admin account!")
    print("This includes:")
    print("  - All users (except admin)")
    print("  - All registrations")
    print("  - All conferences")
    print("  - All papers/submissions")
    print("  - All other data")
    print("\nAdmin account that will be preserved:")
    print(f"  Email: {Config.ADMIN_EMAIL}")
    print("\n" + "=" * 60)
    
    # Check for --yes flag to skip confirmation
    skip_confirmation = '--yes' in sys.argv or '-y' in sys.argv
    
    if not skip_confirmation:
        # Confirmation prompt
        try:
            response = input("\nAre you sure you want to proceed? Type 'YES' to continue: ")
            if response != 'YES':
                print("Operation cancelled.")
                return
        except EOFError:
            print("\nError: Interactive input not available.")
            print("Run with --yes flag to skip confirmation: python clean_database.py --yes")
            return
    else:
        print("\n--yes flag detected. Proceeding with cleanup...")
    
    try:
        # Initialize Firebase
        initialize_firebase()
        
        # Get admin user
        admin_user = get_admin_user()
        admin_uid = admin_user.uid
        
        # Delete all users except admin from Firebase Auth
        delete_all_users_except_admin(admin_uid)
        
        # Clean Realtime Database
        clean_realtime_database(admin_uid)
        
        # Verify admin user
        verify_admin_user(admin_uid)
        
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE!")
        print("=" * 60)
        print(f"\nAdmin account preserved: {Config.ADMIN_EMAIL}")
        print("All other data has been deleted.")
        
    except Exception as e:
        print(f"\nERROR: Cleanup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == '__main__':
    main()
