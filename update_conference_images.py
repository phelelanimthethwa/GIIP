"""
Script to update Firebase conferences with cover images and hero display preferences
"""
from app import app, db

def update_conferences():
    with app.app_context():
        conf_ref = db.reference('conferences')
        confs = conf_ref.get() or {}
        print(f"Updating {len(confs)} conferences in Firebase...")
        
        for cid, cdata in confs.items():
            basic_info = cdata.get('basic_info', {})
            name = (basic_info.get('name') or '').lower()
            
            # Select appropriate cover image based on conference theme/name
            if 'tech' in name or 'robotics' in name or 'ai' in name or 'innovation' in name or 'icirt' in name:
                img_url = '/static/images/conference_tech.jpg'
                hero_style = 'background'
            elif 'business' in name or 'economics' in name or 'sustainability' in name or 'icbmse' in name or 'bme' in name:
                img_url = '/static/images/conference_biz.jpg'
                hero_style = 'background'
            else:
                img_url = '/static/images/default-hero.jpg'
                hero_style = 'background'
            
            # Update basic_info in Firebase
            conf_basic_ref = db.reference(f'conferences/{cid}/basic_info')
            conf_basic_ref.update({
                'image_url': img_url,
                'hero_style': hero_style
            })
            print(f"Updated {cid}: {basic_info.get('name')[:50]}... -> image: {img_url}, hero_style: {hero_style}")

if __name__ == '__main__':
    update_conferences()
