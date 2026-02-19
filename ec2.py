import click
import boto3
import os

# Load tags from environment variables
TAG_CREATED_BY = os.getenv('TAG_CREATED_BY', 'platform-cli')
TAG_OWNER = os.getenv('TAG_OWNER', 'student')

# --- CONFIGURATION ---
ALLOWED_TYPES = ['t3.micro', 't3.small']
MAX_INSTANCES = 2

# SSM Path to the latest Amazon Linux 2 AMI
SSM_AMI_PATH = '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'

def get_ec2_client():
    return boto3.client(
        'ec2',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

def get_latest_ami():
    """Retrieves the ID of the latest Linux AMI via SSM."""
    ssm = boto3.client(
        'ssm',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )
    # Request parameter from AWS by path
    response = ssm.get_parameter(Name=SSM_AMI_PATH)
    ami_id = response['Parameter']['Value']
    return ami_id

@click.group()
def ec2():
    """Manage EC2 virtual machines."""
    pass

@ec2.command()
@click.option('--type', 'instance_type', default='t3.micro', help='Instance type')
@click.option('--key', 'key_name', required=True, help='SSH Key Name')
@click.option('--name', default='my-server', help='Server name')
def create(instance_type, key_name, name):
    """Create a new instance (AMI retrieved from SSM)."""
    ec2_client = get_ec2_client()

    if instance_type not in ALLOWED_TYPES:
        click.echo(f"❌ Error: Type {instance_type} is not allowed.", err=True)
        return

    # Check limit
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:CreatedBy', 'Values': [TAG_CREATED_BY]},
            {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'stopping', 'stopped']}
        ]
    )
    current_count = sum(len(r['Instances']) for r in response['Reservations'])

    if current_count >= MAX_INSTANCES:
        click.echo(f"❌ Error: Limit of {MAX_INSTANCES} instances reached.", err=True)
        return

    # 1. GET AMI DYNAMICALLY
    click.echo("🔎 Searching for latest AMI via SSM...")
    try:
        latest_ami = get_latest_ami()
        click.echo(f"✅ Found AMI: {latest_ami}")
    except Exception as e:
        click.echo(f"❌ Error getting AMI: {e}", err=True)
        return

    # 2. Create Instance
    click.echo(f"🚀 Launching {instance_type} named '{name}'...")
    try:
        instances = ec2_client.run_instances(
            ImageId=latest_ami, 
            InstanceType=instance_type,
            KeyName=key_name,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': name},
                        {'Key': 'CreatedBy', 'Value': TAG_CREATED_BY},
                        {'Key': 'Owner', 'Value': TAG_OWNER}
                    ]
                },
            ]
        )
        instance_id = instances['Instances'][0]['InstanceId']
        click.echo(f"✅ Success! Instance {instance_id} is being created.")
    except Exception as e:
        click.echo(f"AWS Error: {e}", err=True)

@ec2.command()
def list():
    """List our instances."""
    ec2_client = get_ec2_client()
    
    response = ec2_client.describe_instances(
        Filters=[{'Name': 'tag:CreatedBy', 'Values': [TAG_CREATED_BY]}]
    )

    click.echo(f"{'ID':<20} {'Name':<20} {'State':<10} {'Type':<10} {'Public IP'}")
    click.echo("-" * 75)
    
    found = False
    for r in response['Reservations']:
        for i in r['Instances']:
            if i['State']['Name'] == 'terminated':
                continue
            found = True
            public_ip = i.get('PublicIpAddress', 'N/A')
            tags = {t['Key']: t['Value'] for t in i.get('Tags', [])}
            name = tags.get('Name', 'Unknown')
            
            click.echo(f"{i['InstanceId']:<20} {name:<20} {i['State']['Name']:<10} {i['InstanceType']:<10} {public_ip}")
    
    if not found:
        click.echo("No active instances found.")

@ec2.command()
@click.argument('instance_id')
def stop(instance_id):
    """Stop an instance."""
    ec2_client = get_ec2_client()
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        if tags.get('CreatedBy') != TAG_CREATED_BY:
            click.echo(f"❌ Error: Instance {instance_id} is not managed by platform-cli!", err=True)
            return

        ec2_client.stop_instances(InstanceIds=[instance_id])
        click.echo(f"🛑 Stopping {instance_id}...")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@ec2.command()
@click.argument('instance_id')
def start(instance_id):
    """Start an instance."""
    ec2_client = get_ec2_client()
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        if tags.get('CreatedBy') != TAG_CREATED_BY:
            click.echo(f"❌ Error: Instance {instance_id} is not managed by platform-cli!", err=True)
            return

        ec2_client.start_instances(InstanceIds=[instance_id])
        click.echo(f"▶️ Starting {instance_id}...")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@ec2.command()
@click.argument('instance_id')
def terminate(instance_id):
    """TERMINATE an instance permanently."""
    ec2_client = get_ec2_client()
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        if tags.get('CreatedBy') != TAG_CREATED_BY:
            click.echo(f"❌ Error: Instance {instance_id} is not managed by platform-cli!", err=True)
            return

        click.echo(f"⚠️  TERMINATING {instance_id}. Data will be lost.")
        if click.confirm('Are you sure?'):
            ec2_client.terminate_instances(InstanceIds=[instance_id])
            click.echo("✅ Instance terminated.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)