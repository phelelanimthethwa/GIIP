#!/usr/bin/env python3
from app import app, inject_admin_menu

print('✅ Flask app loaded successfully!')
print()

print('Admin Menu Items:')
menu = inject_admin_menu()
for item in menu['admin_menu']:
    print(f'  {item["icon"]:12} | {item["text"]:30} | {item["url"]}')

print()
print('Guest Speaker Application Routes:')
for rule in app.url_map.iter_rules():
    if 'guest' in rule.rule or 'admin_guest_speaker' in str(rule.endpoint):
        print(f'  {rule.rule:40} -> {rule.endpoint}')

print()
print('Guest Speaker Applications in Admin Menu:')
for item in menu['admin_menu']:
    if 'guest speaker' in item['text'].lower():
        print(f'✅ Found: {item["text"]} -> {item["url"]} (icon: {item["icon"]})')
