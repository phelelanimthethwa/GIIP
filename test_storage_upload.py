#!/usr/bin/env python3
"""
Test script to verify Firebase Storage upload functionality
"""

import os
from PIL import Image
import io
from datetime import datetime
from werkzeug.utils import secure_filename

def create_test_image():
    """Create a small test image for upload testing"""
    img = Image.new('RGB', (200, 200), color='blue')
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='JPEG')
    img_buffer.seek(0)
    return img_buffer

def test_storage_upload():
    """Test Firebase Storage upload functionality"""
    print("🧪 Testing Firebase Storage Upload...")

    try:
        from app import storage, db
        from flask_login import current_user
        from werkzeug.datastructures import FileStorage

        print("✅ Firebase imports successful")

        # Create test image
        test_image = create_test_image()
        test_filename = "test_upload.jpg"

        # Create a mock file object
        class MockFile:
            def __init__(self, buffer, filename):
                self.stream = buffer
                self.filename = filename
                self.content_type = 'image/jpeg'

            def read(self):
                return self.stream.getvalue()

            def seek(self, pos):
                self.stream.seek(pos)

        mock_file = MockFile(test_image, test_filename)

        # Test conference ID
        conference_id = "-OUGIiqFvUF3oGHzeZGK"

        print("📤 Testing upload process...")

        # Generate unique filename
        filename = secure_filename(f"{conference_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mock_file.filename}")
        file_path = f"gallery/{conference_id}/{filename}"

        print(f"📁 Generated filename: {filename}")
        print(f"🗂️ File path: {file_path}")

        # Get file size before upload
        file_size = len(mock_file.read())
        mock_file.seek(0)  # Reset file pointer

        print(f"📊 File size: {file_size} bytes")

        # Upload to Firebase Storage
        print("🔥 Uploading to Firebase Storage...")
        bucket = storage.bucket()
        blob = bucket.blob(file_path)

        blob.upload_from_file(mock_file, content_type=mock_file.content_type)
        blob.make_public()

        print("✅ Successfully uploaded to Firebase Storage")

        # Get public URL
        image_url = blob.public_url
        print(f"📎 Public URL: {image_url}")

        # Save image metadata to database
        image_data = {
            'filename': filename,
            'original_name': mock_file.filename,
            'url': image_url,
            'uploaded_by': 'test@example.com',
            'uploaded_at': datetime.now().isoformat(),
            'conference_id': conference_id,
            'file_size': file_size,
            'content_type': mock_file.content_type
        }

        gallery_ref = db.reference(f'conferences/{conference_id}/gallery')
        new_image_ref = gallery_ref.push(image_data)

        print(f"💾 Saved to database with ID: {new_image_ref.key}")

        print("✅ Firebase Storage upload test completed successfully!")

        # Clean up test data
        print("🧹 Cleaning up test data...")
        blob.delete()
        new_image_ref.delete()
        print("✅ Test data cleaned up")

    except Exception as e:
        print(f"❌ Storage test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_storage_upload()
