"""
Documentation Generator Workflow
Automatically generates project documentation
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
from .workflow_base import Workflow, WorkflowStep

class DocumentationWorkflow(Workflow):
    """
    Generates comprehensive project documentation
    
    Creates:
    - README.md
    - ARCHITECTURE.md
    - API documentation
    - Usage examples
    - Contributing guidelines
    """
    
    def __init__(self):
        super().__init__(
            name='generate_documentation',
            description='Generate comprehensive project documentation'
        )
    
    def detect(self, user_input: str) -> float:
        """Detect if this is a documentation request"""
        
        user_input_lower = user_input.lower()
        
        # High confidence patterns
        high_patterns = [
            r'generate\s+(?:the\s+)?documentation',
            r'write\s+(?:a\s+)?(?:the\s+)?readme',
            r'create\s+(?:project\s+)?docs',
            r'document\s+(?:this\s+)?(?:the\s+)?project'
        ]
        
        for pattern in high_patterns:
            if re.search(pattern, user_input_lower):
                return 0.9
        
        # Medium confidence
        doc_keywords = ['documentation', 'readme', 'docs', 'document']
        action_keywords = ['generate', 'create', 'write', 'make']
        
        has_doc = any(kw in user_input_lower for kw in doc_keywords)
        has_action = any(kw in user_input_lower for kw in action_keywords)
        
        if has_doc and has_action:
            return 0.7
        elif has_doc:
            return 0.5
        
        return 0.0
    
    def plan(self, user_input: str, context: Dict = None) -> List[WorkflowStep]:
        """Create documentation generation plan"""
        
        context = context or {}
        
        # Analyze project
        self.add_step(
            'analyze_project',
            'Analyze project structure and code',
            'analyze',
            {'path': context.get('project_path', '.')}
        )
        
        # Generate README
        self.add_step(
            'generate_readme',
            'Generate README.md with project overview',
            'generate_readme',
            {'project_info': None}  # Will be filled by analyze step
        )
        
        # Generate architecture docs
        self.add_step(
            'generate_architecture',
            'Generate ARCHITECTURE.md with system design',
            'generate_architecture',
            {'project_info': None}
        )
        
        # Generate API docs if applicable
        if context.get('has_api', True):
            self.add_step(
                'generate_api_docs',
                'Generate API documentation',
                'generate_api',
                {'api_info': None}
            )
        
        # Generate usage examples
        self.add_step(
            'generate_examples',
            'Generate usage examples',
            'generate_examples',
            {'project_info': None}
        )
        
        # Generate contributing guide
        self.add_step(
            'generate_contributing',
            'Generate CONTRIBUTING.md',
            'generate_contributing',
            {}
        )
        
        return self.steps
    
    def _execute_step(self, step: WorkflowStep, context: Dict) -> Dict:
        """Execute a documentation generation step"""
        
        action = step.action
        
        if action == 'analyze':
            return self._analyze_project(step.parameters, context)
        
        elif action == 'generate_readme':
            return self._generate_readme(step.parameters, context)
        
        elif action == 'generate_architecture':
            return self._generate_architecture(step.parameters, context)
        
        elif action == 'generate_api':
            return self._generate_api_docs(step.parameters, context)
        
        elif action == 'generate_examples':
            return self._generate_examples(step.parameters, context)
        
        elif action == 'generate_contributing':
            return self._generate_contributing(step.parameters, context)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    def _analyze_project(self, params: Dict, context: Dict) -> Dict:
        """Analyze project structure"""
        
        project_path = params.get('path', '.')
        
        # Detect project type
        project_type = self._detect_project_type(project_path)
        
        # Find source files
        source_files = self._find_source_files(project_path)
        
        # Extract dependencies
        dependencies = self._extract_dependencies(project_path)
        
        # Detect testing framework
        test_framework = self._detect_test_framework(project_path)
        
        project_info = {
            'type': project_type,
            'source_files': source_files,
            'dependencies': dependencies,
            'test_framework': test_framework,
            'has_tests': len([f for f in source_files if 'test' in f.lower()]) > 0
        }
        
        # Store in context for other steps
        context['project_info'] = project_info
        
        return project_info
    
    def _detect_project_type(self, path: str) -> str:
        """Detect project type"""
        
        if os.path.exists(os.path.join(path, 'package.json')):
            return 'javascript'
        elif os.path.exists(os.path.join(path, 'requirements.txt')) or \
             os.path.exists(os.path.join(path, 'setup.py')):
            return 'python'
        elif os.path.exists(os.path.join(path, 'platformio.ini')):
            return 'platformio'
        elif os.path.exists(os.path.join(path, '*.ino')):
            return 'arduino'
        else:
            return 'unknown'
    
    def _find_source_files(self, path: str) -> List[str]:
        """Find source files in project"""
        
        source_files = []
        extensions = ['.py', '.js', '.cpp', '.c', '.h', '.ino', '.ts', '.jsx']
        
        try:
            for root, dirs, files in os.walk(path):
                # Skip common directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'venv', '.pytest_cache']]
                
                for file in files:
                    if any(file.endswith(ext) for ext in extensions):
                        source_files.append(os.path.join(root, file))
        except:
            pass
        
        return source_files[:50]  # Limit to 50 files
    
    def _extract_dependencies(self, path: str) -> List[str]:
        """Extract project dependencies"""
        
        dependencies = []
        
        # Python
        req_file = os.path.join(path, 'requirements.txt')
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r') as f:
                    dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except:
                pass
        
        # JavaScript
        package_file = os.path.join(path, 'package.json')
        if os.path.exists(package_file):
            try:
                import json
                with open(package_file, 'r') as f:
                    data = json.load(f)
                    deps = list(data.get('dependencies', {}).keys())
                    dev_deps = list(data.get('devDependencies', {}).keys())
                    dependencies = deps + dev_deps
            except:
                pass
        
        return dependencies[:20]  # Limit to 20 dependencies
    
    def _detect_test_framework(self, path: str) -> Optional[str]:
        """Detect testing framework"""
        
        # Check for pytest
        if os.path.exists(os.path.join(path, 'pytest.ini')) or \
           os.path.exists(os.path.join(path, 'tests')):
            return 'pytest'
        
        # Check for jest
        package_file = os.path.join(path, 'package.json')
        if os.path.exists(package_file):
            try:
                import json
                with open(package_file, 'r') as f:
                    data = json.load(f)
                    if 'jest' in data.get('devDependencies', {}):
                        return 'jest'
            except:
                pass
        
        return None
    
    def _generate_readme(self, params: Dict, context: Dict) -> Dict:
        """Generate README.md"""
        
        project_info = context.get('project_info', {})
        project_name = os.path.basename(os.getcwd())
        
        readme = f"""# {project_name}

