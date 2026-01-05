
import pytest
from pathlib import Path
import re

# Paths
CONTROL_PLANE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = CONTROL_PLANE_DIR.parent
DOCS_DIR = PROJECT_ROOT / "docs"
VPC_HTML_PATH = CONTROL_PLANE_DIR / "api" / "ui" / "vpc.html"
INDEX_HTML_PATH = DOCS_DIR / "index.html"

def test_vpc_html_tab_consistency():
    """Verify vpc.html tabs follow 'Title ... from docs/FILENAME.md' pattern."""
    assert VPC_HTML_PATH.exists(), "vpc.html not found"
    content = VPC_HTML_PATH.read_text(encoding="utf-8")
    
    # Define expected patterns for tabs
    expected_patterns = [
        r"<h3>🏗️ System Architecture</h3>\s*<p>Conceptual exploration of cloud networking internals from docs/ARCHITECTURE\.md</p>",
        r"<h3>🌐 VPC Architecture & Visualization</h3>\s*<p>Real-time logical map of your cloud network with 36 demo scenarios from docs/VPC\.md</p>",
        r"<h3>📚 API Usage Examples</h3>\s*<p>Comprehensive API examples and use cases from docs/API_EXAMPLES\.md</p>",
        r"<h3>🧪 Testing & Performance</h3>\s*<p>Multi-layered testing approach ensuring control plane correctness and reliability from\s*docs/TESTING\.md</p>"
    ]
    
    for pattern in expected_patterns:
        assert re.search(pattern, content), f"Pattern not found in vpc.html: {pattern}"

def test_index_html_consistency():
    """Verify generated index.html matches requirements."""
    assert INDEX_HTML_PATH.exists(), "docs/index.html not found - run generate_site.py"
    content = INDEX_HTML_PATH.read_text(encoding="utf-8")
    
    # Check for License standardization
    assert "AGPL-3.0 license from LICENSE" in content, "License description mismatch"
    
    # Check for removal of outdated text and presence of correct text
    assert "33 demo scenarios" not in content, "Outdated '33 demo scenarios' text found"
    assert "36 demo scenarios" in content, "Correct '36 demo scenarios' text not found"
    
    # Check for specific tab headers
    assert "API Usage Examples" in content
    assert "from docs/API_EXAMPLES.md" in content

if __name__ == "__main__":
    pytest.main([__file__])
