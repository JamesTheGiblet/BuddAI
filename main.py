#!/usr/bin/env python3
import argparse
import sys
import os

# Ensure we can import from current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from buddai_executive import BuddAI

def main():
    """
    Main entry point for BuddAI.
    Boots the executive and enters the interaction loop.
    """
    parser = argparse.ArgumentParser(description="BuddAI v4.0 - Symbiotic AI Exocortex")
    parser.add_argument("--server", action="store_true", help="Start in server mode (Web/WebSocket)")
    parser.add_argument("--user", type=str, default="default", help="User ID for session isolation")
    
    args = parser.parse_args()

    print("\n🔌 Booting BuddAI v4.0...")
    
    try:
        # Initialize Executive
        ai = BuddAI(user_id=args.user, server_mode=args.server)
        
        if args.server:
            print("🚀 Starting Server Mode...")
            try:
                # Attempt to import server module (if available)
                from buddai_server import start_server
                start_server(ai)
            except ImportError:
                print("⚠️  buddai_server.py not found. Falling back to CLI mode.")
                ai.run()
        else:
            # CLI Mode
            ai.run()
            
    except KeyboardInterrupt:
        print("\n👋 Shutdown sequence initiated.")
    except Exception as e:
        print(f"\n❌ Critical Startup Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()