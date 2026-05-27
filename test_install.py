#!/usr/bin/env python3
"""
Test script for Simple Signal CLI
Verifies installation and basic functionality
"""

import sys
import os

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    checks = [
        ("transformers", "Transformers library"),
        ("torch", "PyTorch"),
    ]
    
    all_ok = True
    for package, name in checks:
        try:
            __import__(package)
            print(f"  ✅ {name}: Installed")
        except ImportError:
            print(f"  ❌ {name}: Not installed")
            all_ok = False
    
    return all_ok

def check_config():
    """Check if config file exists and is valid"""
    print("\n📋 Checking configuration...")
    
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            print("  ✅ Configuration file: Valid")
            print(f"     Theme: {config.get('output', {}).get('theme', 'dark')}")
            return True
        except Exception as e:
            print(f"  ❌ Configuration file: Invalid - {e}")
            return False
    else:
        print("  ⚠️  Configuration file: Not found (using defaults)")
        return True

def main():
    """Main test function"""
    print("=" * 60)
    print("Simple Signal CLI - Installation Test")
    print("=" * 60)
    
    deps_ok = check_dependencies()
    config_ok = check_config()
    
    print("\n" + "=" * 60)
    if deps_ok and config_ok:
        print("✅ All checks passed! Ready to run.")
        print("\nTo start the CLI:")
        print("  python ai_cli.py")
        print("Or with a model:")
        print('  MODEL_PATH="path/to/model" python ai_cli.py')
    else:
        print("❌ Some checks failed. Please install missing dependencies.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
