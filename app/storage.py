"""
Cloudflare R2 blob storage utilities.

Uses boto3 with S3-compatible API to upload files to Cloudflare R2.

Required environment variables:
    R2_ACCESS_KEY_ID: Cloudflare R2 access key ID
    R2_SECRET_ACCESS_KEY: Cloudflare R2 secret access key
    R2_ENDPOINT: R2 endpoint URL (e.g., https://{account_id}.r2.cloudflarestorage.com)
    R2_BUCKET_NAME: R2 bucket name
    R2_PUBLIC_URL: Public URL for the bucket (e.g., https://pub-xxx.r2.dev)
"""

import os
import asyncio

import boto3
from botocore.config import Config


def get_r2_client():
    """Create and return an S3-compatible client for Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )


async def upload_to_r2(
    file_bytes: bytes,
    key: str,
    content_type: str = "application/octet-stream"
) -> str:
    """
    Upload file to Cloudflare R2 and return public URL.

    Args:
        file_bytes: The file content as bytes
        key: The object key (path) in the bucket
        content_type: MIME type of the file

    Returns:
        Public URL for the uploaded file
    """
    bucket = os.environ['R2_BUCKET_NAME']
    public_url = os.environ['R2_PUBLIC_URL'].rstrip('/')

    client = get_r2_client()

    await asyncio.to_thread(
        client.put_object,
        Bucket=bucket,
        Key=key,
        Body=file_bytes,
        ContentType=content_type
    )

    return f"{public_url}/{key}"
