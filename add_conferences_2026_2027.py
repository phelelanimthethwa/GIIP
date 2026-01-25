"""
Script to add two conferences for 2026 and 2027 to Firebase
- ICETL-2026: International Conference on Social Science, Education and Learning
- ICIRT-2027: International Conference on Innovation, Robotics and Applied Technology
"""

import os
import sys
import json
from datetime import datetime

# Add the current directory to the path so we can import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed, skipping .env loading")

import firebase_admin
from firebase_admin import credentials, db
from utils import generate_conference_code

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
    
    # Initialize Firebase with options
    firebase_options = {
        'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
        'storageBucket': 'giir-66ae6.firebasestorage.app',
    }
    
    # Initialize the Firebase app (only if not already initialized)
    try:
        firebase_admin.get_app()
        print("Firebase app already initialized")
    except ValueError:
        firebase_admin.initialize_app(cred, firebase_options)
        print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise

def create_conference_with_code(conference_data):
    """
    Create a new conference with an auto-generated unique code
    """
    try:
        # Generate conference code from abbreviation and year
        abbr = conference_data.get('basic_info', {}).get('abbreviation', 'CONF')
        year = conference_data.get('basic_info', {}).get('year', datetime.now().year)
        conference_code = generate_conference_code(abbr, year)

        # Add conference code to the data
        conference_data['conference_code'] = conference_code
        conference_data['code_generated_at'] = datetime.now().isoformat()

        # Save to Firebase
        conferences_ref = db.reference('conferences')
        new_conference_ref = conferences_ref.push(conference_data)

        return {
            'conference_id': new_conference_ref.key,
            'conference_code': conference_code,
            'success': True
        }
    except Exception as e:
        print(f"Error creating conference with code: {e}")
        return {
            'success': False,
            'error': str(e)
        }

# Conference 1: ICETL-2026
conference_2026 = {
    'basic_info': {
        'name': 'International Conference on Social Science, Education and Learning (ICETL-2026)',
        'description': '''Join the premier Social Science and education conference 2026. Taking place virtually on the 21st – 24th July 2026, the international social sciences and education conference 2026 will host the international community from social and behavioural scientists, educators, representatives of non-profit and government organizations, and other stakeholders to discuss such topics as adult education, pedagogy, ICT, inclusive education, and more.

We invite the international community to take an active role in shaping the future of education. Share your research findings, exchange ideas with fellow academic members, expand your network, and get inspired. The conference will be held every year to make it an ideal platform for people to share views and experiences in education and the related areas.

Toronto, the capital of the province of Ontario, is a major Canadian city along Lake Ontario's northwestern shore. It's a dynamic metropolis with a core of soaring skyscrapers, all dwarfed by the iconic, free-standing CN Tower. Toronto also has many green spaces, from the orderly oval of Queen's Park to 400-acre High Park and its trails, sports facilities and zoo. This is the excellent location for providing academic platforms to share related innovations & practices in pedagogy and explore educational technologies and, at the same time, network for future collaborations in education.''',
        'year': 2026,
        'abbreviation': 'ICETL',
        'status': 'upcoming',
        'event_type': 'virtual',
        'start_date': '2026-07-21',
        'end_date': '2026-07-24',
        'location': 'Toronto, Ontario, Canada',
        'website': '',
        'timezone': 'UTC'
    },
    'settings': {
        'registration_enabled': True,  # Enable registration
        'paper_submission_enabled': True,
        'gallery_enabled': True,
        'email_notifications': True,
        'max_registrations': 1000,
        'max_paper_submissions': 500
    },
    'metadata': {
        'created_at': datetime.now().isoformat(),
        'created_by': 'system',
        'version': '1.0.0'
    }
}

# Conference 2: ICIRT-2027
conference_2027 = {
    'basic_info': {
        'name': 'International Conference on Innovation, Robotics and Applied Technology (ICIRT-2027)',
        'description': '''International Conference on Innovation, Robotics and Applied Technology (ICIRT - 2027) will be held virtually during the 26th - 29th Jan 2027. ICIRT is to bring together innovative academics and industrial experts in the field of Science Technology and Management to a common forum. This Conference is Organized by the Global Institute on Innovative Research (GIIR).

The primary goal of the conference is to promote research and developmental activities in Control, Automation, Robotics and Vision Engineering. In addition, it aims to promote scientific information interchange between researchers, developers, engineers, students, and practitioners working in and around the world. The conference will be held every year to make it an ideal platform for people to share views and experiences in Control, Automation, Robotics and Vision Engineering related areas.

Rio de Janeiro is a huge seaside city in Brazil, famed for its Copacabana and Ipanema beaches, 38m Christ the Redeemer statue atop Mount Corcovado and for Sugarloaf Mountain, a granite peak with cable cars to its summit. The city is also known for its sprawling favelas (shanty towns). Its raucous Carnaval festival, featuring parade floats, flamboyant costumes and samba dancers, is considered the world's largest. This is the excellent location for providing academic platforms thus offering an ideal opportunity for networking for future collaboration at an international level.''',
        'year': 2027,
        'abbreviation': 'ICIRT',
        'status': 'upcoming',
        'event_type': 'virtual',
        'start_date': '2027-01-26',
        'end_date': '2027-01-29',
        'location': 'Rio de Janeiro, Brazil',
        'website': '',
        'timezone': 'UTC'
    },
    'settings': {
        'registration_enabled': True,  # Enable registration
        'paper_submission_enabled': True,
        'gallery_enabled': True,
        'email_notifications': True,
        'max_registrations': 1000,
        'max_paper_submissions': 500
    },
    'metadata': {
        'created_at': datetime.now().isoformat(),
        'created_by': 'system',
        'version': '1.0.0'
    }
}

if __name__ == '__main__':
    print("Adding conferences to Firebase...")
    print("\n" + "="*60)
    
    # Add 2026 conference
    print("\n1. Adding ICETL-2026...")
    result_2026 = create_conference_with_code(conference_2026)
    if result_2026['success']:
        print(f"   ✓ Successfully created conference!")
        print(f"   Conference ID: {result_2026['conference_id']}")
        print(f"   Conference Code: {result_2026['conference_code']}")
        print(f"   Name: {conference_2026['basic_info']['name']}")
        print(f"   Dates: {conference_2026['basic_info']['start_date']} to {conference_2026['basic_info']['end_date']}")
        print(f"   Registration Enabled: {conference_2026['settings']['registration_enabled']}")
    else:
        print(f"   ✗ Error: {result_2026.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)
    
    # Add 2027 conference
    print("\n2. Adding ICIRT-2027...")
    result_2027 = create_conference_with_code(conference_2027)
    if result_2027['success']:
        print(f"   ✓ Successfully created conference!")
        print(f"   Conference ID: {result_2027['conference_id']}")
        print(f"   Conference Code: {result_2027['conference_code']}")
        print(f"   Name: {conference_2027['basic_info']['name']}")
        print(f"   Dates: {conference_2027['basic_info']['start_date']} to {conference_2027['basic_info']['end_date']}")
        print(f"   Registration Enabled: {conference_2027['settings']['registration_enabled']}")
    else:
        print(f"   ✗ Error: {result_2027.get('error', 'Unknown error')}")
    
    print("\n" + "="*60)
    print("\nDone! Both conferences have been added to Firebase.")
    print("They should now be visible on the website at /conferences")
    print("Registration is enabled for both conferences.")
