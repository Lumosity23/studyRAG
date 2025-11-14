"""
Tests for frontend components and static files.
"""

import os
import pytest
from pathlib import Path


class TestStaticFiles:
    """Test static file structure and content."""
    
    def test_static_directory_exists(self):
        """Test that static directory exists."""
        static_dir = Path("static")
        assert static_dir.exists(), "Static directory should exist"
        assert static_dir.is_dir(), "Static should be a directory"
    
    def test_index_html_exists(self):
        """Test that index.html exists and has required content."""
        index_file = Path("static/index.html")
        assert index_file.exists(), "index.html should exist"
        
        content = index_file.read_text()
        
        # Check for required HTML structure
        assert "<!DOCTYPE html>" in content
        assert "<html lang=\"en\">" in content
        assert "<title>StudyRAG" in content
        assert "viewport" in content
        
        # Check for accessibility features
        assert "Skip to main content" in content
        assert "aria-" in content
        assert "role=" in content
        
        # Check for required CSS and JS files
        assert "/static/css/main.css" in content
        assert "/static/css/components.css" in content
        assert "/static/js/main.js" in content
        assert "/static/js/components.js" in content
        assert "/static/js/router.js" in content
        assert "/static/js/utils.js" in content
    
    def test_css_files_exist(self):
        """Test that CSS files exist and have basic content."""
        css_dir = Path("static/css")
        assert css_dir.exists(), "CSS directory should exist"
        
        main_css = css_dir / "main.css"
        components_css = css_dir / "components.css"
        
        assert main_css.exists(), "main.css should exist"
        assert components_css.exists(), "components.css should exist"
        
        # Check main.css content
        main_content = main_css.read_text()
        assert ":root" in main_content, "CSS variables should be defined"
        assert "@media" in main_content, "Responsive breakpoints should exist"
        assert "mobile-first" in main_content.lower() or "min-width" in main_content
        
        # Check components.css content
        components_content = components_css.read_text()
        assert ".btn" in components_content, "Button component should be defined"
        assert ".modal" in components_content, "Modal component should be defined"
        assert ".toast" in components_content, "Toast component should be defined"
        assert ".progress" in components_content, "Progress component should be defined"
    
    def test_js_files_exist(self):
        """Test that JavaScript files exist and have basic structure."""
        js_dir = Path("static/js")
        assert js_dir.exists(), "JS directory should exist"
        
        js_files = ["main.js", "components.js", "router.js", "utils.js"]
        
        for js_file in js_files:
            file_path = js_dir / js_file
            assert file_path.exists(), f"{js_file} should exist"
            
            content = file_path.read_text()
            assert "window.StudyRAG" in content, f"{js_file} should use StudyRAG namespace"
    
    def test_assets_directory(self):
        """Test that assets directory exists with required files."""
        assets_dir = Path("static/assets")
        assert assets_dir.exists(), "Assets directory should exist"
        
        favicon = assets_dir / "favicon.svg"
        assert favicon.exists(), "Favicon should exist"
        
        favicon_content = favicon.read_text()
        assert "<svg" in favicon_content, "Favicon should be valid SVG"
    
    def test_service_worker_exists(self):
        """Test that service worker exists."""
        sw_file = Path("static/sw.js")
        assert sw_file.exists(), "Service worker should exist"
        
        content = sw_file.read_text()
        assert "addEventListener" in content, "Service worker should have event listeners"
        assert "install" in content, "Service worker should handle install event"
        assert "fetch" in content, "Service worker should handle fetch event"


class TestResponsiveDesign:
    """Test responsive design features."""
    
    def test_css_has_responsive_breakpoints(self):
        """Test that CSS includes responsive breakpoints."""
        main_css = Path("static/css/main.css")
        content = main_css.read_text()
        
        # Check for common responsive breakpoints
        breakpoints = ["640px", "768px", "1024px"]
        for breakpoint in breakpoints:
            assert f"min-width: {breakpoint}" in content, f"Should have {breakpoint} breakpoint"
    
    def test_mobile_first_approach(self):
        """Test that CSS follows mobile-first approach."""
        main_css = Path("static/css/main.css")
        content = main_css.read_text()
        
        # Mobile-first means base styles are for mobile, then min-width media queries
        min_width_count = content.count("min-width:")
        max_width_count = content.count("max-width:")
        
        # Should have more min-width than max-width queries for mobile-first
        assert min_width_count > 0, "Should have min-width media queries"
        # Allow some max-width for specific cases, but min-width should dominate
        assert min_width_count >= max_width_count, "Should follow mobile-first approach"


