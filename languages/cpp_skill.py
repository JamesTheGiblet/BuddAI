"""
C++ Language Skill
Embedded systems, Arduino/ESP32 patterns, and memory safety
"""

import re
from typing import Dict, List, Optional
from .language_base import LanguageSkill

class CPPSkill(LanguageSkill):
    """
    C++ language skill for Embedded Systems
    """
    def __init__(self):
        super().__init__(
            name="C++",
            file_extensions=['.cpp', '.h', '.hpp', '.ino', '.c', '.cc']
        )

    def _load_patterns(self):
        self.patterns = {
            'raii': {
                'description': 'Resource Acquisition Is Initialization',
                'pattern': r'std::lock_guard|std::unique_ptr|std::shared_ptr',
                'example': 'std::lock_guard<std::mutex> lock(mutex);'
            },
            'arduino_setup_loop': {
                'description': 'Standard Arduino structure',
                'pattern': r'void\s+setup\s*\(\)\s*\{.*void\s+loop\s*\(\)\s*\{',
                'example': 'void setup() { }\nvoid loop() { }'
            },
            'const_correctness': {
                'description': 'Use const for immutable variables/methods',
                'pattern': r'\bconst\s+',
                'example': 'const int MAX_BUFFER = 100;'
            }
        }

        self.anti_patterns = {
            'buffer_overflow': {
                'description': 'Unsafe string copy (strcpy)',
                'pattern': r'\bstrcpy\s*\(',
                'fix': 'Use strncpy or std::string'
            },
            'memory_leak': {
                'description': 'Raw new without delete',
                'pattern': r'\bnew\s+\w+',
                'fix': 'Use smart pointers (std::unique_ptr) or stack allocation'
            },
            'blocking_delay': {
                'description': 'Blocking delay in loop',
                'pattern': r'\bdelay\s*\(',
                'fix': 'Use millis() for non-blocking timing'
            }
        }
        
        self.best_practices = [
            'Use RAII for resource management',
            'Prefer std::string over char arrays',
            'Use smart pointers instead of raw pointers',
            'Avoid blocking delays in main loops',
            'Use const wherever possible',
            'Initialize variables upon declaration',
            'Use nullptr instead of NULL',
            'Prefer references over pointers for arguments'
        ]

    def validate(self, code: str) -> Dict:
        issues = []
        warnings = []
        suggestions = []

        # Check for strcpy
        if re.search(r'\bstrcpy\s*\(', code):
            issues.append('Unsafe strcpy detected - potential buffer overflow')

        # Check for raw new usage (simple check)
        if re.search(r'\bnew\s+', code) and not re.search(r'\bdelete\s+', code):
            warnings.append('Raw "new" detected without obvious "delete" - check for leaks')

        # Check for blocking delay
        if re.search(r'\bdelay\s*\(', code):
            warnings.append('Blocking delay() detected - consider using millis()')

        # Check for void* usage
        if re.search(r'void\s*\*', code):
            suggestions.append('Avoid void* - use templates or specific types')

        # Check for NULL vs nullptr
        if re.search(r'\bNULL\b', code):
            suggestions.append('Use nullptr instead of NULL (C++11+)')

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def get_template(self, template_name: str) -> Optional[str]:
        templates = {
            'arduino_basic': '''#include <Arduino.h>

const int LED_PIN = 2;

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
}

void loop() {
  // Non-blocking blink
  static unsigned long lastToggle = 0;
  if (millis() - lastToggle > 1000) {
    digitalWrite(LED_PIN, !digitalRead(LED_PIN));
    lastToggle = millis();
  }
}''',
            'class_header': '''#ifndef MY_CLASS_H
#define MY_CLASS_H

class MyClass {
public:
    MyClass();
    ~MyClass();
    
    void doSomething();

private:
    int m_data;
};

#endif // MY_CLASS_H'''
        }
        return templates.get(template_name)