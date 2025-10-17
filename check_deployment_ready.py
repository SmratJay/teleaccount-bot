#!/usr/bin/env python3
"""
HEROKU DEPLOYMENT VALIDATOR
Checks if all files are ready for Heroku deployment
"""

import os
import json

def check_file_exists(filename, required=True):
    """Check if a file exists."""
    exists = os.path.exists(filename)
    status = "✅" if exists else "❌"
    requirement = "REQUIRED" if required else "OPTIONAL"
    print(f"{status} {filename} - {requirement}")
    return exists

def check_env_template():
    """Check if .env.heroku has required variables."""
    if not os.path.exists('.env.heroku'):
        return False
    
    with open('.env.heroku', 'r') as f:
        content = f.read()
    
    required_vars = [
        'BOT_TOKEN', 'API_ID', 'API_HASH', 'TELEGRAM_API_ID', 
        'TELEGRAM_API_HASH', 'ADMIN_CHAT_ID', 'ADMIN_USER_ID'
    ]
    
    missing = []
    for var in required_vars:
        if var not in content:
            missing.append(var)
    
    if missing:
        print(f"❌ Missing variables in .env.heroku: {', '.join(missing)}")
        return False
    else:
        print("✅ .env.heroku contains all required variables")
        return True

def check_app_json():
    """Check if app.json is valid."""
    try:
        with open('app.json', 'r') as f:
            data = json.load(f)
        print("✅ app.json is valid JSON")
        
        if 'addons' in data:
            print("✅ PostgreSQL addon configured in app.json")
        else:
            print("❌ PostgreSQL addon missing in app.json")
            return False
        return True
    except Exception as e:
        print(f"❌ app.json error: {e}")
        return False

def main():
    print("🚀 HEROKU DEPLOYMENT READINESS CHECK")
    print("=" * 50)
    
    all_good = True
    
    # Check essential files
    print("\n📁 Essential Files:")
    essential_files = [
        'requirements.txt', 'Procfile', 'runtime.txt', 'app.json', 'real_main.py'
    ]
    
    for file in essential_files:
        if not check_file_exists(file):
            all_good = False
    
    # Check deployment files
    print("\n📋 Deployment Files:")
    deployment_files = [
        '.env.heroku', 'deploy_heroku.sh', 'deploy_heroku.ps1', 
        'HEROKU_DEPLOYMENT_GUIDE.md'
    ]
    
    for file in deployment_files:
        check_file_exists(file, required=False)
    
    # Check configurations
    print("\n⚙️ Configuration Check:")
    if not check_env_template():
        all_good = False
    
    if not check_app_json():
        all_good = False
    
    # Check database config
    try:
        from database import DATABASE_URL
        if 'postgresql' in DATABASE_URL or 'sqlite' in DATABASE_URL:
            print("✅ Database configuration looks good")
        else:
            print("❌ Database configuration issue")
            all_good = False
    except Exception as e:
        print(f"❌ Database import error: {e}")
        all_good = False
    
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 ALL CHECKS PASSED! Ready for Heroku deployment!")
        print("\n🚀 Next steps:")
        print("1. Run: ./deploy_heroku.ps1 (Windows) or ./deploy_heroku.sh (Linux/Mac)")
        print("2. Or manually deploy with git commands")
        print("3. Set your bot tokens in Heroku config vars")
        print("4. Test your bot!")
    else:
        print("❌ Some issues found. Please fix them before deploying.")
    
    return all_good

if __name__ == "__main__":
    main()