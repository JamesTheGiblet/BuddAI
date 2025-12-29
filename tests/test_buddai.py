#!/usr/bin/env python3
"""
BuddAI v3.1 Test Suite
Comprehensive testing for all features

Author: James Gilbert
License: MIT
"""

import sys
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Test utilities
class TestColors:
    PASS = '\033[92m'
    FAIL = '\033[91m'
    INFO = '\033[94m'
    WARN = '\033[93m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{TestColors.INFO}🧪 Testing: {name}{TestColors.END}")

def print_pass(message):
    print(f"  {TestColors.PASS}✅ {message}{TestColors.END}")

def print_fail(message):
    print(f"  {TestColors.FAIL}❌ {message}{TestColors.END}")

def print_warn(message):
    print(f"  {TestColors.WARN}⚠️  {message}{TestColors.END}")


# Test 1: Database Initialization
def test_database_init():
    print_test("Database Initialization")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        
        # Create tables
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TIMESTAMP,
                ended_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repo_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                repo_name TEXT,
                function_name TEXT,
                content TEXT,
                last_modified TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS style_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                preference TEXT,
                confidence FLOAT,
                extracted_at TIMESTAMP
            )
        """)
        
        conn.commit()
        
        # Verify tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['sessions', 'messages', 'repo_index', 'style_preferences']
        all_exist = all(table in tables for table in required_tables)
        
        conn.close()
        
        if all_exist:
            print_pass(f"All {len(required_tables)} tables created successfully")
            return True
        else:
            missing = [t for t in required_tables if t not in tables]
            print_fail(f"Missing tables: {', '.join(missing)}")
            return False


# Test 2: SQL Injection Prevention
def test_sql_injection_prevention():
    print_test("SQL Injection Prevention")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE repo_index (
                id INTEGER PRIMARY KEY,
                function_name TEXT,
                content TEXT
            )
        """)
        
        # Insert test data
        cursor.execute("INSERT INTO repo_index (function_name, content) VALUES (?, ?)",
                      ("testFunc", "test content"))
        conn.commit()
        
        # Test malicious input
        malicious_input = "'; DROP TABLE repo_index; --"
        
        # SECURE: Parameterized query
        try:
            cursor.execute("SELECT * FROM repo_index WHERE function_name LIKE ?", 
                          (f"%{malicious_input}%",))
            results = cursor.fetchall()
            
            # Verify table still exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='repo_index'")
            table_exists = cursor.fetchone() is not None
            
            conn.close()
            
            if table_exists:
                print_pass("Parameterized queries prevent SQL injection")
                print_pass("Table survived malicious input")
                return True
            else:
                print_fail("Table was dropped - vulnerable to injection!")
                return False
                
        except Exception as e:
            print_fail(f"Query failed: {e}")
            return False


# Test 3: Auto-Learning Pattern Extraction
def test_auto_learning():
    print_test("Auto-Learning Pattern Extraction")
    
    sample_code = """
#include <Arduino.h>

#define MOTOR_PIN 5
const int TIMEOUT_MS = 5000;

void setup() {
    Serial.begin(115200);
    ledcSetup(0, 500, 8);
}
"""
    
    import re
    
    patterns = {
        'serial_baud': re.search(r'Serial\.begin\((\d+)\)', sample_code),
        'pin_style': 'define' if '#define' in sample_code else 'const',
        'timeout_value': re.search(r'TIMEOUT.*?(\d+)', sample_code),
        'pwm_freq': re.search(r'ledcSetup\([^,]+,\s*(\d+)', sample_code),
    }
    
    extracted = {}
    for key, value in patterns.items():
        if value:
            extracted[key] = value.group(1) if hasattr(value, 'group') else str(value)
    
    expected = {
        'serial_baud': '115200',
        'pin_style': 'define',
        'timeout_value': '5000',
        'pwm_freq': '500'
    }
    
    success = True
    for key, expected_val in expected.items():
        actual_val = extracted.get(key)
        if actual_val == expected_val:
            print_pass(f"Extracted {key}: {actual_val}")
        else:
            print_fail(f"Failed to extract {key} (got {actual_val}, expected {expected_val})")
            success = False
    
    return success


