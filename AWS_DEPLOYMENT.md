# 🚀 AWS EC2 Deployment Guide - FREE for 12 Months!

Deploy your Telegram Account Selling Bot on AWS EC2 **completely FREE** for the first year, then ~$8-10/month after.

---

## 💰 Cost Breakdown

**First 12 months:** **FREE** ✅
- 750 hours/month EC2 t2.micro (runs 24/7!)
- 30GB storage
- 15GB data transfer
- PostgreSQL RDS also free!

**After 12 months:** ~$8-10/month
- Can easily upgrade to bigger instance as your business grows

---

## 📋 Prerequisites

- AWS account ([sign up here](https://aws.amazon.com/free/))
- Your bot's API keys and tokens
- GitHub repository with your code

**Time needed:** 20-30 minutes for first-time setup

---

## Part 1: Create AWS EC2 Instance (Your Server)

### Step 1: Launch EC2 Instance

1. **Login to AWS Console** → Go to [console.aws.amazon.com](https://console.aws.amazon.com)
2. **Search for "EC2"** in the top search bar → Click **EC2**
3. Click orange **"Launch Instance"** button

### Step 2: Configure Your Instance

**Name:** `telegram-bot-server`

**Application and OS Images:**
- Choose **Ubuntu Server 22.04 LTS** (Free tier eligible)
- Make sure it says **"Free tier eligible"** ✅

**Instance Type:**
- Select **t2.micro** (1GB RAM, 1 vCPU) - Free tier eligible ✅

**Key Pair (Important!):**
- Click **"Create new key pair"**
- Name: `telegram-bot-key`
- Type: **RSA**
- Format: **.pem** (for Mac/Linux) or **.ppk** (for Windows PuTTY)
- Click **"Create key pair"** - it will download automatically
- **SAVE THIS FILE!** You'll need it to connect to your server

**Network Settings:**
- Click **"Edit"**
- Enable **"Allow SSH traffic from"** → Choose **"My IP"** (more secure)
- Enable **"Allow HTTPS traffic from the internet"**
- Enable **"Allow HTTP traffic from the internet"**

**Storage:**
- Keep default **8 GB** (you can increase to **30 GB** for free tier)

### Step 3: Launch!

1. Click **"Launch Instance"**
2. Wait 1-2 minutes for it to start
3. You'll see **"Success"** message

---

## Part 2: Connect to Your Server

### Step 1: Get Your Server IP

1. Go to **EC2 Dashboard** → Click **"Instances"**
2. Click on your **telegram-bot-server** instance
3. Copy the **"Public IPv4 address"** (example: `54.123.45.67`)

### Step 2: Connect via SSH

**On Mac/Linux:**
```bash
# Move your key file to safe location
mv ~/Downloads/telegram-bot-key.pem ~/.ssh/
chmod 400 ~/.ssh/telegram-bot-key.pem

# Connect to your server (replace with YOUR IP)
ssh -i ~/.ssh/telegram-bot-key.pem ubuntu@YOUR_SERVER_IP
```

**On Windows:**
- Use **PuTTY** or **Windows Terminal** with the .ppk key
- [Follow this guide](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/putty.html)

**First time connecting:**
- You'll see a security warning → Type **yes** and press Enter

---

## Part 3: Install Your Bot (One Command!)

Once connected to your server, run this automated setup:

```bash
# Download and run the automated setup script
curl -o setup_bot.sh https://raw.githubusercontent.com/YOUR_USERNAME/teleaccount-bot/main/setup_bot.sh
chmod +x setup_bot.sh
sudo ./setup_bot.sh
```

**The script will:**
✅ Install Python 3.11
✅ Install PostgreSQL database
✅ Install all bot dependencies
✅ Set up auto-start on reboot
✅ Configure firewall

**Time:** ~5-10 minutes

---

## Part 4: Configure Your Bot

### Step 1: Clone Your Repository

```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/teleaccount-bot.git
cd teleaccount-bot
```

### Step 2: Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

### Step 3: Set Environment Variables

Run the interactive configuration helper:

```bash
python3 aws_setup_helper.py
```

This will ask you for:
- Bot token from @BotFather
- API ID and API Hash from my.telegram.org
- Admin Telegram ID
- Secret key (auto-generated if you don't have one)

All values are saved securely in `/etc/telegram-bot/.env`

**OR manually create the file:**

```bash
sudo mkdir -p /etc/telegram-bot
sudo nano /etc/telegram-bot/.env
```

Add this content (replace with YOUR values):
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
API_ID=your_api_id
API_HASH=your_api_hash
ADMIN_TELEGRAM_ID=your_telegram_id
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://postgres:yourpassword@localhost/telegrambot
```

Save: **Ctrl+X** → **Y** → **Enter**

### Step 4: Set Up Database

```bash
# Create database
sudo -u postgres createdb telegrambot

# Initialize tables
python3 -c "from database import init_db; init_db()"
```

---

## Part 5: Start Your Bot as a Service

### Step 1: Create Systemd Service

```bash
sudo cp telebot.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Step 2: Start the Bot

```bash
# Start the bot
sudo systemctl start telebot

# Enable auto-start on reboot
sudo systemctl enable telebot

# Check status
sudo systemctl status telebot
```

You should see **"active (running)"** in green! ✅

### Step 3: View Logs

```bash
# Real-time logs
sudo journalctl -u telebot -f

# Recent logs
sudo journalctl -u telebot -n 50
```

---

## Part 6: Test Your Bot

1. Open Telegram
2. Search for your bot: `@YourBotUsername`
3. Send `/start`
4. Your bot should respond! 🎉

---

## 🔧 Managing Your Bot

### Restart Bot
```bash
sudo systemctl restart telebot
```

### Stop Bot
```bash
sudo systemctl stop telebot
```

### View Logs
```bash
sudo journalctl -u telebot -f
```

### Update Bot Code
```bash
cd /home/ubuntu/teleaccount-bot
git pull
sudo systemctl restart telebot
```

---

## 📊 Part 7: Optional - Set Up PostgreSQL RDS (Managed Database)

**If you want a separate managed database** (also free tier):

1. Go to **RDS** in AWS Console
2. Click **"Create database"**
3. Choose **PostgreSQL**
4. Select **Free tier** template
5. Set master password
6. Create database
7. Update `DATABASE_URL` in your `.env` file

**Benefits:** Automatic backups, easier scaling

---

## 💾 Backups

### Automated Daily Backups

```bash
# Create backup script
sudo nano /usr/local/bin/backup_bot.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump telegrambot > $BACKUP_DIR/db_$DATE.sql

# Keep only last 7 backups
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
```

Make executable and add to cron:
```bash
sudo chmod +x /usr/local/bin/backup_bot.sh
sudo crontab -e
```

Add this line (runs daily at 2 AM):
```
0 2 * * * /usr/local/bin/backup_bot.sh
```

---

## 🚀 Scaling Your Bot

### When You Outgrow Free Tier:

**Upgrade Instance Size:**
1. Stop your instance
2. Actions → Instance Settings → Change Instance Type
3. Choose **t2.small** ($17/month) or **t2.medium** ($34/month)
4. Start instance

**Add More Storage:**
1. Volumes → Select volume → Actions → Modify Volume
2. Increase size
3. Reboot instance

---

## ⚠️ Troubleshooting

### Bot not starting?
```bash
# Check logs for errors
sudo journalctl -u telebot -n 100

# Check if bot file exists
ls -la /home/ubuntu/teleaccount-bot/real_main.py

# Test bot manually
cd /home/ubuntu/teleaccount-bot
python3 real_main.py
```

### Database connection errors?
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -d telegrambot -c "SELECT 1;"
```

### Can't connect via SSH?
1. Check Security Group allows SSH from your IP
2. Verify you're using correct .pem key
3. Make sure instance is running

---

## 🔐 Security Best Practices

1. **Never share your .pem key file**
2. **Keep your Security Group restricted** - Only allow SSH from your IP
3. **Regularly update Ubuntu:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```
4. **Use strong passwords** for database
5. **Enable AWS MFA** (Multi-Factor Authentication)

---

## 💡 Pro Tips

**Keep Your Bot Running:**
- Systemd automatically restarts if it crashes
- Bot auto-starts on server reboot
- Logs are stored for debugging

**Monitor Your Usage:**
- AWS Console → Billing Dashboard
- Set up billing alerts (recommended!)
- Free tier shows remaining hours

**Save Money:**
- Use **Spot Instances** for non-critical tasks
- **Stop instance** when not needed (you only pay for running hours)
- Free tier is **always free** for 12 months!

---

## 📞 Need Help?

- **AWS Documentation:** [docs.aws.amazon.com](https://docs.aws.amazon.com)
- **AWS Free Tier FAQ:** [aws.amazon.com/free/faqs](https://aws.amazon.com/free/faqs/)
- **Check bot logs:** `sudo journalctl -u telebot -f`

---

## 🎉 Success!

Your Telegram bot is now:
- ✅ Running 24/7 on AWS
- ✅ FREE for 12 months
- ✅ Auto-starts on reboot
- ✅ Easy to scale as you grow
- ✅ Professional infrastructure

**Next steps:**
1. Test all bot features
2. Set up billing alerts
3. Monitor server performance
4. Enjoy your free hosting! 🚀

---

**Questions?** Check the troubleshooting section or AWS documentation!
