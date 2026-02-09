import os
from dotenv import load_dotenv
load_dotenv()
import click
import boto3
from ec2 import ec2
from s3 import s3
from route53 import route53

@click.group()
def cli():
    """AWS Resource Management CLI Tool."""
    pass

@cli.command()
def info():
    """Verify AWS connection and current configuration."""
    session = boto3.Session(
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    
    try:
        # Call STS (Security Token Service) to check identity
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        
        click.echo("✅ Connection successful!")
        click.echo(f"Account ID: {identity['Account']}")
        click.echo(f"User ARN:   {identity['Arn']}")
        
        # Display current tag configuration for verification
        click.echo("-" * 20)
        click.echo("Current Tag Configuration:")
        click.echo(f"CreatedBy: {os.getenv('TAG_CREATED_BY')}")
        click.echo(f"Owner:     {os.getenv('TAG_OWNER')}")
        
    except Exception as e:
        click.echo("❌ Connection failed!", err=True)
        click.echo(e, err=True)

# Register commands from other modules
cli.add_command(ec2)
cli.add_command(s3)
cli.add_command(route53)

if __name__ == '__main__':
    cli()