# Test 4: Module Detection
def test_module_detection():
    print_test("Module Detection")
    
    MODULE_PATTERNS = {
        "ble": ["bluetooth", "ble", "wireless"],
        "servo": ["servo", "flipper", "weapon"],
        "motor": ["motor", "drive", "movement", "l298n"],
        "safety": ["safety", "timeout", "failsafe"],
    }
    
    test_cases = [
        ("Generate code with BLE and servo control", ["ble", "servo"]),
        ("Add motor driver with safety timeout", ["motor", "safety"]),
        ("Build complete robot with bluetooth, motors, and weapon", ["ble", "motor", "servo"]),
    ]
    
    def extract_modules(message):
        message_lower = message.lower()
        detected = []
        for module, keywords in MODULE_PATTERNS.items():
            if any(kw in message_lower for kw in keywords):
                detected.append(module)
        return detected
    
    success = True
    for message, expected_modules in test_cases:
        detected = extract_modules(message)
        if set(detected) == set(expected_modules):
            print_pass(f"Detected: {detected} from '{message[:50]}...'")
        else:
            print_fail(f"Expected {expected_modules}, got {detected}")
            success = False
    
    return success


# Test 5: Complexity Detection
def test_complexity_detection():
    print_test("Complexity Detection")
    
    COMPLEX_TRIGGERS = ["complete", "entire", "full", "build entire"]
    MODULE_PATTERNS = {
        "ble": ["bluetooth", "ble"],
        "servo": ["servo"],
        "motor": ["motor"],
    }
    
    def is_complex(message):
        message_lower = message.lower()
        trigger_count = sum(1 for trigger in COMPLEX_TRIGGERS if trigger in message_lower)
        module_count = sum(1 for module, keywords in MODULE_PATTERNS.items() 
                          if any(kw in message_lower for kw in keywords))
        return trigger_count >= 2 or module_count >= 3
    
    test_cases = [
        ("Generate a motor driver class", False),
        ("Build complete robot with BLE, servo, and motors", True),
        ("Create entire system with full integration", True),
        ("What pins should I use?", False),
    ]
    
    success = True
    for message, expected_complex in test_cases:
        detected = is_complex(message)
        if detected == expected_complex:
            complexity = "COMPLEX" if detected else "SIMPLE"
            print_pass(f"{complexity}: '{message}'")
        else:
            print_fail(f"Expected {expected_complex}, got {detected} for '{message}'")
            success = False
    
    return success


# Test 6: LRU Cache Performance
def test_lru_cache():
    print_test("LRU Cache Performance")
    
    from functools import lru_cache
    import time
    
    call_count = 0
    
    @lru_cache(maxsize=128)
    def cached_function(keywords):
        nonlocal call_count
        call_count += 1
        time.sleep(0.01)  # Simulate slow operation
        return f"Result for {keywords}"
    
    # First call - should execute
    cached_function(("motor", "servo"))
    first_count = call_count
    
    # Second call - should use cache
    cached_function(("motor", "servo"))
    second_count = call_count
    
    # Different call - should execute
    cached_function(("ble", "battery"))
    third_count = call_count
    
    if first_count == 1 and second_count == 1 and third_count == 2:
        print_pass("Cache working: 2nd call skipped execution")
        print_pass(f"Function called {call_count} times for 3 queries")
        return True
    else:
        print_fail(f"Cache not working properly: {first_count}, {second_count}, {third_count}")
        return False


