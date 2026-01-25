"""
Direct script to add conferences using Flask app context
Run this with: python -m flask shell < add_conferences_direct.py
Or: python add_conferences_direct.py (if Flask app is importable)
"""

# This script should be run from the Flask app context
# You can run it with: flask shell < add_conferences_direct.py
# Or import app and run with app.app_context()

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, create_conference_with_code, db
    from datetime import datetime
    from flask_login import current_user
    
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
            'registration_enabled': True,
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
            'registration_enabled': True,
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
    
    with app.app_context():
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
        
except ImportError as e:
    print(f"Error importing Flask app: {e}")
    print("\nTo run this script:")
    print("1. Make sure you're in the project directory")
    print("2. Run: flask shell < add_conferences_direct.py")
    print("   OR")
    print("3. Use the admin panel button: 'Add 2026 & 2027 Conferences'")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
