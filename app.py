import streamlit as st
import boto3
import os
from dotenv import load_dotenv

# 1. Load configuration
load_dotenv()

TAG_CREATED_BY = os.getenv('TAG_CREATED_BY', 'platform-cli')
TAG_OWNER = os.getenv('TAG_OWNER', 'student')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')

# --- HELPERS
def get_client(service):
    return boto3.client(
        service,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=AWS_REGION
    )

def get_latest_ami():
    """Retrieves the ID of the latest Amazon Linux 2 via SSM."""
    ssm = get_client('ssm')
    path = '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
    return ssm.get_parameter(Name=path)['Parameter']['Value']

# --- PAGE CONFIG ---
st.set_page_config(page_title="Platform CLI UI", page_icon="☁️", layout="wide")
st.title("☁️ AWS Self-Service Portal")
st.markdown(f"**User:** {TAG_OWNER} | **Region:** {AWS_REGION}")

# Sidebar Menu
menu = st.sidebar.selectbox("Select Service", ["EC2 (Servers)", "S3 (Storage)", "Route53 (DNS)"])

# ==========================
# 🖥️ EC2 SECTION
# ==========================
if menu == "EC2 (Servers)":
    st.header("🖥️ Virtual Machines (EC2)")
    ec2 = get_client('ec2')

    # --- LAUNCH FORM ---
    with st.expander("➕ Launch New Instance"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Server Name", value="web-server")
            key_name = st.text_input("SSH Key Name", value="edik")
        with col2:
            instance_type = st.selectbox("Type", ["t3.micro", "t3.small"])
            st.info("AMI will be retrieved automatically from SSM")

        if st.button("Launch Instance"):
            with st.spinner("Finding AMI and launching..."):
                try:
                    ami_id = get_latest_ami()
                    ec2.run_instances(
                        ImageId=ami_id,
                        InstanceType=instance_type,
                        KeyName=key_name,
                        MinCount=1, MaxCount=1,
                        TagSpecifications=[{
                            'ResourceType': 'instance',
                            'Tags': [
                                {'Key': 'Name', 'Value': name},
                                {'Key': 'CreatedBy', 'Value': TAG_CREATED_BY},
                                {'Key': 'Owner', 'Value': TAG_OWNER}
                            ]
                        }]
                    )
                    st.success(f"Instance '{name}' is launching!")
                    st.rerun() # Refresh page
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- INSTANCE LIST ---
    st.subheader("My Active Instances")
    try:
        response = ec2.describe_instances(
            Filters=[{'Name': 'tag:CreatedBy', 'Values': [TAG_CREATED_BY]}]
        )
        
        data = []
        for r in response['Reservations']:
            for i in r['Instances']:
                if i['State']['Name'] == 'terminated': continue
                
                tags = {t['Key']: t['Value'] for t in i.get('Tags', [])}
                data.append({
                    "ID": i['InstanceId'],
                    "Name": tags.get('Name', 'Unknown'),
                    "State": i['State']['Name'],
                    "Type": i['InstanceType'],
                    "IP": i.get('PublicIpAddress', 'No IP')
                })

        if data:
            st.dataframe(data, use_container_width=True)
            
            # Management Controls
            selected_id = st.selectbox("Select ID to manage", [d['ID'] for d in data])
            c1, c2, c3 = st.columns(3)
            if c1.button("▶️ Start"):
                ec2.start_instances(InstanceIds=[selected_id])
                st.toast(f"Starting {selected_id}...")
            if c2.button("tj Stop"):
                ec2.stop_instances(InstanceIds=[selected_id])
                st.toast(f"Stopping {selected_id}...")
            if c3.button("🗑️ Terminate"):
                ec2.terminate_instances(InstanceIds=[selected_id])
                st.warning(f"Instance {selected_id} is being terminated.")
                st.rerun()
        else:
            st.info("No active instances found.")
            
    except Exception as e:
        st.error(f"Error loading list: {e}")

# ==========================
# 🗄️ S3 SECTION
# ==========================
elif menu == "S3 (Storage)":
    st.header("🗄️ File Storage (S3)")
    s3 = get_client('s3')

    # --- CREATE BUCKET ---
    with st.expander("➕ Create Bucket"):
        b_name = st.text_input("Bucket Name (lowercase only!)")
        is_public = st.checkbox("Make Public? (Dangerous)")
        
        if is_public:
            st.warning("⚠️ Warning! Files will be accessible to the whole internet.")
            confirm = st.checkbox("I understand the risks")
        else:
            confirm = True

        if st.button("Create Bucket"):
            if not b_name:
                st.error("Enter a name!")
            elif not confirm:
                st.error("Confirm public bucket creation.")
            else:
                try:
                    # Create
                    if AWS_REGION == 'us-east-1':
                        s3.create_bucket(Bucket=b_name)
                    else:
                        s3.create_bucket(Bucket=b_name, CreateBucketConfiguration={'LocationConstraint': AWS_REGION})
                    
                    # Tags
                    s3.put_bucket_tagging(
                        Bucket=b_name,
                        Tagging={'TagSet': [{'Key': 'CreatedBy', 'Value': TAG_CREATED_BY}, {'Key': 'Owner', 'Value': TAG_OWNER}]}
                    )
                    
                    # Permissions
                    if is_public:
                        s3.delete_public_access_block(Bucket=b_name)
                    else:
                        s3.put_public_access_block(Bucket=b_name, PublicAccessBlockConfiguration={'BlockPublicAcls': True, 'IgnorePublicAcls': True, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': True})
                        
                    st.success(f"Bucket {b_name} created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- BUCKET LIST ---
    st.subheader("My Buckets")
    try:
        resp = s3.list_buckets()
        my_buckets = []
        for b in resp['Buckets']:
            try:
                tags = s3.get_bucket_tagging(Bucket=b['Name'])
                tag_dict = {t['Key']: t['Value'] for t in tags['TagSet']}
                if tag_dict.get('CreatedBy') == TAG_CREATED_BY:
                    my_buckets.append(b['Name'])
            except:
                continue
        
        if my_buckets:
            selected_bucket = st.selectbox("Select bucket to manage", my_buckets)
            
            # UPLOAD FILE
            uploaded_file = st.file_uploader("Upload file")
            if uploaded_file and st.button("Upload"):
                s3.upload_fileobj(uploaded_file, selected_bucket, uploaded_file.name)
                st.success("File uploaded!")
                
        else:
            st.info("No buckets found.")
            
    except Exception as e:
        st.error(f"Error: {e}")

# ==========================
# 🌐 ROUTE53 SECTION
# ==========================
elif menu == "Route53 (DNS)":
    st.header("🌐 DNS Management (Route53)")
    r53 = get_client('route53')
    
    # --- CREATE ZONE ---
    with st.expander("➕ Create Hosted Zone"):
        domain = st.text_input("Domain (e.g., project.com)")
        if st.button("Create Zone"):
            import time
            ref = f"{domain}-{int(time.time())}"
            try:
                res = r53.create_hosted_zone(Name=domain, CallerReference=ref)
                zid = res.get('HostedZone', {}).get('Id', '').split('/')[-1]
                
                if zid:
                    r53.change_tags_for_resource(
                        ResourceType='hostedzone', ResourceId=zid,
                        AddTags=[{'Key': 'CreatedBy', 'Value': TAG_CREATED_BY}, {'Key': 'Owner', 'Value': TAG_OWNER}]
                    )
                    st.success(f"Zone {domain} created!")
                    st.rerun()
                else:
                    st.error("Zone created but no ID returned.")
            except Exception as e:
                st.error(f"Error: {e}")

    # --- ZONE LIST ---
    st.subheader("My Zones")
    try:
        zones_resp = r53.list_hosted_zones()
        my_zones = {}
        table_data = []
        
        all_zones = zones_resp.get('HostedZones', [])
        
        for z in all_zones:
            zid = z['Id'].split('/')[-1]
            z_name = z['Name']
            try:
                t_resp = r53.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zid)
                tags = {t['Key']: t['Value'] for t in t_resp['ResourceTagSet']['Tags']}
                
                if tags.get('CreatedBy') == TAG_CREATED_BY:
                    my_zones[z_name] = zid
                    table_data.append({
                        "Domain": z_name, 
                        "ID": zid, 
                        "Records": z.get('ResourceRecordSetCount', 0)
                    })
            except:
                continue
        
        if table_data:
            st.table(table_data)
            
            st.divider()
            
            # --- MANAGE RECORDS ---
            st.write("🛠️ **Manage Records**")
            target_zone_name = st.selectbox("Select Zone", list(my_zones.keys()))
            target_zone_id = my_zones[target_zone_name]

            # --- ADD RECORD ---
            st.write("📝 **Add A-Record**")
            c1, c2, c3 = st.columns([2, 2, 1])
            sub = c1.text_input("Subdomain", value="www", help="e.g. 'app'")
            ip = c2.text_input("IP Address", value="1.2.3.4")
            
            if c3.button("Add Record"):
                full_name = f"{sub}.{target_zone_name}"
                try:
                    r53.change_resource_record_sets(
                        HostedZoneId=target_zone_id,
                        ChangeBatch={
                            'Changes': [{
                                'Action': 'UPSERT',
                                'ResourceRecordSet': {
                                    'Name': full_name, 'Type': 'A', 'TTL': 300,
                                    'ResourceRecords': [{'Value': ip}]
                                }
                            }]
                        }
                    )
                    st.success(f"Added {full_name} -> {ip}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

            st.divider()

            # --- DELETE RECORD LIST ---
            st.write("📋 **Existing A-Records (Delete)**")
            
            try:
                rr_resp = r53.list_resource_record_sets(HostedZoneId=target_zone_id)
                records = rr_resp.get('ResourceRecordSets', [])
                a_records = [r for r in records if r['Type'] == 'A']

                if a_records:
                    for rec in a_records:
                        r_name = rec['Name']
                        r_val = rec['ResourceRecords'][0]['Value']
                        r_ttl = rec.get('TTL', 300)

                        rc1, rc2, rc3 = st.columns([3, 2, 1])
                        rc1.text(r_name)
                        rc2.text(r_val)
                        
                        if rc3.button("🗑️ Delete", key=r_name):
                            try:
                                r53.change_resource_record_sets(
                                    HostedZoneId=target_zone_id,
                                    ChangeBatch={
                                        'Changes': [{
                                            'Action': 'DELETE',
                                            'ResourceRecordSet': {
                                                'Name': r_name,
                                                'Type': 'A',
                                                'TTL': r_ttl,
                                                'ResourceRecords': [{'Value': r_val}]
                                            }
                                        }]
                                    }
                                )
                                st.warning(f"Deleted {r_name}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error deleting: {e}")
                else:
                    st.info("No A-records found in this zone.")

            except Exception as e:
                st.error(f"Error fetching records: {e}")

        else:
            st.info("No zones found (checked tags).")
            
    except Exception as e:
        st.error(f"Error loading zones: {e}")