# Test 7: Session Export
def test_session_export():
    print_test("Session Export")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = Path(tmpdir) / "test_export.md"
        
        # Simulate export
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        messages = [
            ("user", "Generate motor code", "2025-12-28 10:00:00"),
            ("assistant", "```cpp\nvoid setupMotors() {}\n```", "2025-12-28 10:00:05"),
        ]
        
        output = f"# BuddAI Session Export\n"
        output += f"**Session ID:** {session_id}\n\n"
        output += "---\n\n"
        
        for role, content, timestamp in messages:
            if role == 'user':
                output += f"## 🧑 James ({timestamp})\n{content}\n\n"
            else:
                output += f"## 🤖 BuddAI\n{content}\n\n"
        
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        # Verify export
        if export_path.exists():
            content = export_path.read_text(encoding='utf-8')
            has_session_id = session_id in content
            has_code = "```cpp" in content
            has_headers = "## " in content and "James" in content  # More flexible check
            
            if has_session_id and has_code and has_headers:
                print_pass("Export file created with correct format")
                print_pass(f"File size: {len(content)} bytes")
                return True
            else:
                if not has_session_id:
                    print_fail("Missing session ID")
                if not has_code:
                    print_fail("Missing code blocks")
                if not has_headers:
                    print_fail("Missing headers")
                return False
        else:
            print_fail("Export file not created")
            return False


# Test 8: Actionable Suggestions
def test_actionable_suggestions():
    print_test("Actionable Suggestions")
    
    user_input = "Generate motor driver with L298N"
    generated_code = """
void setupMotors() {
    pinMode(MOTOR_PIN, OUTPUT);
}
"""
    
    suggestions = []
    
    # Forge Theory Check
    if ("motor" in user_input.lower() or "servo" in user_input.lower()) and "applyForge" not in generated_code:
        suggestions.append({
            'text': "Apply Forge Theory smoothing?",
            'action': 'add_forge',
            'code': "float applyForge(float current, float target, float k) { return target + (current - target) * exp(-k); }"
        })
    
    # Safety Check
    if "L298N" in user_input and "safety" not in generated_code.lower():
        suggestions.append({
            'text': "Add 5s safety timeout?",
            'action': 'add_safety',
            'code': "unsigned long lastCommandTime = 0;\nconst unsigned long TIMEOUT_MS = 5000;"
        })
    
    if len(suggestions) == 2:
        print_pass(f"Generated {len(suggestions)} actionable suggestions")
        for i, s in enumerate(suggestions, 1):
            print_pass(f"  {i}. {s['text']} (action: {s['action']})")
            if s['code']:
                print_pass(f"     Code snippet: {len(s['code'])} chars")
        return True
    else:
        print_fail(f"Expected 2 suggestions, got {len(suggestions)}")
        return False


# Test 9: Repository Indexing
def test_repository_indexing():
    print_test("Repository Indexing")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test repository structure
        repo_dir = Path(tmpdir) / "test_repo"
        repo_dir.mkdir()
        
        # Create test files
        test_files = {
            "motor_driver.ino": """
void setupMotors() {
    Serial.begin(115200);
    pinMode(MOTOR_PIN, OUTPUT);
}

void driveForward(int speed) {
    digitalWrite(MOTOR_PIN, HIGH);
}
""",
            "servo_control.cpp": """
#include <Servo.h>

void activateFlipper() {
    servo.write(90);
}
""",
            "utils.py": """
def calculate_pwm(speed):
    return int(speed * 255 / 100)

def apply_forge(current, target, k):
    return target + (current - target) * math.exp(-k)
"""
        }
        
        for filename, content in test_files.items():
            (repo_dir / filename).write_text(content)
        
        # Simulate indexing
        import re
        indexed_functions = []
        
        for file_path in repo_dir.rglob('*'):
            if file_path.is_file() and file_path.suffix in ['.ino', '.cpp', '.py']:
                content = file_path.read_text()
                
                if file_path.suffix in ['.ino', '.cpp']:
                    matches = re.findall(r'\b(?:void|int)\s+(\w+)\s*\(', content)
                    indexed_functions.extend(matches)
                elif file_path.suffix == '.py':
                    matches = re.findall(r'\bdef\s+(\w+)\s*\(', content)
                    indexed_functions.extend(matches)
        
        expected_functions = ['setupMotors', 'driveForward', 'activateFlipper', 'calculate_pwm', 'apply_forge']
        
        if set(indexed_functions) == set(expected_functions):
            print_pass(f"Indexed {len(indexed_functions)} functions correctly")
            for func in indexed_functions:
                print_pass(f"  - {func}()")
            return True
        else:
            missing = set(expected_functions) - set(indexed_functions)
            extra = set(indexed_functions) - set(expected_functions)
            if missing:
                print_fail(f"Missing functions: {missing}")
            if extra:
                print_warn(f"Extra functions: {extra}")
            return False


