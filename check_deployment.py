#!/usr/bin/env python3
"""
Pre-deployment verification script
Checks if all files and configurations are ready for cloud deployment
"""

import os
import sys
from pathlib import Path

def check_deployment_readiness():
    """Check if the bot is ready for cloud deployment."""
    
    print("🔍 DEPLOYMENT READINESS CHECK")
    print("=" * 50)
    
    issues = []
    successes = []
    
    # Check required files
    required_files = [
        'real_main.py',
        'requirements.txt', 
        'Procfile',
        'runtime.txt',
        '.replit',
        'replit.nix',
        'app.json',
        'DEPLOYMENT_GUIDE.md'
    ]
    
    print("\n📁 Required Files Check:")
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
            successes.append(f"File {file} exists")
        else:
            print(f"❌ {file} - MISSING")
            issues.append(f"Missing file: {file}")
    
    # Check environment variables in .env
    print("\n🔐 Environment Variables Check:")
    if os.path.exists('.env'):
        print("✅ .env file exists")
        
        # Read and check key variables
        with open('.env', 'r') as f:
            env_content = f.read()
            
        required_vars = [
            'BOT_TOKEN',
            'API_ID', 
            'API_HASH',
            'ADMIN_CHAT_ID',
            'LEADER_CHANNEL_ID'
        ]
        
        for var in required_vars:
            if var in env_content and not f'{var}=your_' in env_content:
                print(f"✅ {var} configured")
                successes.append(f"Environment variable {var} set")
            else:
                print(f"⚠️  {var} needs configuration")
                issues.append(f"Environment variable {var} needs proper value")
    else:
        print("⚠️  .env file not found (OK for cloud deployment)")
    
    # Check main application
    print("\n🤖 Application Check:")
    if os.path.exists('real_main.py'):
        try:
            # Try importing the main module
            sys.path.insert(0, '.')
            
            # Check if key modules can be imported
            try:
                from database import get_db_session
                print("✅ Database module can be imported")
                successes.append("Database module accessible")
            except Exception as e:
                print(f"⚠️  Database import issue: {e}")
                issues.append(f"Database import problem: {e}")
            
            try:
                from handlers.main_handlers import setup_main_handlers
                print("✅ Main handlers can be imported")
                successes.append("Main handlers accessible")
            except Exception as e:
                print(f"⚠️  Handlers import issue: {e}")
                issues.append(f"Handlers import problem: {e}")
                
        except Exception as e:
            print(f"❌ Application import failed: {e}")
            issues.append(f"Main application import error: {e}")
    
    # Check directory structure
    print("\n📂 Directory Structure Check:")
    required_dirs = ['database', 'handlers', 'services', 'utils', 'webapp']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/ directory")
            successes.append(f"Directory {dir_name} exists")
        else:
            print(f"⚠️  {dir_name}/ directory missing")
            issues.append(f"Missing directory: {dir_name}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT SUMMARY")
    print("=" * 50)
    
    print(f"✅ Successes: {len(successes)}")
    print(f"⚠️  Issues: {len(issues)}")
    
    if issues:
        print("\n❌ ISSUES TO FIX:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    
    if len(issues) == 0:
        print("\n🎉 READY FOR DEPLOYMENT!")
        print("✅ All checks passed!")
        print("\n🚀 Next Steps:")
        print("1. Create GitHub repository")
        print("2. Push your code to GitHub")
        print("3. Deploy to Replit or Heroku")
        print("4. Set environment variables on hosting platform")
        print("5. Test your bot!")
        
        return True
    else:
        print(f"\n🔧 FIX {len(issues)} ISSUE(S) BEFORE DEPLOYMENT")
        return False

if __name__ == "__main__":
    check_deployment_readiness()