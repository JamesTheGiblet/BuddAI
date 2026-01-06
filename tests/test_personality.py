import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path so we can import buddai modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from buddai_executive import BuddAI

def test_personality_loading():
    print("🧪 Testing Personality Loading...")
    
    # Initialize BuddAI (mocking server_mode to avoid input loops)
    try:
        ai = BuddAI(user_id="test_user", server_mode=True)
        
        # 1. Check Identity & Meta
        print("\n👤 Verifying Identity & Meta...")
        user_name = ai.get_personality_value("identity.user_name")
        ai_name = ai.get_personality_value("identity.ai_name")
        version = ai.get_personality_value("meta.version")
        
        if user_name == "James" and ai_name == "BuddAI":
            print(f"✅ Identity Loaded: {ai_name} v{version} is ready to assist {user_name}")
        else:
            print(f"❌ Identity Mismatch. Got User: {user_name}, AI: {ai_name}")
            
        # 2. Check Communication & Phrases
        print("\n💬 Verifying Communication Style...")
        welcome = ai.get_personality_value("communication.welcome_message")
        phrases = ai.get_personality_value("identity.signature_phrases")
        
        if welcome and "{rule_count}" in welcome:
             print(f"✅ Welcome Message Template Loaded")
        else:
             print(f"❌ Welcome Message Issue: {welcome}")
             
        if phrases and len(phrases) > 0:
            print(f"✅ Loaded {len(phrases)} signature phrases (e.g., '{phrases[0]}')")
        else:
            print("❌ No signature phrases found")

        # 3. Test Schedule Logic & Work Cycles
        print("\n⏰ Testing Schedule & Work Cycles...")
        status = ai.get_user_status()
        current_time = datetime.now().strftime('%H:%M')
        print(f"   Current Time: {current_time}")
        print(f"   Detected Status: {status}")
        
        # Verify specific schedule slots exist
        morning_mode = ai.get_personality_value(["work_cycles", "schedule", "weekdays", "0-4", "5.5-6.5", "mode"])
        if morning_mode == "morning_build_peak":
            print("✅ Morning Build Peak schedule slot verified")
        else:
            print(f"❌ Morning schedule slot missing or incorrect: {morning_mode}")

        # 4. Verify Forge Theory Configuration
        print("\n⚡ Verifying Forge Theory...")
        forge_enabled = ai.get_personality_value("forge_theory.enabled")
        k_balanced = ai.get_personality_value("forge_theory.constants.balanced.value")
        formula = ai.get_personality_value("forge_theory.formula")
        
        if forge_enabled and k_balanced == 0.1:
            print(f"✅ Forge Theory Active (Balanced k={k_balanced})")
            print(f"   Formula: {formula}")
        else:
            print(f"❌ Forge Theory configuration mismatch")

        # 5. Verify Technical Preferences
        print("\n🛠️  Verifying Technical Preferences...")
        baud = ai.get_personality_value("technical_preferences.james_patterns.serial_baud")
        safety = ai.get_personality_value("technical_preferences.james_patterns.safety_first")
        
        if "115200" in str(baud) and "5000ms" in str(safety):
            print(f"✅ Technical Patterns Loaded: Baud {baud}, Safety {safety}")
        else:
            print(f"❌ Technical preferences mismatch")

        # 6. Verify Interaction Modes
        print("\n🔄 Verifying Interaction Modes...")
        modes = ai.get_personality_value("interaction_modes")
        if modes and "morning_build" in modes and "evening_build" in modes:
            print(f"✅ Interaction Modes Loaded: {', '.join(modes.keys())}")
        else:
            print("❌ Interaction modes missing")

        # 7. Verify Deep Key Access (Advanced Features)
        print("\n🔑 Verifying Advanced Features...")
        shadow_enabled = ai.get_personality_value("advanced_features.shadow_suggestions.enabled")
        auto_fix = ai.get_personality_value("advanced_features.self_correction.enabled")
        
        if shadow_enabled and auto_fix:
            print("✅ Advanced features (Shadow Suggestions, Self Correction) enabled")
        else:
            print("❌ Advanced features configuration issue")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_personality_loading()
