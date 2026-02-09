import click
import boto3
import os
import time

# Load tags from environment variables
TAG_CREATED_BY = os.getenv('TAG_CREATED_BY', 'platform-cli')
TAG_OWNER = os.getenv('TAG_OWNER', 'student')

def get_route53_client():
    return boto3.client(
        'route53',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION')
    )

@click.group()
def route53():
    """Manage Route53 DNS Zones."""
    pass

@route53.command()
@click.argument('domain_name')
def create_zone(domain_name):
    """Create a new Hosted Zone."""
    client = get_route53_client()
    caller_ref = f"{domain_name}-{int(time.time())}"

    click.echo(f"🌐 Creating zone for {domain_name}...")
    try:
        response = client.create_hosted_zone(
            Name=domain_name,
            CallerReference=caller_ref,
            HostedZoneConfig={'Comment': 'Managed by platform-cli', 'PrivateZone': False}
        )
        
        zone_id = response['HostedZone']['Id']
        clean_zone_id = zone_id.split('/')[-1]
        click.echo(f"✅ Zone created! ID: {clean_zone_id}")

        client.change_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=clean_zone_id,
            AddTags=[
                {'Key': 'CreatedBy', 'Value': TAG_CREATED_BY},
                {'Key': 'Owner', 'Value': TAG_OWNER}
            ]
        )
        click.echo("🏷️ Tags successfully added.")
    except Exception as e:
        click.echo(f"AWS Error: {e}", err=True)

@route53.command()
def list():
    """List ONLY our zones."""
    client = get_route53_client()
    try:
        response = client.list_hosted_zones()
        click.echo(f"{'Zone ID':<20} {'Name':<25} {'Records'}")
        click.echo("-" * 60)
        
        found = False
        for zone in response['HostedZones']:
            zone_id = zone['Id'].split('/')[-1]
            try:
                tags_resp = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)
                tags = {t['Key']: t['Value'] for t in tags_resp['ResourceTagSet']['Tags']}
                
                if tags.get('CreatedBy') == TAG_CREATED_BY:
                    found = True
                    click.echo(f"{zone_id:<20} {zone['Name']:<25} {zone['ResourceRecordSetCount']}")
            except Exception:
                continue

        if not found:
            click.echo("No zones found.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@route53.command()
@click.argument('zone_id')
@click.argument('subdomain')
@click.argument('ip_address')
def add_record(zone_id, subdomain, ip_address):
    """Add an A-record (script automatically appends domain name)."""
    client = get_route53_client()
    
    # 1. Check Permissions
    try:
        tags_resp = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)
        tags = {t['Key']: t['Value'] for t in tags_resp['ResourceTagSet']['Tags']}
        
        if tags.get('CreatedBy') != TAG_CREATED_BY:
            click.echo(f"❌ Error: Zone {zone_id} is not managed by platform-cli!", err=True)
            return
    except Exception as e:
        click.echo(f"Permission check error: {e}", err=True)
        return

    # 2. Get Zone Name to construct Full Qualified Domain Name (FQDN)
    try:
        zone_info = client.get_hosted_zone(Id=zone_id)
        zone_name = zone_info['HostedZone']['Name'] # returns "example.com."
        
        # Combine subdomain + zone_name -> "www.example.com."
        full_record_name = f"{subdomain}.{zone_name}"
        
    except Exception as e:
        click.echo(f"❌ Error fetching zone info: {e}", err=True)
        return

    click.echo(f"📝 Adding record {full_record_name} -> {ip_address}...")
    
    # 3. Create Record
    try:
        change_batch = {
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': full_record_name, # <-- Используем полное имя
                    'Type': 'A', 
                    'TTL': 300,
                    'ResourceRecords': [{'Value': ip_address}]
                }
            }]
        }
        client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)
        click.echo("✅ Record added.")
    except Exception as e:
        click.echo(f"AWS Error: {e}", err=True)

# Delete Records
@route53.command()
@click.argument('zone_id')
@click.argument('subdomain')
@click.argument('ip_address')
def delete_record(zone_id, subdomain, ip_address):
    """Delete a record from a zone."""
    client = get_route53_client()

    try:
        tags_resp = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)
        tags = {t['Key']: t['Value'] for t in tags_resp['ResourceTagSet']['Tags']}
        
        if tags.get('CreatedBy') != TAG_CREATED_BY:
            click.echo(f"❌ Error: Zone {zone_id} is not managed by platform-cli!", err=True)
            return
    except Exception as e:
        click.echo(f"Permission error: {e}", err=True)
        return

    try:
        zone_info = client.get_hosted_zone(Id=zone_id)
        zone_name = zone_info['HostedZone']['Name']
        full_record_name = f"{subdomain}.{zone_name}"
    except Exception as e:
        click.echo(f"Error fetching zone: {e}", err=True)
        return

    click.echo(f"🗑️ Deleting record {full_record_name} -> {ip_address}...")


    try:
        change_batch = {
            'Changes': [{
                'Action': 'DELETE',
                'ResourceRecordSet': {
                    'Name': full_record_name,
                    'Type': 'A',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': ip_address}]
                }
            }]
        }
        client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)
        click.echo("✅ Record deleted.")
    except Exception as e:
        click.echo(f"AWS Error: {e}", err=True)