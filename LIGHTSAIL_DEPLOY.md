# AWS Lightsail Deployment - Complete Guide

## Wat is Lightsail?

**AWS Lightsail = VPS hosting met vaste prijzen**
- Simpeler dan EC2
- $3.50 - $5 /maand all-in
- Perfect voor kleine apps
- Geen verrassingen in je factuur

---

## Stap-voor-Stap Deployment

### Stap 1: Create Lightsail Instance (2 minuten)

1. **Ga naar AWS Lightsail Console**:
   - https://lightsail.aws.amazon.com/

2. **Create Instance**:
   - Click "Create instance"
   - Region: **Europe (Frankfurt)** of **Europe (Ireland)**
   - Platform: **Linux/Unix**
   - Blueprint: **OS Only** → **Ubuntu 22.04 LTS**

3. **Instance Plan**:
   - Kies: **$3.50/maand** (512MB, voor testing)
   - Of: **$5/maand** (1GB, aanbevolen voor productie)

4. **Name**: `photo-match`

5. **Click**: "Create instance"

⏱️ Instance is klaar in ~1 minuut

---

### Stap 2: Setup Static IP (gratis!)

1. **In Lightsail Console**:
   - Click op je instance "photo-match"
   - Tab: **Networking**
   - Click: "Create static IP"
   - Attach to: photo-match
   - Name: `photo-match-ip`
   - Click: "Create"

✅ Je hebt nu een vast IP adres (bijv. 18.195.123.45)

---

### Stap 3: Configure Firewall

1. **In instance networking tab**:
   - Firewall rules:
     - ✅ SSH (22) - Already there
     - ✅ HTTP (80) - Click "Add rule"
     - ✅ HTTPS (443) - Click "Add rule"

---

### Stap 4: SSH naar Instance

**Optie A: Via Browser (makkelijkst)**
```
1. Click op je instance
2. Click "Connect using SSH" button
3. Terminal opent in browser
```

**Optie B: Via Terminal**
```bash
# Download SSH key
# Lightsail Console → Account → SSH keys → Download

# SSH
ssh -i LightsailDefaultKey-eu-central-1.pem ubuntu@<YOUR-STATIC-IP>
```

---

### Stap 5: Install Docker

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Docker
sudo apt install docker.io docker-compose -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (no need for sudo)
sudo usermod -aG docker ubuntu

# Apply group change
newgrp docker

# Test
docker --version
docker-compose --version
```

**Output should be:**
```
Docker version 24.x.x
docker-compose version 1.29.x
```

---

### Stap 6: Upload Code

**Optie A: Git Clone (aanbevolen)**

```bash
# Als je code op GitHub staat:
git clone https://github.com/jouw-username/photo_match.git
cd photo_match
```

**Optie B: Upload Files**

```bash
# Op je lokale computer:
scp -i LightsailDefaultKey.pem -r /path/to/photo_match ubuntu@<YOUR-IP>:~/

# Dan op server:
cd photo_match
```

**Optie C: Manual Copy-Paste**

```bash
# Create directory
mkdir photo_match
cd photo_match

# Copy paste files via nano
nano Dockerfile
# Paste content, Ctrl+X, Y, Enter

nano docker-compose.yml
# Paste content, Ctrl+X, Y, Enter

# etc voor alle files
```

---

### Stap 7: Build en Start

```bash
cd photo_match

# Build Docker image
docker build -t photo-match .

# Start met docker-compose
docker-compose up -d

