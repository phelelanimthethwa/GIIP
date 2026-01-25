"""
Script to add all conferences for 2026-2027 that are not already in the database
"""
import os
import sys
import json
from datetime import datetime

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
        cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
        cred = credentials.Certificate(cred_dict)
        print("Using Firebase credentials from environment variable")
    else:
        cred = credentials.Certificate('serviceAccountKey.json')
        print("Using Firebase credentials from serviceAccountKey.json")
    
    firebase_options = {
        'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com',
        'storageBucket': 'giir-66ae6.firebasestorage.app',
    }
    
    try:
        firebase_admin.get_app()
        print("Firebase app already initialized")
    except ValueError:
        firebase_admin.initialize_app(cred, firebase_options)
        print("Firebase initialized successfully")
except Exception as e:
    print(f"Error initializing Firebase: {str(e)}")
    raise

def get_existing_conferences():
    """Get all existing conferences from database"""
    try:
        conferences_ref = db.reference('conferences')
        conferences = conferences_ref.get() or {}
        existing = {}
        for conf_id, conf_data in conferences.items():
            if conf_data and 'basic_info' in conf_data:
                name = conf_data['basic_info'].get('name', '')
                abbreviation = conf_data['basic_info'].get('abbreviation', '')
                year = conf_data['basic_info'].get('year', '')
                # Create a unique key
                key = f"{abbreviation}-{year}".upper()
                existing[key] = {
                    'id': conf_id,
                    'name': name,
                    'abbreviation': abbreviation,
                    'year': year
                }
        return existing
    except Exception as e:
        print(f"Error getting existing conferences: {e}")
        return {}

def create_conference_with_code(conference_data):
    """Create a new conference with an auto-generated unique code"""
    try:
        abbr = conference_data.get('basic_info', {}).get('abbreviation', 'CONF')
        year = conference_data.get('basic_info', {}).get('year', datetime.now().year)
        conference_code = generate_conference_code(abbr, year)

        conference_data['conference_code'] = conference_code
        conference_data['code_generated_at'] = datetime.now().isoformat()

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

