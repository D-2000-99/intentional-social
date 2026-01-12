#!/usr/bin/env python3
"""
Migration script to copy data from AWS S3 to Cloudflare R2.

This script:
1. Connects to the source S3 bucket
2. Lists all objects in the S3 bucket
3. Copies each object to the destination R2 bucket (preserving keys)
4. Optionally verifies the copy was successful
5. Provides progress reporting

Usage:
    python migrate_s3_to_r2.py [--dry-run] [--verify] [--prefix PREFIX]

Environment variables required:
    S3_SOURCE_ACCESS_KEY_ID: AWS S3 access key ID (source)
    S3_SOURCE_SECRET_ACCESS_KEY: AWS S3 secret access key (source)
    S3_SOURCE_REGION: AWS S3 region (default: us-east-1)
    S3_SOURCE_BUCKET_NAME: AWS S3 bucket name (source)
    
    R2_ACCESS_KEY_ID: Cloudflare R2 access key ID (destination)
    R2_SECRET_ACCESS_KEY: Cloudflare R2 secret access key (destination)
    R2_ENDPOINT_URL: Cloudflare R2 endpoint URL
    R2_BUCKET_NAME: Cloudflare R2 bucket name (destination)
"""

import argparse
import logging
import sys
import time
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('s3_to_r2_migration.log')
    ]
)
logger = logging.getLogger(__name__)


def get_s3_client(access_key: str, secret_key: str, region: str, endpoint_url: Optional[str] = None):
    """
    Create an S3-compatible client (works for both AWS S3 and Cloudflare R2).
    
    Args:
        access_key: Access key ID
        secret_key: Secret access key
        region: Region (or "auto" for R2)
        endpoint_url: Optional endpoint URL (required for R2)
    
    Returns:
        boto3 S3 client
    """
    config = Config(
        signature_version='s3v4',
        region_name=region if region != "auto" else "us-east-1",
    )
    
    client_kwargs = {
        'aws_access_key_id': access_key,
        'aws_secret_access_key': secret_key,
        'config': config,
    }
    
    if endpoint_url:
        client_kwargs['endpoint_url'] = endpoint_url
    
    if region != "auto":
        client_kwargs['region_name'] = region
    
    return boto3.client('s3', **client_kwargs)


def list_all_objects(s3_client, bucket_name: str, prefix: Optional[str] = None):
    """
    List all objects in an S3/R2 bucket.
    
    Args:
        s3_client: boto3 S3 client
        bucket_name: Bucket name
        prefix: Optional prefix to filter objects
    
    Yields:
        Object keys (strings)
    """
    paginator = s3_client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix or '')
    
    object_count = 0
    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                object_count += 1
                yield obj['Key']
    
    logger.info(f"Found {object_count} objects in bucket '{bucket_name}' (prefix: {prefix or 'all'})")


