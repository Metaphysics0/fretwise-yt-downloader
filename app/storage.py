import os
import asyncio
from pathlib import Path

import boto3
from botocore.config import Config


def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=os.environ['R2_ENDPOINT'],
        aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )


async def upload_to_r2(
    file_path: Path,
    key: str,
    content_type: str = "application/octet-stream"
) -> str:
    bucket = os.environ['R2_BUCKET_NAME']
    public_url = os.environ['R2_PUBLIC_URL'].rstrip('/')

    client = get_r2_client()

    await asyncio.to_thread(
        client.upload_file,
        Filename=str(file_path),
        Bucket=bucket,
        Key=key,
        ExtraArgs={"ContentType": content_type},
    )

    return f"{public_url}/{key}"
