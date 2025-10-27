#!/usr/bin/env python
"""Quick test script to verify sitemap works"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from django.test import Client

client = Client()

print("Testing /robots.txt...")
response = client.get('/robots.txt')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✓ robots.txt works!")
    print(response.content.decode()[:200])
else:
    print("✗ robots.txt failed")

print("\n" + "="*50 + "\n")

print("Testing /sitemap.xml...")
response = client.get('/sitemap.xml')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✓ sitemap.xml works!")
    print(response.content.decode()[:300])
else:
    print("✗ sitemap.xml failed")
    print(f"Error: {response.content.decode()[:500]}")

print("\n" + "="*50)
print("Test complete!")
