import subprocess
import sys
import time

# -------------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------------
# Command to run BuddAI in CLI mode. 
# Adjust "buddai_executive.py" to your actual entry point if different.
# Example: ["python", "buddai_executive.py", "--cli"]
CLI_COMMAND = [sys.executable, "buddai_executive.py", "--cli"]

# -------------------------------------------------------------------------
# TEST SCENARIOS (Based on EVOLUTION_v3.8_to_v4.0.md)
# -------------------------------------------------------------------------
SCENARIOS = [
    {
        "id": "Q1",
        "name": "PWM LED Control (Hardware Check)",
        "prompt": "Generate ESP32 PWM LED control code.",
        "must_contain": ["ESP32Servo.h", "attach"],
        "should_not_contain": ["analogWrite"], # Arduino standard, often wrong for ESP32 specific
        "notes": "Checks if the 'Use ESP32Servo.h' correction was learned."
    },
    {
        "id": "Q5",
        "name": "State Machine Logic (Pattern Check)",
        "prompt": "Write a state machine for a robot system.",
        "must_contain": ["enum", "switch", "case", "break"],
        "notes": "Ensures software logic (switch/case) is generated, not hardware positioning."
    },
    {
        "id": "Q8",
        "name": "Forge Theory Methodology (Personality Check)",
        "prompt": "Generate motor speed control using Forge Theory.",
        "must_contain": ["target - current", "* k", "+="],
        "notes": "Verifies the exponential decay formula: current += (target - current) * k"
    },
    {
        "id": "Q10",
        "name": "Complex System Decomposition (Architecture Check)",
        "prompt": "Build a combat robot with drive, weapon, battery, and safety systems.",
        "must_contain": ["Safety", "Battery", "Drive", "Weapon"],
        "notes": "Checks if the Modular Builder breaks down the request."
    }
]

def run_test(scenario):
    print(f"Running {scenario['id']}: {scenario['name']}...")
    print(f"  Prompt: \"{scenario['prompt']}\"")
    
    try:
        # Run the CLI command with the prompt as an argument
        # Assuming the CLI takes the prompt as the last argument
        cmd = CLI_COMMAND + [scenario['prompt']]
        
        start_time = time.time()
        # Run process
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=120 # Generous timeout for generation
        )
        duration = time.time() - start_time
        
        if result.returncode != 0:
            print(f"  ❌ FAILED: Process exited with code {result.returncode}")
            if result.stderr:
                print(f"  Stderr: {result.stderr.strip()}")
            return False

        output = result.stdout
        passed = True
        missing = []
        
        # Check required keywords
        for keyword in scenario.get("must_contain", []):
            if keyword.lower() not in output.lower():
                passed = False
                missing.append(keyword)
        
        # Check forbidden keywords
        for keyword in scenario.get("should_not_contain", []):
            if keyword.lower() in output.lower():
                passed = False
                print(f"  ❌ FAILED: Output contained forbidden term '{keyword}'")

        if passed:
            print(f"  ✅ PASSED in {duration:.2f}s")
            return True
        else:
            print(f"  ❌ FAILED: Missing keywords: {missing}")
            return False

    except FileNotFoundError:
        print(f"  ❌ ERROR: Could not find executable: {CLI_COMMAND}")
        print("     Please update CLI_COMMAND in the script to point to your python file.")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def main():
    print("===================================================")
    print("   BUDDAI v5.0 VALIDATION RUNNER")
    print("===================================================")
    
    passed_count = 0
    for scenario in SCENARIOS:
        if run_test(scenario):
            passed_count += 1
        print("-" * 50)
    
    print(f"\nResults: {passed_count}/{len(SCENARIOS)} Passed")
    
    if passed_count == len(SCENARIOS):
        print("🏆 ALL SYSTEMS NOMINAL. SYMBIOSIS CONFIRMED.")
    else:
        print("⚠️  SOME TESTS FAILED. CHECK LEARNING DATABASE.")

if __name__ == "__main__":
    main()
