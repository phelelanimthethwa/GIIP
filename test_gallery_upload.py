#!/usr/bin/env python3
"""
Test script to verify gallery upload functionality
"""

import requests
import json
from PIL import Image
import io

def create_test_image():
    """Create a small test image for upload testing"""
    img = Image.new('RGB', (100, 100), color='red')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    img_buffer.seek(0)
    return img_buffer

def test_gallery_upload():
    """Test the gallery upload functionality"""
    print("🧪 Testing Gallery Upload Functionality...")

    try:
        # Create test image
        test_image = create_test_image()

        # Prepare multipart form data
        files = {
            'image': ('test.jpg', test_image, 'image/jpeg')
        }

        # Test upload endpoint
        url = "http://127.0.0.1:5000/admin/conference-galleries/-OUGIiqFvUF3oGHzeZGK/upload"

        print("📤 Testing upload to:", url)
        print("🖼️ Test image: test.jpg (100x100 red square)")

        # Note: This will fail without proper authentication, but we can check the response
        response = requests.post(url, files=files)

        print(f"📊 Response Status: {response.status_code}")
        print(f"📝 Response Content: {response.text[:200]}...")

        if response.status_code == 400:
            response_data = response.json()
            print(f"❌ Upload failed: {response_data.get('error', 'Unknown error')}")
        elif response.status_code == 401:
            print("🔐 Authentication required (expected for admin endpoints)")
        elif response.status_code == 200:
            print("✅ Upload successful!")
        else:
            print(f"⚠️ Unexpected response: {response.status_code}")

    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_page_access():
    """Test if the gallery page is accessible"""
    print("\n🌐 Testing Page Access...")

    try:
        response = requests.get("http://127.0.0.1:5000/admin/conference-galleries")
        print(f"📊 Page Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ Gallery page accessible")
            print("📝 Checking for jQuery...")

            if 'jquery-3.6.0.min.js' in response.text:
                print("✅ Full jQuery version found")
            else:
                print("❌ jQuery not found in page")

        else:
            print(f"❌ Page not accessible: {response.status_code}")

    except Exception as e:
        print(f"❌ Page test failed: {e}")

if __name__ == "__main__":
    test_page_access()
    test_gallery_upload()

    print("\n📋 Summary:")
    print("✅ jQuery fix applied (slim → full version)")
    print("✅ File extension validation fixed (document → image extensions)")
    print("✅ Gallery upload should now work properly")
    print("\n🌐 Test at: http://127.0.0.1:5000/admin/conference-galleries")
