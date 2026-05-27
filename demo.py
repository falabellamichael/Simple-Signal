#!/usr/bin/env python3
"""
Demo script showing Simple Signal CLI output
Run this to see what the CLI looks like without starting the full app
"""

import sys
sys.path.insert(0, '.')

from ai_cli import SimpleSignalAI, CLIInterface

def demo():
    """Run a quick demo of the CLI interface"""
    
    # Create AI instance (will run in demo mode)
    ai = SimpleSignalAI()
    cli = CLIInterface(ai)
    
    print("\n" + "=" * 60)
    print("Simple Signal CLI - Demo Mode")
    print("=" * 60)
    print("\nThis is a demonstration of the CLI interface.")
    print("Type messages below and press Enter to chat!")
    print("Type 'quit' or 'q' to exit.\n")
    
    # Simulate some demo interactions
    demo_messages = [
        "Hello! I'm Simple Signal AI.",
        "I can help you with various tasks.",
        "Try asking me something!",
        "What can you do?",
    ]
    
    for msg in demo_messages:
        print(f"\n🤖 {msg}")
    
    print("\n" + "=" * 60)
    print("To use the full interactive mode:")
    print("  python ai_cli.py")
    print("=" * 60)

if __name__ == "__main__":
    demo()
