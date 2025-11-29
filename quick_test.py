import requests
import json
import time

# Give app time to start
time.sleep(2)

try:
    response = requests.post('http://127.0.0.1:5000/payment/create', 
                           json={'user_id': 'test', 'full_name': 'Test', 'email': 'test@test.com', 'total_amount': 100.0},
                           timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")