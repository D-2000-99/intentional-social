#!/usr/bin/env python3
"""
Test script to verify pre-signed URL generation for S3 photos.
Run from backend directory: python test_presigned_url.py
"""

import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.s3 import get_s3_client, generate_presigned_url
from app.core.s3 import s3_client  # Import to reset it
from app.config import settings

# Reset the cached client to test with new config
import app.core.s3 as s3_module
s3_module.s3_client = None

def main():
    print("=" * 60)
    print("Testing S3 Pre-signed URL Generation")
    print("=" * 60)
    
    # Print configuration
    print(f"\nAWS Configuration:")
    print(f"  Access Key ID: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "  Access Key ID: NOT SET")
    print(f"  Region: {settings.AWS_REGION}")
    print(f"  Bucket: {settings.S3_BUCKET_NAME}")
    print(f"  Secret Key: {'SET' if settings.AWS_SECRET_ACCESS_KEY else 'NOT SET'}")
    
    # Test S3 key
    test_key = "posts/photos/175/166/20251203_7c8ece7c-876d-4781-829c-22c452d9351c.jpg"
    print(f"\nTest S3 Key: {test_key}")
    
    try:
        # Get S3 client
        print("\n1. Initializing S3 client...")
        client = get_s3_client()
        print("   ✓ S3 client initialized successfully")
        
        # Verify object exists and check permissions
        print("\n2. Verifying object exists and permissions...")
        try:
            client.head_object(Bucket=settings.S3_BUCKET_NAME, Key=test_key)
            print("   ✓ Object exists in S3 (head_object works)")
        except Exception as e:
            print(f"   ✗ Cannot access object with head_object: {e}")
            print("   This might indicate missing s3:GetObject permission")
        
        # Try to actually get the object
        try:
            response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=test_key)
            content_length = response['ContentLength']
            print(f"   ✓ Can read object (get_object works, size: {content_length} bytes)")
        except Exception as e:
            print(f"   ✗ Cannot read object with get_object: {e}")
            print("   ⚠️  This confirms missing s3:GetObject permission!")
            print("   ⚠️  Pre-signed URLs will fail without this permission.")
        
        # Generate pre-signed URL
        print("\n3. Generating pre-signed URL...")
        url = generate_presigned_url(test_key, expiration=600)
        print("   ✓ Pre-signed URL generated successfully")
        
        print(f"\n4. Pre-signed URL (expires in 600 seconds):")
        print("   " + "-" * 56)
        print(f"   {url}")
        print("   " + "-" * 56)
        
        print("\n5. Test with curl:")
        print("   " + "-" * 56)
        print(f"   curl -I '{url}'")
        print("   " + "-" * 56)
        print("\n   Or open in browser:")
        print(f"   {url}")
        
        return url
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    url = main()
    if url:
        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Test failed!")
        print("=" * 60)
        sys.exit(1)

