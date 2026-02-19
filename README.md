# ☁️ AWS Self-Service Platform (CLI & UI)

**Internal Developer Platform (IDP)** for automated and secure AWS resource management.

This project implements **Platform Engineering** concepts: it provides developers with a convenient interface (CLI and Web UI) to work with the cloud, abstracting away AWS API complexity while enforcing automatic **Guardrails** and tagging standards.

---

## ⚡ Key Features

### 🖥️ EC2 (Virtual Machines)
* **Smart Provisioning:** Automatically retrieves the latest Amazon Linux 2 AMI via AWS Systems Manager (SSM).
* **Guardrails:** Restricts usage to cost-effective instance types only (`t3.micro`, `t3.small`).
* **Security:** Prevents accidental deletion of other users' servers via ownership tag verification.

### 🌐 Route53 (DNS)
* **Automation:** Automatically constructs FQDNs (e.g., input `app` becomes `app.project.com.`).
* **Isolation:** Zone filtering — users only see and manage zones created via this tool.
* **Idempotency:** Uses `UPSERT` actions for safe record updates.
* **CRUD:** Full lifecycle management (Create zones, Add/Delete records).

### 🗄️ S3 (Storage)
* **Rapid bucket creation** with mandatory automatic tagging.
* **Streamed file uploads** via Web UI (files are uploaded directly to AWS without saving to local disk).

---

## 🛠️ Tech Stack

* **Python 3.8+** — Core logic and automation.
* **Boto3** — AWS SDK for cloud interaction.
* **Click** — Framework for building the CLI.
* **Streamlit** — Framework for the Self-Service Web Portal.
* **Python-Dotenv** — Configuration and secrets management.

## 📋 Prerequisites

1. **Python 3.8** or higher installed.
2. **AWS Account**.
3. **Access Keys** (Access Key ID & Secret Access Key).

---

## 🚀 Installation & Setup

### 1. Clone the repository
```bash
git clone [https://github.com/eduardbnd/Platform-CLI.git](https://github.com/eduardbnd/Platform-CLI.git)
cd platform-cli
```

### 2. Create Virtual Environment
Isolate project dependencies:

**Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Secrets (.env)**

Create a `.env` file in the project root.

> **Important:** This file contains secrets and is added to `.gitignore`, so it will not be pushed to the repository.

Add the following credentials:

```ini
# AWS Credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=your_region

# Tagging Governance
TAG_CREATED_BY=your_value
TAG_OWNER=your_value

# Tagging Governance
4. TAG_CREATED_BY=your_value
5. TAG_OWNER=your_value
```

## 💻 Usage (CLI)

Command Line Interface for engineers and automation scripts.

### 🖥️ Server Management (EC2)

**Create server**
```bash
python main.py ec2 create --name <server_name> --key <your_key> --type <t3.micro or t3.small>
```

**List instances**
```bash
python main.py ec2 list
```

**Stop server**
```bash
python main.py ec2 stop <INSTANCE_ID>
```
**Start server**
```bash
python main.py ec2 start <INSTANCE_ID>
```

**Terminate server**
```bash
python main.py ec2 terminate <INSTANCE_ID>
```

### 🌐 DNS Management (Route53)


**1. Create Hosted Zone**
```bash
python main.py route53 create-zone <name of your zone>
```

**2. Add Record**
```bash
python main.py route53 add-record <ZONE_ID> <name of your record> <ip(ex. 1.1.1.1)>
```

**3. Delete Record**
```bash
python main.py route53 delete-record <ZONE_ID> <name of your record> <ip(ex. 1.1.1.1)>
```

### 🗄️ File Management (S3)

**Create bucket**
```bash
python main.py s3 create-bucket <bucket_name>
```

**Upload file**
```bash
python main.py s3 upload <bucket_name> ./<your_file>
```

## 🌐 Usage (Web UI)

Self-Service Portal for developers.

**Run the application:**

1. Execute the following command in your terminal:
```bash
streamlit run app.py
```

2. Open your browser at: `http://localhost:8501`
3. Use the sidebar menu to navigate between services.

---

## 🏷️ Tagging Policy (Governance)

All resources created via this platform are automatically tagged:

| Tag Key | Value | Description |
| :--- | :--- | :--- |
| `CreatedBy` | `.env value` | Allows the tool to filter resources and manage only its "own" objects. |
| `Owner` | `.env value` | Indicates the resource owner (for Cost Allocation). |

---

## 🧹 Cleanup Instructions

To avoid unexpected AWS charges, please clean up resources after testing:

1. **EC2:** Run `terminate` for all instances.
2. **S3:** Delete all objects, then delete the buckets.
3. **Route53:** Delete records, then delete the Hosted Zones.

---

**Author:** Eduard Bondarenko  
**Year:** 2026