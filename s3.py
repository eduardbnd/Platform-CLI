import click
import boto3
import os
from botocore.exceptions import ClientError

# Load tags from environment variables
TAG_CREATED_BY = os.getenv('TAG_CREATED_BY', 'platform-cli')
TAG_OWNER = os.getenv('TAG_OWNER', 'student')

def get_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

@click.group()
def s3():
    """Manage S3 Buckets."""
    pass

@s3.command()
@click.argument('bucket_name')
@click.option('--public', is_flag=True, help='Make bucket public (Dangerous!)')
def create(bucket_name, public):
    """Create a new S3 bucket."""
    bucket_name = bucket_name.lower()
    s3_client = get_s3_client()
    region = os.getenv('AWS_REGION')

    if public:
        click.echo(f"⚠️  WARNING: You are about to make bucket '{bucket_name}' PUBLIC.")
        if not click.confirm('Are you absolutely sure?'):
            click.echo("Operation cancelled.")
            return

    try:
        # Create bucket
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )

        # APPLY TAGS FROM ENV VARIABLES
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': [
                    {'Key': 'CreatedBy', 'Value': TAG_CREATED_BY},
                    {'Key': 'Owner', 'Value': TAG_OWNER}
                ]
            }
        )

        if public:
            s3_client.delete_public_access_block(Bucket=bucket_name)
            click.echo(f"🔓 Bucket '{bucket_name}' created (Public).")
        else:
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True, 'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True, 'RestrictPublicBuckets': True
                }
            )
            click.echo(f"🔒 Bucket '{bucket_name}' created (Private).")

    except ClientError as e:
        click.echo(f"AWS Error: {e}", err=True)

@s3.command()
def list():
    """List ONLY our buckets."""
    s3_client = get_s3_client()
    try:
        response = s3_client.list_buckets()
        click.echo(f"{'Bucket Name':<40} {'Creation Date'}")
        click.echo("-" * 65)
        
        found = False
        for bucket in response['Buckets']:
            name = bucket['Name']
            try:
                tags_resp = s3_client.get_bucket_tagging(Bucket=name)
                tags = {t['Key']: t['Value'] for t in tags_resp['TagSet']}
                
                # Compare with environment variable
                if tags.get('CreatedBy') == TAG_CREATED_BY:
                    found = True
                    click.echo(f"{name:<40} {bucket['CreationDate']}")
            except ClientError:
                continue

        if not found:
            click.echo("No buckets found.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@s3.command()
@click.argument('bucket_name')
@click.argument('file_path')
def upload(bucket_name, file_path):
    """Upload a file to a bucket."""
    s3_client = get_s3_client()
    if not os.path.exists(file_path):
        click.echo(f"❌ Error: File '{file_path}' not found.", err=True)
        return

    try:
        file_name = os.path.basename(file_path)
        click.echo(f"⬆️ Uploading '{file_name}'...")
        s3_client.upload_file(file_path, bucket_name, file_name)
        click.echo(f"✅ Success! File uploaded.")
    except Exception as e:
        click.echo(f"AWS Error: {e}", err=True)