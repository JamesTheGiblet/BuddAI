"""
HTML Language Skill
Semantic HTML5, accessibility, SEO, and best practices
"""

import re
from typing import Dict, List, Optional
from .language_base import LanguageSkill

class HTMLSkill(LanguageSkill):
    """
    HTML5 language skill
    
    Provides:
    - Semantic HTML patterns
    - Accessibility validation (ARIA, alt text)
    - SEO best practices
    - Form validation patterns
    - Common layouts
    - Anti-pattern detection
    """
    
    def __init__(self):
        super().__init__(
            name="HTML",
            file_extensions=['.html', '.htm']
        )
    
    def _load_patterns(self):
        """Load HTML patterns and best practices"""
        
        # Semantic HTML patterns
        self.patterns = {
            'semantic_structure': {
                'description': 'Use semantic HTML5 elements',
                'pattern': r'<(header|nav|main|article|section|aside|footer)',
                'example': '<header>\n  <nav>...</nav>\n</header>\n<main>\n  <article>...</article>\n</main>\n<footer>...</footer>'
            },
            'accessible_images': {
                'description': 'Images must have alt text',
                'pattern': r'<img[^>]+alt=["\'][^"\']*["\']',
                'example': '<img src="photo.jpg" alt="Descriptive text">'
            },
            'form_labels': {
                'description': 'Form inputs must have labels',
                'pattern': r'<label[^>]*>.*?<input',
                'example': '<label for="email">Email:</label>\n<input type="email" id="email" name="email">'
            },
            'meta_tags': {
                'description': 'Include meta tags for SEO',
                'pattern': r'<meta\s+name=["\'](?:description|viewport|keywords)["\']',
                'example': '<meta name="description" content="Page description">\n<meta name="viewport" content="width=device-width, initial-scale=1">'
            },
            'heading_hierarchy': {
                'description': 'Use proper heading hierarchy',
                'pattern': r'<h[1-6]>',
                'example': '<h1>Main Title</h1>\n<h2>Section</h2>\n<h3>Subsection</h3>'
            }
        }
        
        # Anti-patterns to avoid
        self.anti_patterns = {
            'divitis': {
                'description': 'Excessive div nesting (use semantic elements)',
                'pattern': r'<div[^>]*>\s*<div[^>]*>\s*<div[^>]*>\s*<div',
                'fix': 'Use semantic elements like <section>, <article>, <header>'
            },
            'missing_alt': {
                'description': 'Images without alt attributes',
                'pattern': r'<img(?![^>]*alt=)',
                'fix': 'Add alt="" for decorative images or alt="description" for content images'
            },
            'inline_styles': {
                'description': 'Inline styles (use CSS classes)',
                'pattern': r'style=["\'][^"\']+["\']',
                'fix': 'Move styles to CSS file and use classes'
            },
            'missing_doctype': {
                'description': 'Missing DOCTYPE declaration',
                'pattern': r'^(?!<!DOCTYPE html>)',
                'fix': 'Add <!DOCTYPE html> at the top of the file'
            },
            'deprecated_tags': {
                'description': 'Using deprecated HTML tags',
                'pattern': r'<(font|center|marquee|blink|big|strike)',
                'fix': 'Use CSS for styling instead'
            }
        }
        
        # Best practices
        self.best_practices = [
            'Use semantic HTML5 elements (header, nav, main, article, section, aside, footer)',
            'Always include alt text on images for accessibility',
            'Use label elements for form inputs',
            'Include meta description and viewport tags',
            'Maintain proper heading hierarchy (h1 -> h2 -> h3)',
            'Use ARIA attributes for enhanced accessibility',
            'Validate forms with HTML5 validation attributes',
            'Keep markup clean and readable with proper indentation',
            'Separate structure (HTML) from presentation (CSS)',
            'Use semantic class names that describe content, not appearance'
        ]
    
    def validate(self, code: str) -> Dict:
        """
        Validate HTML code
        
        Checks for:
        - Missing DOCTYPE
        - Missing alt text on images
        - Non-semantic structure
        - Deprecated tags
        - Accessibility issues
        """
        
        issues = []
        warnings = []
        suggestions = []
        
        # Check for DOCTYPE
        if not re.search(r'<!DOCTYPE html>', code, re.IGNORECASE):
            issues.append('Missing DOCTYPE declaration')
        
        # Check for images without alt
        img_tags = re.findall(r'<img[^>]*>', code)
        for img in img_tags:
            if 'alt=' not in img:
                issues.append(f'Image missing alt attribute: {img[:50]}...')
        
        # Check for deprecated tags
        for tag_name, info in self.anti_patterns.items():
            if tag_name == 'deprecated_tags':
                matches = re.findall(info['pattern'], code)
                if matches:
                    issues.append(f'Using deprecated tag(s): {", ".join(set(matches))}')
        
        # Check for semantic structure
        has_semantic = bool(re.search(self.patterns['semantic_structure']['pattern'], code))
        div_count = len(re.findall(r'<div', code))
        
        if div_count > 5 and not has_semantic:
            warnings.append('Consider using semantic HTML5 elements instead of divs')
        
        # Check for inline styles
        inline_styles = re.findall(r'style=["\'][^"\']+["\']', code)
        if len(inline_styles) > 3:
            warnings.append(f'Found {len(inline_styles)} inline styles - consider using CSS classes')
        
        # Check for heading hierarchy
        headings = re.findall(r'<h([1-6])>', code)
        if headings:
            h_numbers = [int(h) for h in headings]
            if h_numbers and min(h_numbers) > 1:
                suggestions.append('Start with <h1> for the main heading')
        
        # Check for meta tags
        has_viewport = bool(re.search(r'<meta[^>]*name=["\']viewport["\']', code))
        if not has_viewport and '<html' in code:
            suggestions.append('Add viewport meta tag for responsive design')
        
        # Check for form labels
        inputs = re.findall(r'<input[^>]*>', code)
        labels = re.findall(r'<label[^>]*>', code)
        if len(inputs) > len(labels):
            warnings.append('Some form inputs may be missing labels')
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions
        }
    
    def get_template(self, template_name: str) -> Optional[str]:
        """Get HTML template by name"""
        
        templates = {
            'basic': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="">
    <title>Document</title>
</head>
<body>
    <header>
        <nav>
            <!-- Navigation -->
        </nav>
    </header>
    
    <main>
        <article>
            <h1>Main Heading</h1>
            <!-- Content -->
        </article>
    </main>
    
    <footer>
        <!-- Footer content -->
    </footer>
</body>
</html>''',
            
            'form': '''<form action="/submit" method="post">
    <div>
        <label for="name">Name:</label>
        <input type="text" id="name" name="name" required>
    </div>
    
    <div>
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required>
    </div>
    
    <div>
        <label for="message">Message:</label>
        <textarea id="message" name="message" rows="5" required></textarea>
    </div>
    
    <button type="submit">Submit</button>
</form>''',
            
            'article': '''<article>
    <header>
        <h1>Article Title</h1>
        <p class="byline">
            By <span class="author">Author Name</span> on 
            <time datetime="2026-01-10">January 10, 2026</time>
        </p>
    </header>
    
    <section>
        <h2>Section Heading</h2>
        <p>Content goes here...</p>
    </section>
    
    <footer>
        <p>Tags: <a href="#">tag1</a>, <a href="#">tag2</a></p>
    </footer>
</article>''',
            
            'landing_page': '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Your product description">
    <title>Product Name - Tagline</title>
</head>
<body>
    <header>
        <nav>
            <a href="#features">Features</a>
            <a href="#pricing">Pricing</a>
            <a href="#contact">Contact</a>
        </nav>
    </header>
    
    <main>
        <section class="hero">
            <h1>Compelling Headline</h1>
            <p>Supporting description that explains the value</p>
            <a href="#" class="cta">Get Started</a>
        </section>
        
        <section id="features">
            <h2>Features</h2>
            <div class="feature-grid">
                <article class="feature">
                    <h3>Feature 1</h3>
                    <p>Description</p>
                </article>
                <!-- More features -->
            </div>
        </section>
        
        <section id="pricing">
            <h2>Pricing</h2>
            <!-- Pricing content -->
        </section>
    </main>
    
    <footer>
        <p>&copy; 2026 Company Name</p>
    </footer>
</body>
</html>'''
        }
        
        return templates.get(template_name)
    
    def get_accessibility_checklist(self) -> List[str]:
        """Get accessibility checklist for HTML"""
        return [
            '✓ All images have descriptive alt text',
            '✓ Form inputs have associated labels',
            '✓ Proper heading hierarchy (h1 > h2 > h3)',
            '✓ ARIA labels for interactive elements',
            '✓ Semantic HTML5 elements used',
            '✓ Keyboard navigation works',
            '✓ Color contrast meets WCAG standards',
            '✓ Links have descriptive text (no "click here")',
            '✓ Tables have proper headers',
            '✓ Language attribute set on <html>'
        ]
    
    def get_seo_checklist(self) -> List[str]:
        """Get SEO checklist for HTML"""
        return [
            '✓ Descriptive title tag (50-60 characters)',
            '✓ Meta description (150-160 characters)',
            '✓ One h1 tag per page',
            '✓ Semantic HTML structure',
            '✓ Image alt text for context',
            '✓ Clean, descriptive URLs',
            '✓ Internal linking structure',
            '✓ Mobile-friendly (viewport meta tag)',
            '✓ Fast loading time',
            '✓ Valid HTML (no errors)'
        ]