"""
Clean up syntax errors from the previous fix
"""

def fix_syntax_errors():
    """Fix any broken strings or syntax errors."""
    
    with open('handlers/real_handlers.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix any broken f-strings or multi-line strings that got mangled
    fixes = [
        # Fix broken multiline strings in error messages
        (r'await update\.message\.reply_text\(f"❌ Withdrawal Error: \{str\(e\)\}[^"]*\n[^"]*Please try again or contact support\."\)', 
         'await update.message.reply_text(f"❌ Withdrawal Error: {str(e)}\\n\\nPlease try again or contact support.")'),
        
        # Fix any other broken multiline strings
        (r'"❌ \*\*Invalid Format!\*\*[^"]*\n[^"]*Please include country code: `\+1234567890`"',
         '"❌ **Invalid Format!**\\n\\nPlease include country code: `+1234567890`"'),
    ]
    
    for pattern, replacement in fixes:
        import re
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Write the fixed content
    with open('handlers/real_handlers.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Fixed syntax errors!")

if __name__ == "__main__":
    fix_syntax_errors()