# Define all conferences
all_conferences = [
    {
        'key': 'ICETL-2026',
        'basic_info': {
            'name': 'International Conference on Social Science, Education and Learning (ICETL-2026)',
            'description': '''Join the premier Social Science and education conference 2026. Taking place virtually on the 21st – 24th July 2026, the international social sciences and education conference 2026 will host the international community from social and behavioural scientists, educators, representatives of non-profit and government organizations, and other stakeholders to discuss such topics as adult education, pedagogy, ICT, inclusive education, and more.

We invite the international community to take an active role in shaping the future of education. Share your research findings, exchange ideas with fellow academic members, expand your network, and get inspired. The conference will be held every year to make it an ideal platform for people to share views and experiences in education and the related areas.

Toronto, the capital of the province of Ontario, is a major Canadian city along Lake Ontario's northwestern shore. It's a dynamic metropolis with a core of soaring skyscrapers, all dwarfed by the iconic, free-standing CN Tower. Toronto also has many green spaces, from the orderly oval of Queen's Park to 400-acre High Park and its trails, sports facilities and zoo. This is the excellent location for providing academic platforms to share related innovations & practices in pedagogy and explore educational technologies and, at the same time, network for future collaborations in education.

Conference Themes: Economics, Psychology, Anthropology, Sociology, Adult Education, Art Education, Business, Course Management, Curriculum Development, Research and Development, Educational Foundations, Education Policy and Leadership, E-Learning, Gaming, Global Issues in Education and Research, ICT, Inclusive Education, Learning/Teaching Methodologies and Assessment, Online Teaching, English Language Teaching (ELT), Foreign Language Teaching, Pedagogy, Psychology, Research in Progress and Research Management.''',
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
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    },
    {
        'key': 'ICBMSE-2026',
        'basic_info': {
            'name': 'International Conference on Business Management, Sustainability and Economics (ICBMSE-2026)',
            'description': '''International Conference on Business Management, Sustainability and Economics (ICBMSE-2026) will be held virtually during the 26th - 29th October 2026. ICBMSE is to bring together innovative academics and industrial experts in the field of Business Management, Sustainability and Economics to a common forum. This Conference is Organized by the Global Institute on Innovative Research (GIIR).

The primary goal of the conference is to promote research and developmental activities in Business Management, Sustainability and Economics. In addition, it aims to promote scientific information interchange between researchers, economists, students, and practitioners working in and around the world. The conference will be held every year to make it an ideal platform for people to share views and experiences in Business Management, Sustainability and Economics related areas.

Oxford, the historic "City of Dreaming Spires," is home to the prestigious University of Oxford. The city features stunning collegiate architecture, the Bodleian Library, the Ashmolean Museum, historic colleges, Oxford University Press, and rich heritage originating as an "oxen's ford." This is an ideal location for international academic networking.''',
            'year': 2026,
            'abbreviation': 'ICBMSE',
            'status': 'upcoming',
            'event_type': 'virtual',
            'start_date': '2026-10-26',
            'end_date': '2026-10-29',
            'location': 'Oxford, UK',
            'website': '',
            'timezone': 'UTC'
        },
        'settings': {
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    },
    {
        'key': 'ICIRT-2027',
        'basic_info': {
            'name': 'International Conference on Innovation, Robotics and Applied Technology (ICIRT-2027)',
            'description': '''International Conference on Innovation, Robotics and Applied Technology (ICIRT-2027) will be held virtually during the 26th - 29th January 2027. ICIRT is to bring together innovative academics and industrial experts in the field of Science Technology and Management to a common forum. This Conference is Organized by the Global Institute on Innovative Research (GIIR).

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
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    },
    {
        'key': 'ICBMSE-2027-PARIS',
        'basic_info': {
            'name': 'International Conference on Business Management, Sustainability and Economics (ICBMSE-2027 Paris)',
            'description': '''International Conference on Business Management, Sustainability and Economics (ICBMSE-2027) will be held virtually during the 19th - 22nd April 2027. ICBMSE is to bring together innovative academics and industrial experts in the field of Business Management, Sustainability and Economics to a common forum. This Conference is Organized by the Global Institute on Innovative Research (GIIR).

The primary goal of the conference is to promote research and developmental activities in Business Management, Sustainability and Economics. In addition, it aims to promote scientific information interchange between researchers, economists, students, and practitioners working in and around the world. The conference will be held every year to make it an ideal platform for people to share views and experiences in Business Management, Sustainability and Economics related areas.

Paris, France's capital, is a major European city and a global center for art, fashion, gastronomy and culture. Its 19th-century cityscape is crisscrossed by wide boulevards and the River Seine. Beyond such landmarks as the Eiffel Tower and the 12th-century, Gothic Notre-Dame cathedral, the city is known for its café culture and designer boutiques along the Rue du Faubourg Saint-Honoré.''',
            'year': 2027,
            'abbreviation': 'ICBMSE',
            'status': 'upcoming',
            'event_type': 'virtual',
            'start_date': '2027-04-19',
            'end_date': '2027-04-22',
            'location': 'Paris, France',
            'website': '',
            'timezone': 'UTC'
        },
        'settings': {
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    },
    {
        'key': 'ETL-2027',
        'basic_info': {
            'name': 'International Conference on Social Science, Education and Learning (ETL-2027)',
            'description': '''International Conference on Social Science, Education and Learning (ETL-2027) will be held virtually during the 27th - 30th July 2027. The conference will host the international community from social and behavioural scientists, educators, representatives of non-profit and government organizations, and other stakeholders to discuss such topics as adult education, pedagogy, ICT, inclusive education, and more.

We invite the international community to take an active role in shaping the future of education. Share your research findings, exchange ideas with fellow academic members, expand your network, and get inspired. The conference will be held every year to make it an ideal platform for people to share views and experiences in education and the related areas.

Rome, Italy's capital and most populated commune, is famous for its unparalleled history, ancient ruins (Colosseum, Roman Forum), Renaissance art (Sistine Chapel), Vatican City (St. Peter's Basilica), iconic Trevi Fountain, and vibrant culture. A major political, cultural, and religious center where past and present blend seamlessly.

Conference Themes: Economics, Psychology, Anthropology, Sociology, Adult Education, Art Education, Business, Course Management, Curriculum Development, Research and Development, Educational Foundations, Education Policy and Leadership, E-Learning, Gaming, Global Issues in Education and Research, ICT, Inclusive Education, Learning/Teaching Methodologies and Assessment, Online Teaching, English Language Teaching (ELT), Foreign Language Teaching, Pedagogy, Psychology, Research in Progress and Research Management.''',
            'year': 2027,
            'abbreviation': 'ETL',
            'status': 'upcoming',
            'event_type': 'virtual',
            'start_date': '2027-07-27',
            'end_date': '2027-07-30',
            'location': 'Rome, Italy',
            'website': '',
            'timezone': 'UTC'
        },
        'settings': {
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    },
    {
        'key': 'ICBMSE-2027-COPENHAGEN',
        'basic_info': {
            'name': 'International Conference on Business Management, Sustainability and Economics (ICBMSE-2027 Copenhagen)',
            'description': '''International Conference on Business Management, Sustainability and Economics (ICBMSE-2027) will be held virtually during the 8th - 11th November 2027. ICBMSE is to bring together innovative academics and industrial experts in the field of Business Management, Sustainability and Economics to a common forum. This Conference is Organized by the Global Institute on Innovative Research (GIIR).

The primary goal of the conference is to promote research and developmental activities in Business Management, Sustainability and Economics. In addition, it aims to promote scientific information interchange between researchers, economists, students, and practitioners working in and around the world. The conference will be held every year to make it an ideal platform for people to share views and experiences in Business Management, Sustainability and Economics related areas.

Copenhagen, Denmark's capital on the coastal islands of Zealand and Amager, is known for its blend of historic charm and modern design, sustainable living, world-class New Nordic cuisine, royal palaces (Amalienborg, Rosenborg), iconic Nyhavn harbour, Tivoli Gardens, excellent cycling culture, and rich Viking settlement history. Connected to Sweden by the Øresund Bridge.''',
            'year': 2027,
            'abbreviation': 'ICBMSE',
            'status': 'upcoming',
            'event_type': 'virtual',
            'start_date': '2027-11-08',
            'end_date': '2027-11-11',
            'location': 'Copenhagen, Denmark',
            'website': '',
            'timezone': 'UTC'
        },
        'settings': {
            'registration_enabled': True,
            'paper_submission_enabled': True,
            'gallery_enabled': True,
            'email_notifications': True,
            'max_registrations': 1000,
            'max_paper_submissions': 500
        }
    }
]

if __name__ == '__main__':
    print("="*70)
    print("ADDING CONFERENCES TO DATABASE")
    print("="*70)
    
    # Get existing conferences
    print("\nChecking existing conferences...")
    existing = get_existing_conferences()
    print(f"Found {len(existing)} existing conference(s)")
    if existing:
        print("Existing conferences:")
        for key, info in existing.items():
            print(f"  - {key}: {info['name']}")
    
    print("\n" + "="*70)
    print("PROCESSING CONFERENCES")
    print("="*70)
    
    added_count = 0
    skipped_count = 0
    
    for conf_data in all_conferences:
        key = conf_data['key']
        abbreviation = conf_data['basic_info']['abbreviation']
        year = conf_data['basic_info']['year']
        lookup_key = f"{abbreviation}-{year}".upper()
        
        # Check if already exists
        if lookup_key in existing:
            print(f"\n[SKIP] {key} already exists (ID: {existing[lookup_key]['id']})")
            skipped_count += 1
            continue
        
        # Check for similar conferences (same abbreviation and year but different location)
        # For ICBMSE-2027, we have Paris and Copenhagen versions
        if key.startswith('ICBMSE-2027'):
            # Check if any ICBMSE-2027 exists
            found_similar = False
            for existing_key, existing_info in existing.items():
                if existing_info['abbreviation'] == 'ICBMSE' and existing_info['year'] == 2027:
                    # Check location in name
                    conf_name = conf_data['basic_info']['name']
                    if 'Paris' in conf_name or 'Copenhagen' in conf_name:
                        # This is a location-specific version, allow it
                        pass
                    else:
                        found_similar = True
                        break
            
            if found_similar and 'Paris' not in conf_data['basic_info']['name'] and 'Copenhagen' not in conf_data['basic_info']['name']:
                print(f"\n[SKIP] {key} - Similar conference already exists")
                skipped_count += 1
                continue
        
        # Create the conference
        print(f"\n[ADD] {key}...")
        conference_data = {
            'basic_info': conf_data['basic_info'],
            'settings': conf_data['settings'],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'created_by': 'system',
                'version': '1.0.0'
            }
        }
        
        result = create_conference_with_code(conference_data)
        if result['success']:
            print(f"  [OK] Successfully created!")
            print(f"    Conference ID: {result['conference_id']}")
            print(f"    Conference Code: {result['conference_code']}")
            print(f"    Name: {conference_data['basic_info']['name']}")
            print(f"    Dates: {conference_data['basic_info']['start_date']} to {conference_data['basic_info']['end_date']}")
            print(f"    Location: {conference_data['basic_info']['location']}")
            added_count += 1
        else:
            print(f"  [ERROR] Error: {result.get('error', 'Unknown error')}")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Added: {added_count} conference(s)")
    print(f"Skipped: {skipped_count} conference(s)")
    print(f"Total processed: {len(all_conferences)} conference(s)")
    print("="*70)
    print("\nDone! Conferences are now available at /admin/conferences")
