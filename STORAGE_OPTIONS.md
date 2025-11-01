# Storage Opties voor Photo Match op AWS

## Probleem: File Uploads in Docker

Docker containers zijn **ephemeral** (tijdelijk). Zonder persistente opslag:
```
Upload foto → Container restart → Foto's WEG! 💥
```

## 3 Oplossingen:

---

## Optie 1: Lokale Docker Volume (Simpelst voor EC2/Lightsail)

### Voor EC2 of Lightsail:

**docker-compose.yml** (al geconfigureerd):
```yaml
volumes:
  - ./uploads:/app/uploads  # Host folder → Container folder
```

**Voordelen**:
- ✅ Simpel
- ✅ Geen extra kosten
- ✅ Snel

**Nadelen**:
- ❌ Alleen 1 server (niet schaalbaar)
- ❌ Bij server crash → data weg (tenzij backup)

**Gebruik voor**: Development, kleine apps, Lightsail

---

## Optie 2: AWS EFS (Elastic File System) voor ECS Fargate

EFS is een gedeelde file storage die meerdere containers kunnen gebruiken.

### Setup:

1. **Create EFS**:
```bash
aws efs create-file-system \
  --performance-mode generalPurpose \
  --throughput-mode bursting \
  --encrypted \
  --tags Key=Name,Value=photo-match-uploads
```

2. **Create Mount Targets** (in je VPC subnets)

3. **Security Group**: Allow NFS (port 2049) from ECS tasks

4. **Update Task Definition**: Gebruik `ecs-task-definition.json`

### EFS Setup via Console:

1. EFS Console → Create file system
2. Name: `photo-match-uploads`
3. VPC: Same as ECS cluster
4. Create mount targets in alle availability zones
5. Security group: Allow NFS from ECS security group

6. In ECS Task Definition:
   - Add volume: Type = EFS
   - File system ID: <your-efs-id>
   - Container mount point: `/app/uploads`

**Voordelen**:
- ✅ Schaalbaar (meerdere containers)
- ✅ Persistent
- ✅ Automatische backups mogelijk

**Nadelen**:
- ❌ Extra kosten (~$0.30/GB/maand)
- ❌ Complexer

**Kosten**: ~$1-5/maand (voor kleine app)

---

## Optie 3: AWS S3 (Aanbevolen voor Production!)

Upload foto's direct naar S3 bucket in plaats van lokale opslag.

### Setup:

1. **Create S3 Bucket**:
```bash
aws s3 mb s3://photo-match-uploads-<unique-id> --region eu-west-1
```

2. **Update requirements.txt**:
```txt
boto3==1.28.0
```

3. **Gebruik main_s3.py** in plaats van main.py:
```bash
# In Dockerfile wijzig:
COPY main_s3.py main.py
```

4. **Environment variables** voor ECS Task:
```json
"environment": [
  {
    "name": "USE_S3",
    "value": "true"
  },
  {
    "name": "S3_BUCKET",
    "value": "photo-match-uploads-<unique-id>"
  },
  {
    "name": "AWS_REGION",
    "value": "eu-west-1"
  }
]
```

5. **IAM Role** voor ECS Task:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::photo-match-uploads-*",
        "arn:aws:s3:::photo-match-uploads-*/*"
      ]
    }
  ]
}
```

**Voordelen**:
- ✅ Zeer schaalbaar
- ✅ Geen volume management
- ✅ Goedkoop voor kleine files
- ✅ Built-in versioning & lifecycle
- ✅ CDN integratie mogelijk (CloudFront)

**Nadelen**:
- ❌ Code wijziging nodig
- ❌ Iets langzamer dan lokaal

**Kosten**: $0.023/GB/maand + requests (~$0.50/maand voor kleine app)

---

## Vergelijking:

| Optie | Schaalbaar | Kosten/maand | Complexiteit | Use Case |
|-------|------------|--------------|--------------|----------|
| **Local Volume** | ❌ | $0 | Laag | EC2, Lightsail, Dev |
| **EFS** | ✅ | $1-5 | Medium | ECS multi-container |
| **S3** | ✅✅ | $0.50 | Medium | Production, beste keuze |

---

## Aanbeveling per AWS Service:

### Lightsail ($3.50/maand):
```bash
# Gebruik docker-compose.yml met local volume
docker-compose up -d
```
✅ Local volume is perfect

### EC2 ($8/maand):
```bash
# Gebruik docker-compose.yml met local volume
docker-compose up -d
```
✅ Local volume is prima

### ECS Fargate ($15/maand):
**Keuze A: S3** (aanbevolen)
```bash
# Gebruik main_s3.py
# Set USE_S3=true
```

**Keuze B: EFS**
```bash
# Gebruik ecs-task-definition.json
# Create EFS first
```

---

## Quick Start: S3 Deployment

### 1. Update Dockerfile:

```dockerfile
# Wijzig deze regel:
COPY main_s3.py main.py

# En voeg boto3 toe aan requirements:
RUN pip install boto3
```

### 2. Build en Push:

```bash
docker build -t photo-match .
docker tag photo-match <ACCOUNT>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest
docker push <ACCOUNT>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest
```

### 3. Create S3 Bucket:

```bash
aws s3 mb s3://photo-match-uploads-$(date +%s)
```

### 4. ECS Task met env vars:

```json
"environment": [
  {"name": "USE_S3", "value": "true"},
  {"name": "S3_BUCKET", "value": "photo-match-uploads-XXXXX"}
]
```

### 5. Deploy!

Geen volumes nodig, alles gaat naar S3! 🎉

---

## Test Lokaal met S3:

```bash
# Set environment variables
export USE_S3=true
export S3_BUCKET=photo-match-uploads-test
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>

# Run locally
python main_s3.py
```
