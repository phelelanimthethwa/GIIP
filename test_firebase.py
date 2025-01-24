import firebase_admin
from firebase_admin import credentials, db

def test_firebase_connection():
    try:
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://giir-66ae6-default-rtdb.firebaseio.com'
        })
        
        # Test database connection
        ref = db.reference('/')
        data = ref.get()
        print('Database connection successful!')
        print('Data:', data)
        return True
    except Exception as e:
        print('Error connecting to Firebase:', str(e))
        return False

if __name__ == '__main__':
    test_firebase_connection() 