## Overview

[Brief description of the project]

## Features

- Feature 1
- Feature 2
- Feature 3

## Installation

### Prerequisites

- Python 3.8+ (or specify your requirements)
- [List other dependencies]

### Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/{project_name}.git

# Navigate to project directory
cd {project_name}

# Install dependencies
"""
        
        if project_info.get('type') == 'python':
            readme += """pip install -r requirements.txt
```

## Usage
```python
# Example usage
from {package_name} import main

main()
```
"""
        elif project_info.get('type') == 'javascript':
            readme += """npm install
            
// Example usage
const app = require('./{project_name}');

app.run();
```
"""
        else:
            readme += """# Install project-specific dependencies
```

## Usage

[Provide usage examples]
"""
        
        if project_info.get('has_tests'):
            readme += f"""
## Testing

Run the test suite:
```bash
"""
            if project_info.get('test_framework') == 'pytest':
                readme += """pytest
```
"""
            elif project_info.get('test_framework') == 'jest':
                readme += """npm test
```
"""
            else:
                readme += """# Run tests
```
"""
        
        readme += """
## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[Specify license]

## Contact

[Your contact information]
"""
        
        return {
            'file': 'README.md',
            'content': readme,
            'lines': len(readme.split('\n'))
        }
    
    def _generate_architecture(self, params: Dict, context: Dict) -> Dict:
        """Generate ARCHITECTURE.md"""
        
        project_info = context.get('project_info', {})
        
        architecture = """# Architecture

## Overview

This document describes the high-level architecture of the project.

## Components

### Core Components

- **Component 1**: [Description]
- **Component 2**: [Description]
- **Component 3**: [Description]

### Data Flow
```
[Input] -> [Processing] -> [Output]
```

## Design Decisions

### Technology Choices

- **Language**: [Chosen language and why]
- **Framework**: [If applicable]
- **Database**: [If applicable]

### Patterns Used

- [Design pattern 1]
- [Design pattern 2]

## Directory Structure
```
project/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
└── README.md      # Project overview
```

## Future Improvements

- [ ] Improvement 1
- [ ] Improvement 2
- [ ] Improvement 3
"""
        
        return {
            'file': 'ARCHITECTURE.md',
            'content': architecture,
            'lines': len(architecture.split('\n'))
        }
    
    def _generate_api_docs(self, params: Dict, context: Dict) -> Dict:
        """Generate API documentation"""
        
        api_docs = """# API Documentation

## Endpoints

### GET /api/resource

Retrieves a resource.

**Parameters:**
- `id` (required): Resource ID

**Response:**
```json
{
  "id": 1,
  "data": "..."
}
```

### POST /api/resource

Creates a new resource.

**Body:**
```json
{
  "name": "Resource name",
  "data": "..."
}
```

**Response:**
```json
{
  "id": 2,
  "status": "created"
}
```

## Error Codes

- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Server Error
"""
        
        return {
            'file': 'API.md',
            'content': api_docs,
            'lines': len(api_docs.split('\n'))
        }
    
    def _generate_examples(self, params: Dict, context: Dict) -> Dict:
        """Generate usage examples"""
        
        examples = """# Examples

## Basic Usage
```python
# Example 1: Basic operation
from project import main