def copy_object(
    source_client,
    source_bucket: str,
    dest_client,
    dest_bucket: str,
    key: str,
    verify: bool = False
) -> bool:
    """
    Copy a single object from source to destination.
    
    Args:
        source_client: Source S3 client
        source_bucket: Source bucket name
        dest_client: Destination S3 client (R2)
        dest_bucket: Destination bucket name
        key: Object key
        verify: Whether to verify the copy by comparing sizes
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get object metadata from source
        source_metadata = source_client.head_object(Bucket=source_bucket, Key=key)
        source_size = source_metadata['ContentLength']
        content_type = source_metadata.get('ContentType', 'binary/octet-stream')
        
        # Copy object using copy_from (more efficient than download + upload)
        # Note: copy_from works within the same service, but not cross-service
        # So we need to download and upload
        logger.debug(f"Copying {key} ({source_size} bytes)...")
        
        # Download from source
        source_response = source_client.get_object(Bucket=source_bucket, Key=key)
        body = source_response['Body'].read()
        
        # Upload to destination
        dest_client.put_object(
            Bucket=dest_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            Metadata=source_metadata.get('Metadata', {})
        )
        
        # Verify if requested
        if verify:
            dest_metadata = dest_client.head_object(Bucket=dest_bucket, Key=key)
            dest_size = dest_metadata['ContentLength']
            
            if source_size != dest_size:
                logger.error(f"Size mismatch for {key}: source={source_size}, dest={dest_size}")
                return False
            
            logger.debug(f"Verified {key}: {source_size} bytes")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"Error copying {key}: {error_code} - {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error copying {key}: {str(e)}")
        return False


def object_exists(client, bucket_name: str, key: str) -> bool:
    """
    Check if an object exists in the bucket.
    
    Args:
        client: S3 client
        bucket_name: Bucket name
        key: Object key
    
    Returns:
        True if object exists, False otherwise
    """
    try:
        client.head_object(Bucket=bucket_name, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Migrate data from AWS S3 to Cloudflare R2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='List objects that would be copied without actually copying'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify each copied object by comparing sizes'
    )
    parser.add_argument(
        '--prefix',
        type=str,
        default=None,
        help='Only copy objects with this prefix (e.g., "posts/photos/")'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip objects that already exist in the destination'
    )
    
    args = parser.parse_args()
    
    # Load environment variables
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Source S3 configuration
    s3_access_key = os.getenv('S3_SOURCE_ACCESS_KEY_ID')
    s3_secret_key = os.getenv('S3_SOURCE_SECRET_ACCESS_KEY')
    s3_region = os.getenv('S3_SOURCE_REGION', 'us-east-1')
    s3_bucket = os.getenv('S3_SOURCE_BUCKET_NAME')
    
    # Destination R2 configuration
    r2_access_key = os.getenv('R2_ACCESS_KEY_ID')
    r2_secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
    r2_endpoint = os.getenv('R2_ENDPOINT_URL')
    r2_bucket = os.getenv('R2_BUCKET_NAME')
    
    # Validate configuration
    missing_vars = []
    if not s3_access_key:
        missing_vars.append('S3_SOURCE_ACCESS_KEY_ID')
    if not s3_secret_key:
        missing_vars.append('S3_SOURCE_SECRET_ACCESS_KEY')
    if not s3_bucket:
        missing_vars.append('S3_SOURCE_BUCKET_NAME')
    if not r2_access_key:
        missing_vars.append('R2_ACCESS_KEY_ID')
    if not r2_secret_key:
        missing_vars.append('R2_SECRET_ACCESS_KEY')
    if not r2_endpoint:
        missing_vars.append('R2_ENDPOINT_URL')
    if not r2_bucket:
        missing_vars.append('R2_BUCKET_NAME')
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these in your .env file or environment")
        sys.exit(1)
    
    logger.info("=" * 80)
    logger.info("S3 to R2 Migration Script")
    logger.info("=" * 80)
    logger.info(f"Source: S3 bucket '{s3_bucket}' in region '{s3_region}'")
    logger.info(f"Destination: R2 bucket '{r2_bucket}' at {r2_endpoint}")
    if args.prefix:
        logger.info(f"Prefix filter: {args.prefix}")
    if args.dry_run:
        logger.info("DRY RUN MODE - No objects will be copied")
    if args.verify:
        logger.info("Verification enabled - will verify each copied object")
    if args.skip_existing:
        logger.info("Skip existing enabled - will skip objects that already exist")
    logger.info("=" * 80)
    
    try:
        # Create clients
        logger.info("Connecting to source S3 bucket...")
        source_client = get_s3_client(s3_access_key, s3_secret_key, s3_region)
        
        # Test source connection
        try:
            source_client.head_bucket(Bucket=s3_bucket)
            logger.info(f"✓ Successfully connected to source S3 bucket '{s3_bucket}'")
        except ClientError as e:
            logger.error(f"Failed to connect to source S3 bucket: {str(e)}")
            sys.exit(1)
        
        logger.info("Connecting to destination R2 bucket...")
        dest_client = get_s3_client(r2_access_key, r2_secret_key, "auto", r2_endpoint)
        
        # Test destination connection
        try:
            dest_client.head_bucket(Bucket=r2_bucket)
            logger.info(f"✓ Successfully connected to destination R2 bucket '{r2_bucket}'")
        except ClientError as e:
            logger.error(f"Failed to connect to destination R2 bucket: {str(e)}")
            sys.exit(1)
        
        # List all objects
        logger.info("\nListing objects from source bucket...")
        objects = list(list_all_objects(source_client, s3_bucket, args.prefix))
        
        if not objects:
            logger.warning("No objects found in source bucket")
            sys.exit(0)
        
        total_objects = len(objects)
        logger.info(f"\nFound {total_objects} objects to migrate")
        
        if args.dry_run:
            logger.info("\nDRY RUN - Objects that would be copied:")
            for i, key in enumerate(objects, 1):
                logger.info(f"  {i}. {key}")
            logger.info(f"\nTotal: {total_objects} objects")
            sys.exit(0)
        
        # Copy objects
        logger.info("\nStarting migration...")
        start_time = time.time()
        copied = 0
        skipped = 0
        failed = 0
        
        for i, key in enumerate(objects, 1):
            # Check if object already exists
            if args.skip_existing and object_exists(dest_client, r2_bucket, key):
                logger.info(f"[{i}/{total_objects}] Skipping (exists): {key}")
                skipped += 1
                continue
            
            # Copy object
            logger.info(f"[{i}/{total_objects}] Copying: {key}")
            success = copy_object(
                source_client,
                s3_bucket,
                dest_client,
                r2_bucket,
                key,
                verify=args.verify
            )
            
            if success:
                copied += 1
            else:
                failed += 1
                logger.warning(f"Failed to copy: {key}")
            
            # Progress update every 10 objects
            if i % 10 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total_objects - i) / rate if rate > 0 else 0
                logger.info(
                    f"Progress: {i}/{total_objects} objects "
                    f"({copied} copied, {skipped} skipped, {failed} failed) "
                    f"- ETA: {remaining:.0f}s"
                )
        
        # Final summary
        elapsed_time = time.time() - start_time
        logger.info("\n" + "=" * 80)
        logger.info("Migration Summary")
        logger.info("=" * 80)
        logger.info(f"Total objects: {total_objects}")
        logger.info(f"Successfully copied: {copied}")
        logger.info(f"Skipped (existing): {skipped}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Time elapsed: {elapsed_time:.2f} seconds")
        if copied > 0:
            logger.info(f"Average rate: {copied / elapsed_time:.2f} objects/second")
        logger.info("=" * 80)
        
        if failed > 0:
            logger.warning(f"Migration completed with {failed} errors. Check the log for details.")
            sys.exit(1)
        else:
            logger.info("Migration completed successfully!")
            sys.exit(0)
    
    except NoCredentialsError:
        logger.error("Credentials not found. Please check your environment variables.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

