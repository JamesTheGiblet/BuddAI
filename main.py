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
    parser = argparse.ArgumentParser(description="BuddAI v5.0 - Symbiotic AI Exocortex")
    parser.add_argument("--server", action="store_true", help="Start in server mode (Web/WebSocket)")
    parser.add_argument("--user", type=str, default="default", help="User ID for session isolation")
    parser.add_argument("--port", type=int, default=8000, help="Port for server mode")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP address")
    parser.add_argument("--public-url", type=str, default="", help="Public URL for QR codes")
    parser.add_argument("prompt", nargs="?", help="One-shot prompt to execute")
    
    args = parser.parse_args()

    # Fix for Windows console encoding (emojis)
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    print("\n🔌 Booting BuddAI v5.0...")
    
    try:
        # Initialize Executive
        ai = BuddAI(user_id=args.user, server_mode=args.server)
        
        if args.server:
            print("🚀 Starting Server Mode...")
            try:
                # Attempt to import server module (if available)
                from buddai_server import start_server
                start_server(ai, host=args.host, port=args.port, public_url=args.public_url)
            except ImportError:
                print("⚠️  buddai_server.py not found. Falling back to CLI mode.")
                ai.run()
        else:
            # CLI Mode (Interactive or One-Shot)
            if args.prompt:
                print(ai.chat(args.prompt))
            else:
                ai.run()
            
    except KeyboardInterrupt:
        print("\n👋 Shutdown sequence initiated.")
    except Exception as e:
        print(f"\n❌ Critical Startup Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()