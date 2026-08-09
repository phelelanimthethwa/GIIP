"""
Script to upload local default conference cover images to Firebase Storage
and update database image_url fields with public Firebase Storage URLs.
"""
import os
from app import app, db, get_firebase_storage_bucket

def upload_images_to_firebase_storage():
    with app.app_context():
        bucket = get_firebase_storage_bucket()
        image_files = {
            'default-hero.jpg': 'static/images/default-hero.jpg',
            'conference_tech.jpg': 'static/images/conference_tech.jpg',
            'conference_biz.jpg': 'static/images/conference_biz.jpg'
        }
        
        storage_urls = {}
        for name, local_path in image_files.items():
            if os.path.exists(local_path):
                blob = bucket.blob(f'conferences/{name}')
                with open(local_path, 'rb') as f:
                    blob.upload_from_file(f, content_type='image/jpeg')
                blob.make_public()
                storage_urls[name] = blob.public_url
                print(f"Uploaded {name} -> {blob.public_url}")
        
        # Now update conferences in Firebase Realtime Database
        conf_ref = db.reference('conferences')
        confs = conf_ref.get() or {}
        print(f"\nUpdating {len(confs)} conferences in Firebase DB with Firebase Storage URLs...")
        
        for cid, cdata in confs.items():
            basic_info = cdata.get('basic_info', {})
            name = (basic_info.get('name') or '').lower()
            
            if 'tech' in name or 'robotics' in name or 'ai' in name or 'innovation' in name or 'icirt' in name:
                new_url = storage_urls.get('conference_tech.jpg')
            elif 'business' in name or 'economics' in name or 'sustainability' in name or 'icbmse' in name or 'bme' in name:
                new_url = storage_urls.get('conference_biz.jpg')
            else:
                new_url = storage_urls.get('default-hero.jpg')
            
            if new_url:
                db.reference(f'conferences/{cid}/basic_info').update({
                    'image_url': new_url
                })
                print(f"Updated {cid} -> {new_url}")

if __name__ == '__main__':
    upload_images_to_firebase_storage()