result = main.process_data(input_data)
print(result)
```

## Advanced Usage
```python
# Example 2: Advanced configuration
from project import advanced

config = {
    'option1': True,
    'option2': 'value'
}

result = advanced.run(config)
```

## Common Patterns

### Pattern 1: Error Handling
```python
try:
    result = operation()
except Exception as e:
    handle_error(e)
```

### Pattern 2: Async Operations
```python
import asyncio

async def main():
    result = await async_operation()
    return result

asyncio.run(main())
```
"""
        
        return {
            'file': 'EXAMPLES.md',
            'content': examples,
            'lines': len(examples.split('\n'))
        }
    
    def _generate_contributing(self, params: Dict, context: Dict) -> Dict:
        """Generate CONTRIBUTING.md"""
        
        contributing = """# Contributing

Thank you for considering contributing to this project!

## How to Contribute

### Reporting Bugs

- Use the issue tracker
- Describe the bug clearly
- Include steps to reproduce
- Provide system information

### Suggesting Features

- Open an issue with the "enhancement" label
- Describe the feature and its benefits
- Consider implementation details

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/project.git

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest
```

## Code Style

- Follow PEP 8 (Python) or appropriate style guide
- Write descriptive variable names
- Add comments for complex logic
- Write tests for new features

## Testing

- Write unit tests for new code
- Ensure all tests pass
- Aim for >80% code coverage

## Code Review

- Be respectful and constructive
- Address all feedback
- Keep pull requests focused

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
"""
        
        return {
            'file': 'CONTRIBUTING.md',
            'content': contributing,
            'lines': len(contributing.split('\n'))
        }