# Check of het draait
docker-compose ps
```

**Output:**
```
NAME                COMMAND                  STATUS              PORTS
photo-match-1       "uvicorn main:app ..." Up 2 minutes        0.0.0.0:80->80/tcp
```

✅ **App draait nu op http://<YOUR-STATIC-IP>**

---

### Stap 8: Setup Domain (optioneel)

**Als je een domein hebt (bijv. photomatch.nl):**

1. **Bij je domain provider** (Transip, Hostnet, etc):
   ```
   Type: A
   Name: @ (of www)
   Value: <YOUR-LIGHTSAIL-STATIC-IP>
   TTL: 300
   ```

2. **Wait 5-10 minuten** voor DNS propagation

3. **Test**:
   ```bash
   ping photomatch.nl
   # Should resolve to your IP
   ```

---

### Stap 9: Setup HTTPS/SSL (gratis met Let's Encrypt)

**Install Certbot:**

```bash
sudo apt install certbot python3-certbot-nginx -y
```

**Install Nginx:**

```bash
sudo apt install nginx -y
```

**Configure Nginx:**

```bash
sudo nano /etc/nginx/sites-available/photo-match
```

**Paste:**
```nginx
server {
    listen 80;
    server_name photomatch.nl www.photomatch.nl;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/photo-match /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**Get SSL Certificate:**
```bash
sudo certbot --nginx -d photomatch.nl -d www.photomatch.nl
```

**Follow prompts:**
```
Email: your@email.com
Terms: Yes (A)
Share email: No (N)
Redirect HTTP to HTTPS: Yes (2)
```

✅ **HTTPS is nu actief! Certificate renews automatically.**

🎉 **App draait nu op: https://photomatch.nl**

---

### Stap 10: Verify Everything Works

```bash
# Check Docker
docker-compose ps

# Check logs
docker-compose logs -f

# Check Nginx
sudo systemctl status nginx

# Test upload
# Open browser: https://photomatch.nl
# Upload een foto
# Check if it works!
```

---

## Maintenance & Updates

### View Logs:
```bash
cd photo_match
docker-compose logs -f
```

### Restart App:
```bash
docker-compose restart
```

### Update Code:
```bash
# Stop app
docker-compose down

# Pull new code
git pull

# Rebuild
docker build -t photo-match .

# Start
docker-compose up -d
```

### Check Disk Space:
```bash
df -h
```

### Backup (Snapshot):
```
1. Lightsail Console
2. Click instance
3. Snapshots tab
4. Create snapshot
5. Cost: ~$0.70/month
```

---

## Monitoring

### Check resource usage:
```bash
# CPU & Memory
htop

# Docker stats
docker stats
```

### Setup alerts:
```
1. Lightsail Console
2. Metrics tab
3. Create alarm (CPU > 80%, etc)
4. Get email alerts
```

---

## Troubleshooting

### App niet bereikbaar:
```bash
# Check firewall
# Lightsail Console → Networking → Verify ports 80, 443 open

# Check Docker
docker-compose ps

# Check logs
docker-compose logs
```

### Out of memory:
```bash
# Upgrade Lightsail plan
# Lightsail Console → Manage → Change plan → $5/month (1GB)
```

### SSL certificate issues:
```bash
# Renew manually
sudo certbot renew

# Check expiry
sudo certbot certificates
```

---

## Kosten Breakdown

| Item | Kosten |
|------|--------|
| Lightsail instance ($5/maand) | $5.00 |
| Static IP | $0 (gratis bij Lightsail) |
| SSL Certificate (Let's Encrypt) | $0 |
| Bandwidth (1TB) | $0 (included) |
| Snapshot backup (optioneel) | $0.70 |
| **TOTAAL** | **$5.00 - $5.70/maand** |

**Vergelijk met ECS Fargate:** $31+ /maand 😱

---

## Upgraden naar groter plan (later):

```
Lightsail Console
→ Click instance
→ Manage
→ Change plan
→ Select bigger plan
→ Instance wordt automatisch ge-resize (0 downtime!)
```

Plans:
- $5/maand → $10/maand (2GB RAM)
- $10/maand → $20/maand (4GB RAM)
- etc.

---

## Conclusie

✅ **Lightsail is perfect voor deze app:**
- 5 minuten setup
- $5/maand all-in
- Gratis HTTPS
- Simpel te onderhouden
- Kan later upgraden als nodig

🚀 **Je app draait nu in production op AWS!**
