# AWS Deployment Guide - Photo Match App

Deze guide helpt je de Photo Match applicatie te deployen op AWS met HTTPS support.

## Optie 1: AWS ECS (Elastic Container Service) - Aanbevolen

### Stap 1: Build en Push Docker Image naar ECR

```bash
# 1. Installeer AWS CLI (als je dat nog niet hebt)
# macOS: brew install awscli
# Of download van: https://aws.amazon.com/cli/

# 2. Configureer AWS credentials
aws configure

# 3. Login naar ECR
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com

# 4. Create ECR repository
aws ecr create-repository --repository-name photo-match --region eu-west-1

# 5. Build Docker image
docker build -t photo-match .

# 6. Tag image voor ECR
docker tag photo-match:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest

# 7. Push naar ECR
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest
```

### Stap 2: ECS Cluster Setup via AWS Console

1. **Ga naar ECS Console**: https://console.aws.amazon.com/ecs/
2. **Create Cluster**:
   - Cluster name: `photo-match-cluster`
   - Infrastructure: AWS Fargate (serverless)
   - Click "Create"

### Stap 3: Task Definition

1. **Create Task Definition**:
   - Family: `photo-match-task`
   - Launch type: Fargate
   - Operating system: Linux
   - CPU: 0.5 vCPU
   - Memory: 1 GB

2. **Container Definition**:
   - Container name: `photo-match`
   - Image URI: `<YOUR_AWS_ACCOUNT_ID>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest`
   - Port mappings: 80 (TCP)
   - Environment variables (optional):
     - Name: `PORT`, Value: `80`

3. **Storage** (voor uploads):
   - Add volume voor persistent storage als je dat wilt

4. Click "Create"

### Stap 4: Application Load Balancer Setup

1. **Create ALB**:
   - Go to EC2 > Load Balancers
   - Create Application Load Balancer
   - Name: `photo-match-alb`
   - Scheme: Internet-facing
   - IP address type: IPv4
   - VPC: Default VPC
   - Mappings: Select minimaal 2 availability zones

2. **Security Groups**:
   - Create new security group:
     - Allow HTTP (80) from 0.0.0.0/0
     - Allow HTTPS (443) from 0.0.0.0/0

3. **Target Group**:
   - Target type: IP addresses
   - Protocol: HTTP
   - Port: 80
   - Health check path: `/api/photo` (of `/`)
   - VPC: Same as ALB

4. **SSL Certificate (voor HTTPS)**:
   - In ALB Listeners, add listener for HTTPS (443)
   - Request certificate via AWS Certificate Manager (ACM)
   - Add your domain name
   - Validate via DNS or Email
   - Attach certificate to HTTPS listener

### Stap 5: Create ECS Service

1. **Go to ECS Cluster**
2. **Create Service**:
   - Launch type: Fargate
   - Task Definition: `photo-match-task:latest`
   - Service name: `photo-match-service`
   - Number of tasks: 1 (of meer voor high availability)

3. **Load Balancer**:
   - Type: Application Load Balancer
   - Select your ALB
   - Container to load balance: photo-match:80
   - Target group: Select created target group

4. **Auto Scaling** (optioneel):
   - Min tasks: 1
   - Max tasks: 3
   - Target CPU utilization: 70%

5. Click "Create Service"

### Stap 6: DNS Setup

1. **Get ALB DNS name** from Load Balancer console
2. **Create DNS Record** in your domain provider:
   - Type: CNAME
   - Name: photo-match (or www, or @)
   - Value: <ALB-DNS-NAME>
   - TTL: 300

### Stap 7: Verify Deployment

1. Wait 5-10 minutes voor deployment
2. Check ECS Service tasks status (should be RUNNING)
3. Check Target Group health (should be healthy)
4. Access via: `https://your-domain.com`

---

## Optie 2: AWS EC2 (Simpeler maar minder schaalbaar)

### Stap 1: Launch EC2 Instance

```bash
# 1. Launch EC2 Instance via AWS Console
# - AMI: Amazon Linux 2023
# - Instance type: t2.micro (of t3.micro)
# - Security Group: Allow HTTP (80), HTTPS (443), SSH (22)
```

### Stap 2: SSH naar Instance & Setup

```bash
# SSH naar instance
ssh -i your-key.pem ec2-user@<EC2-PUBLIC-IP>

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Relogin to apply docker group
exit
# SSH again

# Clone repository (of upload files)
git clone <YOUR-REPO> photo_match
cd photo_match

# Build en start
docker-compose up -d
```

### Stap 3: Setup HTTPS met Let's Encrypt

```bash
# Install certbot
sudo yum install certbot python3-certbot-nginx -y

# Install Nginx
sudo yum install nginx -y

# Configure Nginx as reverse proxy
sudo nano /etc/nginx/conf.d/photo-match.conf
```

Voeg toe:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Get SSL Certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is setup automatisch
```

---

## Optie 3: AWS Lightsail (Meest simpel en goedkoop)

1. **Create Lightsail Instance**:
   - OS: Amazon Linux 2023
   - Plan: $5/month (of $3.50/month)
   - Enable static IP

2. **SSH en Setup** (zelfde als EC2 hierboven)

3. **Attach Static IP** in Lightsail console

4. **Setup DNS** pointing naar Static IP

---

## Cost Vergelijking (ca.)

| Service | Kosten per maand |
|---------|------------------|
| **ECS Fargate** (1 task, 0.5 vCPU, 1GB) | ~$15-20 |
| **EC2 t2.micro** | ~$8-10 |
| **Lightsail** | $3.50-5 |
| **ALB** | ~$16 + data |
| **ECR** | Eerste 500MB gratis |

**Aanbeveling**:
- **Lightsail** voor simpele deployment en lage kosten
- **ECS Fargate** voor productie met auto-scaling
- **EC2** als middle ground

---

## Monitoring & Logging

### CloudWatch Logs (voor ECS)
```bash
# Logs worden automatisch naar CloudWatch gestuurd
# Check in CloudWatch Console > Log groups
```

### Docker Logs (voor EC2/Lightsail)
```bash
# Check container logs
docker-compose logs -f

# Check alleen app logs
docker-compose logs -f photo-match
```

---

## Troubleshooting

### ECS Task blijft crashen
```bash
# Check CloudWatch logs
# Check Task Definition environment variables
# Verify ECR image is correct
```

### 502 Bad Gateway
```bash
# Check Target Group health
# Verify container is running on port 80
# Check Security Groups allow ALB -> Container traffic
```

### HTTPS niet werkend
```bash
# Verify ACM certificate is issued
# Check ALB listener has HTTPS (443) configured
# Verify DNS points to ALB
```

---

## Updates Deployen

### ECS Fargate
```bash
# 1. Build nieuwe image
docker build -t photo-match .

# 2. Tag en push
docker tag photo-match:latest <ACCOUNT>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest
docker push <ACCOUNT>.dkr.ecr.eu-west-1.amazonaws.com/photo-match:latest

# 3. Update ECS Service (via console of CLI)
aws ecs update-service --cluster photo-match-cluster --service photo-match-service --force-new-deployment
```

### EC2/Lightsail
```bash
# SSH naar server
cd photo_match
git pull  # of upload nieuwe files
docker-compose down
docker-compose build
docker-compose up -d
```
