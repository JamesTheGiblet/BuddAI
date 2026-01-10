"""
JavaScript Language Skill
ES6+, DOM manipulation, async patterns, and modern best practices
"""

import re
from typing import Dict, List, Optional
from .language_base import LanguageSkill

class JavaScriptSkill(LanguageSkill):
    """
    JavaScript (ES6+) language skill
    
    Provides:
    - Modern ES6+ patterns
    - Async/await best practices
    - DOM manipulation patterns
    - Event handling
    - Common pitfalls and solutions
    - Anti-pattern detection
    """
    
    def __init__(self):
        super().__init__(
            name="JavaScript",
            file_extensions=['.js', '.mjs', '.jsx', '.ts', '.tsx']
        )
    
    def _load_patterns(self):
        """Load JavaScript patterns and best practices"""
        
        # Modern JavaScript patterns
        self.patterns = {
            'arrow_functions': {
                'description': 'ES6 arrow functions',
                'pattern': r'=>',
                'example': 'const add = (a, b) => a + b;\nconst greet = name => `Hello ${name}`;'
            },
            'const_let': {
                'description': 'Modern variable declarations',
                'pattern': r'\b(const|let)\s+',
                'example': 'const name = "value";\nlet count = 0;'
            },
            'template_literals': {
                'description': 'Template literals for string interpolation',
                'pattern': r'`[^`]*\$\{[^}]+\}[^`]*`',
                'example': 'const message = `Hello ${name}!`;'
            },
            'async_await': {
                'description': 'Async/await for asynchronous code',
                'pattern': r'\basync\s+\w+|\bawait\s+',
                'example': 'async function fetchData() {\n  const data = await fetch(url);\n  return data.json();\n}'
            },
            'destructuring': {
                'description': 'Destructuring assignment',
                'pattern': r'(const|let)\s*\{[^}]+\}\s*=|const\s*\[[^\]]+\]\s*=',
                'example': 'const { name, age } = user;\nconst [first, second] = array;'
            },
            'spread_operator': {
                'description': 'Spread operator for arrays/objects',
                'pattern': r'\.\.\.',
                'example': 'const newArray = [...oldArray, newItem];\nconst merged = { ...obj1, ...obj2 };'
            },
            'array_methods': {
                'description': 'Modern array methods',
                'pattern': r'\.(map|filter|reduce|find|some|every|forEach)\(',
                'example': 'const doubled = numbers.map(n => n * 2);\nconst evens = numbers.filter(n => n % 2 === 0);'
            },
            'promises': {
                'description': 'Promise-based asynchronous code',
                'pattern': r'new Promise\(|\.then\(|\.catch\(',
                'example': 'fetch(url)\n  .then(res => res.json())\n  .then(data => console.log(data))\n  .catch(err => console.error(err));'
            }
        }
        
        # Anti-patterns to avoid
        self.anti_patterns = {
            'var_keyword': {
                'description': 'Using var instead of const/let',
                'pattern': r'\bvar\s+',
                'fix': 'Use const for constants and let for variables'
            },
            'callback_hell': {
                'description': 'Nested callbacks (pyramid of doom)',
                'pattern': r'function\s*\([^)]*\)\s*\{[^}]*function\s*\([^)]*\)\s*\{[^}]*function\s*\([^)]*\)\s*\{',
                'fix': 'Use async/await or Promises to flatten callback chains'
            },
            'string_concatenation': {
                'description': 'String concatenation instead of template literals',
                'pattern': r'["\'][^"\']*["\']\s*\+\s*\w+\s*\+\s*["\']',
                'fix': 'Use template literals: `Hello ${name}`'
            },
            'loose_equality': {
                'description': 'Using == instead of ===',
                'pattern': r'[^=!<>]==[^=]|!=[^=]',
                'fix': 'Use strict equality (===) and inequality (!==)'
            },
            'implicit_globals': {
                'description': 'Variables without declaration keywords',
                'pattern': r'^\s*\w+\s*=\s*[^=]',
                'fix': 'Always declare variables with const, let, or var'
            },
            'eval_usage': {
                'description': 'Using eval() (security risk)',
                'pattern': r'\beval\s*\(',
                'fix': 'Avoid eval() - use JSON.parse() or safer alternatives'
            },
            'blocking_loops': {
                'description': 'Synchronous loops on large datasets',
                'pattern': r'for\s*\([^)]*;[^)]*;[^)]*\)\s*\{[\s\S]{200,}',
                'fix': 'Consider async iteration or chunking for large datasets'
            }
        }
        
        # Best practices
        self.best_practices = [
            'Use const by default, let when reassignment is needed, never var',
            'Prefer arrow functions for callbacks and short functions',
            'Use template literals for string interpolation',
            'Use async/await instead of nested callbacks',
            'Use strict equality (===) instead of loose equality (==)',
            'Destructure objects and arrays for cleaner code',
            'Use spread operator for copying arrays/objects',
            'Prefer array methods (map, filter, reduce) over for loops',
            'Handle promise rejections with .catch() or try/catch',
            'Use optional chaining (?.) for safe property access',
            'Use nullish coalescing (??) for default values',
            'Avoid modifying function arguments (immutability)',
            'Use meaningful variable and function names',
            'Keep functions small and focused (single responsibility)',
            'Add error handling for all async operations'
        ]
    
    def validate(self, code: str) -> Dict:
        """
        Validate JavaScript code
        
        Checks for:
        - Use of var keyword
        - Callback hell patterns
        - String concatenation instead of template literals
        - Loose equality operators
        - Missing error handling
        - Common pitfalls
        """
        
        issues = []
        warnings = []
        suggestions = []
        
        # Check for var usage
        var_count = len(re.findall(r'\bvar\s+', code))
        if var_count > 0:
            warnings.append(f'Found {var_count} uses of "var" - use const/let instead')
        
        # Check for loose equality
        loose_equality = re.findall(r'[^=!<>]==[^=]|!=[^=]', code)
        if loose_equality:
            warnings.append(f'Using loose equality (==) - use strict equality (===) instead')
        
        # Check for callback hell
        nested_callbacks = re.findall(
            r'function\s*\([^)]*\)\s*\{[^}]*function\s*\([^)]*\)\s*\{[^}]*function',
            code
        )
        if nested_callbacks:
            suggestions.append('Detected nested callbacks - consider using async/await')
        
        # Check for string concatenation
        string_concat = re.findall(r'["\'][^"\']*["\']\s*\+\s*\w+', code)
        if len(string_concat) > 2:
            suggestions.append('Using string concatenation - consider template literals')
        
        # Check for modern features
        has_const_let = bool(re.search(r'\b(const|let)\s+', code))
        has_arrow = bool(re.search(r'=>', code))
        
        if len(code) > 100:
            if not has_const_let:
                suggestions.append('Consider using const/let instead of var')
            if not has_arrow and 'function' in code:
                suggestions.append('Consider using arrow functions for cleaner syntax')
        
        # Check for async patterns
        has_async = bool(re.search(r'\basync\s+|\bawait\s+', code))
        has_promises = bool(re.search(r'\.then\(|\.catch\(|new Promise', code))
        
        if has_promises and not has_async:
            suggestions.append('Consider using async/await instead of .then() chains')
        
        # Check for error handling in async code
        if has_async or has_promises:
            has_error_handling = bool(re.search(r'\.catch\(|try\s*\{|catch\s*\(', code))
            if not has_error_handling:
                warnings.append('Async code missing error handling (try/catch or .catch())')
        
        # Check for eval
        if re.search(r'\beval\s*\(', code):
            issues.append('Using eval() is a security risk - use safer alternatives')
        
        # Check for console.log in production-like code
        console_logs = len(re.findall(r'console\.(log|debug|info)', code))
        if console_logs > 5 and len(code) > 500:
            suggestions.append(f'Found {console_logs} console statements - consider using proper logging')
        
        # Check for missing semicolons (if using semicolons)
        has_semicolons = ';' in code
        lines = code.split('\n')
        if has_semicolons:
            missing_semi = [i for i, line in enumerate(lines) 
                          if line.strip() and not line.strip().endswith((';', '{', '}', ','))
                          and not line.strip().startswith(('if', 'else', 'for', 'while', '//'))]
            if len(missing_semi) > 3:
                suggestions.append('Inconsistent semicolon usage - be consistent')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def get_template(self, template_name: str) -> Optional[str]:
        """Get JavaScript template by name"""
        
        templates = {
            'async_fetch': '''// Async/await fetch pattern
async function fetchData(url) {
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error;
  }
}

// Usage
fetchData('https://api.example.com/data')
  .then(data => console.log(data))
  .catch(err => console.error(err));''',
            
            'dom_manipulation': '''// Modern DOM manipulation
const app = document.querySelector('#app');

// Create elements
const createCard = (title, content) => {
  const card = document.createElement('div');
  card.className = 'card';
  
  card.innerHTML = `
    <h2>${title}</h2>
    <p>${content}</p>
  `;
  
  return card;
};

// Event handling with delegation
app.addEventListener('click', (event) => {
  if (event.target.matches('.button')) {
    handleButtonClick(event.target);
  }
});

// Add multiple elements
const cards = data.map(item => createCard(item.title, item.content));
app.append(...cards);''',
            
            'event_handling': '''// Modern event handling patterns
class EventManager {
  constructor() {
    this.listeners = new Map();
  }
  
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }
  
  emit(event, data) {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach(callback => callback(data));
  }
  
  off(event, callback) {
    const callbacks = this.listeners.get(event) || [];
    const index = callbacks.indexOf(callback);
    if (index > -1) {
      callbacks.splice(index, 1);
    }
  }
}

// Usage
const events = new EventManager();
events.on('user:login', (user) => console.log('User logged in:', user));
events.emit('user:login', { name: 'John' });''',
            
            'array_operations': '''// Modern array operations
const numbers = [1, 2, 3, 4, 5];

// Transform data
const doubled = numbers.map(n => n * 2);
const evens = numbers.filter(n => n % 2 === 0);
const sum = numbers.reduce((acc, n) => acc + n, 0);

// Find items
const first = numbers.find(n => n > 2);
const hasLarge = numbers.some(n => n > 10);
const allPositive = numbers.every(n => n > 0);

// Chain operations
const result = numbers
  .filter(n => n % 2 === 0)
  .map(n => n * 2)
  .reduce((acc, n) => acc + n, 0);

// Object array operations
const users = [
  { name: 'Alice', age: 25 },
  { name: 'Bob', age: 30 }
];

const names = users.map(u => u.name);
const adults = users.filter(u => u.age >= 18);
const averageAge = users.reduce((acc, u) => acc + u.age, 0) / users.length;''',
            
            'class_module': '''// Modern class with private fields
class User {
  #password; // Private field
  
  constructor(name, email, password) {
    this.name = name;
    this.email = email;
    this.#password = password;
  }
  
  // Getter
  get displayName() {
    return this.name.toUpperCase();
  }
  
  // Method
  verifyPassword(input) {
    return this.#password === input;
  }
  
  // Static method
  static fromJSON(json) {
    return new User(json.name, json.email, json.password);
  }
}

// Usage
const user = new User('John', 'john@example.com', 'secret');
console.log(user.displayName); // JOHN
console.log(user.verifyPassword('secret')); // true''',
            
            'promise_patterns': '''// Advanced Promise patterns

// Promise.all - wait for all
async function fetchMultiple(urls) {
  const promises = urls.map(url => fetch(url));
  const responses = await Promise.all(promises);
  return Promise.all(responses.map(r => r.json()));
}

// Promise.race - first to complete
async function fetchWithTimeout(url, timeout = 5000) {
  const fetchPromise = fetch(url);
  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Timeout')), timeout)
  );
  
  return Promise.race([fetchPromise, timeoutPromise]);
}

// Promise.allSettled - all results (success or failure)
async function fetchAllResults(urls) {
  const promises = urls.map(url => fetch(url));
  const results = await Promise.allSettled(promises);
  
  return results.map(result => ({
    success: result.status === 'fulfilled',
    data: result.status === 'fulfilled' ? result.value : result.reason
  }));
}

// Retry pattern
async function fetchWithRetry(url, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fetch(url);
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}'''
        }
        
        return templates.get(template_name, None)

    def get_common_pitfalls(self) -> List[str]:
        """Get common JavaScript pitfalls"""
        return [
            'Using var instead of const/let (hoisting issues)',
            'Callback hell (nested callbacks)',
            'Blocking the event loop with synchronous operations',
            'Floating point math errors (0.1 + 0.2 !== 0.3)',
            'this context binding issues',
            'Implicit type coercion (== vs ===)',
            'Modifying objects/arrays directly (mutability)',
            'Memory leaks from event listeners or closures'
        ]

    def get_es6_features(self) -> List[str]:
        """Get list of ES6+ features to use"""
        return [
            'Arrow functions',
            'Async/await',
            'Destructuring assignment',
            'Template literals',
            'Spread/Rest operators',
            'Classes',
            'Modules (import/export)',
            'Promises',
            'Map/Set data structures',
            'Default parameters'
        ]

    def get_performance_tips(self) -> List[str]:
        """Get JavaScript performance optimization tips"""
        return [
            '✓ Debounce or throttle expensive event handlers (scroll, resize)',
            '✓ Use requestAnimationFrame for animations',
            '✓ Avoid memory leaks (clean up listeners)',
            '✓ Use Web Workers for heavy computation',
            '✓ Minimize DOM manipulation (batch updates)',
            '✓ Use virtualization for long lists',
            '✓ Lazy load modules and components',
            '✓ Optimize loops and array operations'
        ]