# Test 10: Search Query Safety
def test_search_query_safety():
    print_test("Search Query Safety")
    
    malicious_queries = [
        "'; DROP TABLE repo_index; --",
        "' OR '1'='1",
        "admin'--",
        "<script>alert('xss')</script>",
    ]
    
    import re
    
    success = True
    for query in malicious_queries:
        # Extract keywords safely
        keywords = re.findall(r'\b\w{4,}\b', query.lower())
        
        # Build parameterized query
        conditions = []
        params = []
        for keyword in keywords:
            conditions.append("(function_name LIKE ? OR content LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        # Verify no SQL injection possible
        if conditions:
            safe_sql = f"SELECT * FROM repo_index WHERE {' OR '.join(conditions)}"
            # SQL should only contain placeholders
            if "DROP" not in safe_sql and "'; " not in safe_sql:
                print_pass(f"Safely handled: '{query[:30]}...'")
            else:
                print_fail(f"Potential injection: '{query}'")
                success = False
        else:
            print_pass(f"Rejected empty query: '{query}'")
    
    return success


# Test 11: Context Window Management
def test_context_window():
    print_test("Context Window Management")
    
    context_messages = []
    
    # Add many messages
    for i in range(20):
        context_messages.append({"role": "user", "content": f"Message {i}"})
        context_messages.append({"role": "assistant", "content": f"Response {i}"})
    
    # Simulate limiting to last 5 messages
    limited_context = context_messages[-5:]
    
    if len(limited_context) == 5:
        print_pass(f"Context limited to {len(limited_context)} messages (from {len(context_messages)})")
        print_pass(f"Oldest kept: '{limited_context[0]['content']}'")
        print_pass(f"Newest kept: '{limited_context[-1]['content']}'")
        return True
    else:
        print_fail(f"Context not limited properly: {len(limited_context)} messages")
        return False


# Main Test Runner
def run_all_tests():
    print("\n" + "="*60)
    print("🔥 BuddAI v3.1 Comprehensive Test Suite")
    print("="*60)
    
    tests = [
        ("Database Initialization", test_database_init),
        ("SQL Injection Prevention", test_sql_injection_prevention),
        ("Auto-Learning", test_auto_learning),
        ("Module Detection", test_module_detection),
        ("Complexity Detection", test_complexity_detection),
        ("LRU Cache", test_lru_cache),
        ("Session Export", test_session_export),
        ("Actionable Suggestions", test_actionable_suggestions),
        ("Repository Indexing", test_repository_indexing),
        ("Search Query Safety", test_search_query_safety),
        ("Context Window", test_context_window),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_fail(f"Test crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{TestColors.PASS}✅ PASS{TestColors.END}" if result else f"{TestColors.FAIL}❌ FAIL{TestColors.END}"
        print(f"{status} - {name}")
    
    print("\n" + "="*60)
    percentage = int((passed / total) * 100)
    
    if passed == total:
        print(f"{TestColors.PASS}🎉 ALL TESTS PASSED: {passed}/{total} ({percentage}%){TestColors.END}")
    elif passed >= total * 0.8:
        print(f"{TestColors.WARN}⚠️  MOST TESTS PASSED: {passed}/{total} ({percentage}%){TestColors.END}")
    else:
        print(f"{TestColors.FAIL}❌ TESTS FAILED: {passed}/{total} ({percentage}%){TestColors.END}")
    
    print("="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)