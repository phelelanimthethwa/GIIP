"""
Script to add organizing committee members to the database
"""
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase Admin SDK
try:
    if os.environ.get('FIREBASE_CREDENTIALS'):
        # In production, use credentials from environment variable
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
        print("Using Firebase credentials from environment variable")
    else:
        # In development, use service account file
        cred = credentials.Certificate('serviceAccountKey.json')
        print("Using Firebase credentials from serviceAccountKey.json")
    
    # Initialize Firebase if not already initialized
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

# Define the new committee members
new_members = [
    {
        'role': 'Advisory',
        'name': 'Pablo Antonio Cano Jiménez',
        'affiliation': 'Adjunct Professor, Pedagogy Department, University of Huelva',
        'expertise': ['Foreign language education', 'Self-esteem in language learning', 'Educational methodology'],
        'email': 'pabloantonio.cano@ddi.uhu.es',
        'orcid': '0000-0002-8715-5966'
    },
    {
        'role': 'Advisory',
        'name': 'Dr. Kate Neequaye',
        'affiliation': 'Senior Lecturer, Tourism Department, Takoradi Technical University',
        'expertise': ['Tourism management', 'Hospitality', 'Food safety', 'Nutrition'],
        'email': 'kate.neequaye@ttu.edu.gh'
    },
    {
        'role': 'Advisory',
        'name': 'Dr. Kyungu Lubaba Lubadi',
        'affiliation': 'Research Fellow, Department of Economics, Stellenbosch University',
        'expertise': ['Moral education', 'Curriculum management', "Women's rights", 'Refugee education'],
        'email': 'urainter@gmail.com',
        'orcid': '0000-0002-4939-9767'
    },
    {
        'role': 'Advisory',
        'name': 'Dr. Doreen Anyamesem Odame',
        'affiliation': 'Lecturer, General Studies, Ghana Communication Technology University',
        'expertise': []
    },
    {
        'role': 'Advisory',
        'name': 'Dr. Sisanda Ngubane',
        'affiliation': 'Accredited Training Provider, Researcher, Consultant, Coceka Consulting',
        'expertise': ['Fundraising', 'Project management', 'Proposal development', 'SMME support'],
        'email': 'sisanda@cocekaconsulting.co.za',
        'phone': '+27 72 828 5310'
    },
    {
        'role': 'Advisory',
        'name': 'Dr. Nana Ama Boansi Boakye',
        'affiliation': 'Senior Lecturer, Hospitality Management, Takoradi Technical University',
        'expertise': ['Nutrition', 'Food technology', 'Food safety', 'Hospitality management'],
        'email': 'nana.ama.boakye@ttu.edu.gh',
        'phone': '+233 244 419 446'
    },
    {
        'role': 'Advisory',
        'name': 'Prof. Badar Alam Iqbal',
        'affiliation': 'Emeritus/Extraordinary Professor, Research Fellow, Stellenbosch University',
        'expertise': ['International economics', 'FDI', 'BRICS economies', 'International trade'],
        'email': 'dr.badar@umonarch-email.ch'
    }
]

def add_committee_members():
    """Add new committee members to the organizing committee"""
    try:
        # Get current about_content
        about_ref = db.reference('about_content')
        try:
            about_content = about_ref.get() or {}
        except Exception as e:
            # If about_content doesn't exist yet, create empty structure
            if '404' in str(e) or 'NotFound' in str(e):
                print("about_content doesn't exist yet, creating new structure...")
                about_content = {}
            else:
                raise
        
        # Initialize committee list if it doesn't exist
        if 'committee' not in about_content:
            about_content['committee'] = []
        
        # Get existing member names to avoid duplicates
        existing_names = {member.get('name', '').lower() for member in about_content['committee']}
        
        # Add new members (only if they don't already exist)
        added_count = 0
        skipped_count = 0
        
        for member in new_members:
            member_name_lower = member['name'].lower()
            if member_name_lower not in existing_names:
                # Convert expertise to list format if it's not already
                if isinstance(member.get('expertise'), list):
                    expertise_list = member['expertise']
                else:
                    expertise_list = [member['expertise']] if member.get('expertise') else []
                
                # Create member dict with required fields only
                member_dict = {
                    'role': member['role'],
                    'name': member['name'],
                    'affiliation': member['affiliation'],
                    'expertise': expertise_list
                }
                
                # Add optional fields if they exist
                if member.get('email'):
                    member_dict['email'] = member['email']
                if member.get('phone'):
                    member_dict['phone'] = member['phone']
                if member.get('orcid'):
                    member_dict['orcid'] = member['orcid']
                
                about_content['committee'].append(member_dict)
                existing_names.add(member_name_lower)
                added_count += 1
                print(f"[OK] Added: {member['name']}")
            else:
                skipped_count += 1
                print(f"[SKIP] Skipped (already exists): {member['name']}")
        
        # Save updated about_content back to Firebase
        about_ref.set(about_content)
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  Added: {added_count} new members")
        print(f"  Skipped: {skipped_count} existing members")
        print(f"  Total committee members: {len(about_content['committee'])}")
        print(f"{'='*60}")
        print("\n[SUCCESS] Organizing committee updated successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Error updating organizing committee: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == '__main__':
    print("Adding organizing committee members...")
    print("="*60)
    add_committee_members()