class TestAccessibility:
    """Test accessibility features."""
    
    def test_html_has_accessibility_attributes(self):
        """Test that HTML includes proper accessibility attributes."""
        index_file = Path("static/index.html")
        content = index_file.read_text()
        
        # Check for ARIA attributes
        aria_attributes = ["aria-label", "aria-expanded", "aria-controls", "aria-live"]
        for attr in aria_attributes:
            assert attr in content, f"Should include {attr} for accessibility"
        
        # Check for semantic HTML
        semantic_elements = ["<nav", "<main", "<header", "<footer", "role="]
        for element in semantic_elements:
            assert element in content, f"Should include {element} for semantic structure"
        
        # Check for skip link
        assert "Skip to main content" in content, "Should have skip link"
    
    def test_css_has_focus_styles(self):
        """Test that CSS includes proper focus styles."""
        main_css = Path("static/css/main.css")
        content = main_css.read_text()
        
        assert ":focus" in content, "Should have focus styles"
        assert "outline:" in content, "Should define outline for focus"
    
    def test_css_supports_reduced_motion(self):
        """Test that CSS respects reduced motion preferences."""
        main_css = Path("static/css/main.css")
        content = main_css.read_text()
        
        assert "prefers-reduced-motion" in content, "Should respect reduced motion preference"


class TestComponentStructure:
    """Test component structure and functionality."""
    
    def test_components_js_has_required_components(self):
        """Test that components.js defines required UI components."""
        components_js = Path("static/js/components.js")
        content = components_js.read_text()
        
        required_components = ["Toast", "Modal", "ProgressBar", "FileUpload", "LoadingOverlay"]
        for component in required_components:
            assert component in content, f"Should define {component} component"
    
    def test_utils_js_has_utility_functions(self):
        """Test that utils.js provides utility functions."""
        utils_js = Path("static/js/utils.js")
        content = utils_js.read_text()
        
        utility_functions = ["debounce", "throttle", "formatFileSize", "formatDate"]
        for func in utility_functions:
            assert func in content, f"Should provide {func} utility function"
    
    def test_router_js_has_routing_functionality(self):
        """Test that router.js provides routing functionality."""
        router_js = Path("static/js/router.js")
        content = router_js.read_text()
        
        routing_features = ["register", "navigate", "handleRouteChange"]
        for feature in routing_features:
            assert feature in content, f"Should provide {feature} routing feature"


class TestFileIntegrity:
    """Test file integrity and structure."""
    
    def test_no_syntax_errors_in_js_files(self):
        """Test that JavaScript files don't have obvious syntax errors."""
        js_dir = Path("static/js")
        
        for js_file in js_dir.glob("*.js"):
            content = js_file.read_text()
            
            # Basic syntax checks
            open_braces = content.count("{")
            close_braces = content.count("}")
            assert open_braces == close_braces, f"{js_file.name} should have balanced braces"
            
            open_parens = content.count("(")
            close_parens = content.count(")")
            assert open_parens == close_parens, f"{js_file.name} should have balanced parentheses"
    
    def test_css_files_are_valid(self):
        """Test that CSS files have basic validity."""
        css_dir = Path("static/css")
        
        for css_file in css_dir.glob("*.css"):
            content = css_file.read_text()
            
            # Basic CSS syntax checks
            open_braces = content.count("{")
            close_braces = content.count("}")
            assert open_braces == close_braces, f"{css_file.name} should have balanced braces"
            
            # Should not have obvious syntax errors
            assert "undefined" not in content.lower(), f"{css_file.name} should not contain 'undefined'"
    
    def test_html_is_well_formed(self):
        """Test that HTML is well-formed."""
        index_file = Path("static/index.html")
        content = index_file.read_text()
        
        # Basic HTML structure checks - use more specific patterns to avoid comments
        assert content.count("<html") == content.count("</html>"), "HTML tags should be balanced"
        assert content.count("<head>") == content.count("</head>"), "Head tags should be balanced"
        assert content.count("<body") == content.count("</body>"), "Body tags should be balanced"
        
        # Required meta tags
        assert '<meta charset="UTF-8">' in content, "Should have charset meta tag"
        assert 'name="viewport"' in content, "Should have viewport meta tag"


if __name__ == "__main__":
    pytest.main([__file__])