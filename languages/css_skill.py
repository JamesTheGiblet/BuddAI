"""
CSS Language Skill
Modern CSS, Flexbox, Grid, responsive design, and best practices
"""

import re
from typing import Dict, List, Optional

from .language_base import LanguageSkill

class CSSSkill(LanguageSkill):
    """
    CSS3 language skill
    
    Provides:
    - Modern CSS patterns (Flexbox, Grid)
    - Responsive design principles
    - Animation best practices
    - Performance optimization
    - Cross-browser compatibility
    - Anti-pattern detection
    """
    
    def __init__(self):
        super().__init__(
            name="CSS",
            file_extensions=['.css', '.scss', '.sass', '.less']
        )
    
    def _load_patterns(self):
        """Load CSS patterns and best practices"""
        
        # Modern CSS patterns
        self.patterns = {
            'flexbox': {
                'description': 'Flexbox layout patterns',
                'pattern': r'display:\s*flex',
                'example': '.container {\n  display: flex;\n  justify-content: space-between;\n  align-items: center;\n}'
            },
            'grid': {
                'description': 'CSS Grid layout patterns',
                'pattern': r'display:\s*grid',
                'example': '.grid {\n  display: grid;\n  grid-template-columns: repeat(3, 1fr);\n  gap: 1rem;\n}'
            },
            'custom_properties': {
                'description': 'CSS custom properties (variables)',
                'pattern': r'--[\w-]+:\s*[^;]+',
                'example': ':root {\n  --primary-color: #007bff;\n  --spacing: 1rem;\n}'
            },
            'media_queries': {
                'description': 'Responsive media queries',
                'pattern': r'@media\s*\([^)]+\)',
                'example': '@media (min-width: 768px) {\n  .container { max-width: 960px; }\n}'
            },
            'animations': {
                'description': 'CSS animations and transitions',
                'pattern': r'(animation|transition):\s*[^;]+',
                'example': '.fade {\n  transition: opacity 0.3s ease;\n}\n@keyframes slide {\n  from { transform: translateX(-100%); }\n  to { transform: translateX(0); }\n}'
            },
            'pseudo_elements': {
                'description': 'Pseudo-elements for enhanced styling',
                'pattern': r'::(before|after)',
                'example': '.card::before {\n  content: "";\n  display: block;\n}'
            }
        }
        
        # Anti-patterns to avoid
        self.anti_patterns = {
            'important_overuse': {
                'description': 'Excessive use of !important',
                'pattern': r'!important',
                'fix': 'Increase selector specificity instead of using !important'
            },
            'absolute_units': {
                'description': 'Using absolute units (px) for font sizes',
                'pattern': r'font-size:\s*\d+px',
                'fix': 'Use relative units (rem, em) for better accessibility'
            },
            'float_layout': {
                'description': 'Using floats for layout (outdated)',
                'pattern': r'float:\s*(left|right)',
                'fix': 'Use Flexbox or Grid for modern layouts'
            },
            'inline_styles_in_css': {
                'description': 'Overly specific selectors',
                'pattern': r'[#\.][\w-]+\s+[#\.][\w-]+\s+[#\.][\w-]+\s+[#\.][\w-]+',
                'fix': 'Reduce selector specificity for maintainability'
            },
            'vendor_prefixes_manual': {
                'description': 'Manual vendor prefixes (use autoprefixer)',
                'pattern': r'-webkit-|-moz-|-ms-|-o-',
                'fix': 'Use autoprefixer tool instead of manual prefixes'
            },
            'magic_numbers': {
                'description': 'Magic numbers without context',
                'pattern': r':\s*\d+\.\d+px',
                'fix': 'Use custom properties to document magic numbers'
            }
        }
        
        # Best practices
        self.best_practices = [
            'Use Flexbox or Grid for layouts instead of floats',
            'Use relative units (rem, em, %) for responsive design',
            'Implement mobile-first responsive design with media queries',
            'Use CSS custom properties for theming and reusability',
            'Minimize use of !important (prefer specificity)',
            'Use semantic class names (BEM methodology)',
            'Optimize animations (use transform and opacity for performance)',
            'Use shorthand properties where appropriate',
            'Group related properties together',
            'Use autoprefixer instead of manual vendor prefixes',
            'Implement consistent spacing with custom properties',
            'Use CSS Grid for 2D layouts, Flexbox for 1D layouts'
        ]
    
    def validate(self, code: str) -> Dict:
        """
        Validate CSS code
        
        Checks for:
        - Excessive !important usage
        - Absolute font sizes
        - Outdated layout methods
        - Missing modern features
        - Performance issues
        """
        
        issues = []
        warnings = []
        suggestions = []
        
        # Check for excessive !important
        important_count = len(re.findall(r'!important', code))
        if important_count > 5:
            warnings.append(f'Excessive use of !important ({important_count} times) - consider refactoring specificity')
        
        # Check for absolute font sizes
        absolute_fonts = re.findall(r'font-size:\s*\d+px', code)
        if len(absolute_fonts) > 3:
            warnings.append(f'Using absolute font sizes (px) - consider using rem or em for accessibility')
        
        # Check for float-based layouts
        float_count = len(re.findall(r'float:\s*(left|right)', code))
        if float_count > 2:
            suggestions.append('Consider using Flexbox or Grid instead of floats for layout')
        
        # Check for modern layout usage
        has_flexbox = bool(re.search(r'display:\s*flex', code))
        has_grid = bool(re.search(r'display:\s*grid', code))
        
        if not has_flexbox and not has_grid and len(code) > 200:
            suggestions.append('Consider using modern layout methods (Flexbox or Grid)')
        
        # Check for responsive design
        has_media_queries = bool(re.search(r'@media', code))
        if len(code) > 300 and not has_media_queries:
            suggestions.append('Add media queries for responsive design')
        
        # Check for CSS variables
        has_variables = bool(re.search(r'--[\w-]+:', code))
        if len(code) > 500 and not has_variables:
            suggestions.append('Consider using CSS custom properties for better maintainability')
        
        # Check for overly specific selectors
        overly_specific = re.findall(r'[#\.][\w-]+\s+[#\.][\w-]+\s+[#\.][\w-]+\s+[#\.][\w-]+', code)
        if overly_specific:
            warnings.append(f'Found {len(overly_specific)} overly specific selectors - reduce specificity')
        
        # Check for vendor prefixes
        vendor_prefixes = re.findall(r'-webkit-|-moz-|-ms-|-o-', code)
        if len(vendor_prefixes) > 5:
            suggestions.append('Consider using autoprefixer instead of manual vendor prefixes')
        
        # Check for animation performance
        bad_animations = re.findall(r'(animation|transition):[^;]*(width|height|left|top|margin|padding)', code)
        if bad_animations:
            warnings.append('Avoid animating layout properties (width, height, position) - use transform instead')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def get_template(self, template_name: str) -> Optional[str]:
        """Get CSS template by name"""
        
        templates = {
            'reset': '''/* Modern CSS Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  line-height: 1.6;
  color: #333;
}

img, picture, video, canvas, svg {
  display: block;
  max-width: 100%;
}

input, button, textarea, select {
  font: inherit;
}''',
            
            'flexbox_layout': '''.container {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.flex-item {
  flex: 1 1 300px;
}

/* Responsive */
@media (max-width: 768px) {
  .container {
    flex-direction: column;
  }
}''',
            
            'grid_layout': '''.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
  padding: 2rem;
}

.grid-item {
  background: #fff;
  border-radius: 8px;
  padding: 1.5rem;
}

/* Responsive grid */
@media (min-width: 768px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}''',
            
            'variables': ''':root {
  /* Colors */
  --primary: #007bff;
  --secondary: #6c757d;
  --success: #28a745;
  --danger: #dc3545;
  --warning: #ffc107;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 2rem;
  --spacing-xl: 4rem;
  
  /* Typography */
  --font-size-sm: 0.875rem;
  --font-size-base: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
  
  /* Borders */
  --border-radius: 0.25rem;
  --border-width: 1px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.15);
}

.button {
  background: var(--primary);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-sm);
}''',
            
            'animations': '''/* Fade in animation */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

/* Smooth transitions */
.transition {
  transition: all 0.3s ease;
}

.button {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* Performant animations (use transform and opacity) */
.slide-in {
  animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideIn {
  from {
    transform: translateX(-100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}''',
            
            'responsive': '''/* Mobile-first approach */
.container {
  width: 100%;
  padding: 1rem;
}

/* Tablet */
@media (min-width: 768px) {
  .container {
    max-width: 720px;
    margin: 0 auto;
    padding: 1.5rem;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .container {
    max-width: 960px;
    padding: 2rem;
  }
}

/* Large desktop */
@media (min-width: 1280px) {
  .container {
    max-width: 1200px;
  }
}

/* Responsive typography */
html {
  font-size: 14px;
}

@media (min-width: 768px) {
  html {
    font-size: 16px;
  }
}

@media (min-width: 1024px) {
  html {
    font-size: 18px;
  }
}'''
        }
        
        return templates.get(template_name)
    
    def get_performance_tips(self) -> List[str]:
        """Get CSS performance optimization tips"""
        return [
            '✓ Animate transform and opacity (GPU-accelerated)',
            '✓ Avoid animating width, height, position, margin, padding',
            '✓ Use will-change for animations (sparingly)',
            '✓ Minimize repaints and reflows',
            '✓ Use CSS containment (contain property)',
            '✓ Optimize selector performance (avoid deep nesting)',
            '✓ Use CSS Grid for complex layouts',
            '✓ Lazy load non-critical CSS',
            '✓ Minimize use of expensive properties (box-shadow, filters)',
            '✓ Use transform: translate() instead of position changes'
        ]
    
    def get_responsive_breakpoints(self) -> Dict:
        """Get standard responsive breakpoints"""
        return {
            'mobile': '0px - 767px',
            'tablet': '768px - 1023px',
            'desktop': '1024px - 1279px',
            'large_desktop': '1280px+',
            'common_breakpoints': {
                'sm': '640px',
                'md': '768px',
                'lg': '1024px',
                'xl': '1280px',
                '2xl': '1536px'
            }
        }
    
    def get_modern_features(self) -> List[str]:
        """Get list of modern CSS features to use"""
        return [
            'CSS Grid for 2D layouts',
            'Flexbox for 1D layouts',
            'CSS Custom Properties (variables)',
            'CSS Container Queries',
            'CSS Subgrid',
            'CSS Logical Properties',
            'CSS :has() selector',
            'CSS @layer for cascade control',
            'CSS aspect-ratio property',
            'CSS clamp() for responsive sizing',
            'CSS min(), max() functions',
            'CSS :is() and :where() selectors'
        ]