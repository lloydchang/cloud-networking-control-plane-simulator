# export_vpc_static_fully_offline.py
import json
import os
import re
import requests
import sys
import base64
from bs4 import BeautifulSoup

API_BASE_URL = "http://localhost:8000"
TEMPLATE_PATH = "control-plane/api/ui/vpc.html"
OUTPUT_DIR = "docs"

# Scenario-specific scripts relative to TEMPLATE_PATH
SCENARIO_SCRIPTS = [
    "scripts/scenario_hybrid.js",
    "scripts/scenario_vpn.js",
    "scripts/scenario_mesh.js"
]

def fetch_remote_resource(url):
    """Fetch remote JS or CSS content from a URL."""
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Warning: Could not fetch {url}: {e}")
        return None

def wrap_scenario_script(content, func_name):
    """
    Wrap scenario JS code in a window function to expose globally.
    func_name: renderScenarioHybrid / renderScenarioVPN / renderScenarioMesh
    """
    return f"window.{func_name} = function(...args) {{\n{content}\n}};"

def extract_coverage_from_testing_md():
    """Extract coverage information from TESTING.md"""
    testing_md_path = "docs/TESTING.md"
    if not os.path.exists(testing_md_path):
        print(f"Warning: {testing_md_path} not found, using default coverage")
        return None
    
    try:
        with open(testing_md_path, 'r') as f:
            content = f.read()
        
        # Extract coverage table using regex
        coverage_pattern = r'\| `([^`]+)` \| (\d+)% \| ([^|]+) \|'
        matches = re.findall(coverage_pattern, content)
        
        if matches:
            coverage_data = {}
            for component, percentage, status in matches:
                coverage_data[component] = {
                    "percentage": int(percentage),
                    "status": status.strip()
                }
            
            # Extract overall coverage
            overall_match = re.search(r'\*\*Overall\*\* \| \*\*(\d+)%\*\*', content)
            if overall_match:
                coverage_data["overall"] = int(overall_match.group(1))
            
            return coverage_data
    except Exception as e:
        print(f"Error parsing TESTING.md: {e}")
        return None

def export_static_fully_offline():
    """Export a single-file static VPC dashboard with all JS/CSS inlined, local and remote."""

    # Fetch scenarios (with graceful fallback)
    scenarios = []
    try:
        response = requests.get(f"{API_BASE_URL}/scenarios")
        response.raise_for_status()
        scenarios = response.json()
    except Exception as e:
        print(f"Warning: Could not fetch scenarios from API ({e}), using default scenarios")
        scenarios = ["demo", "basic", "advanced"]  # Default scenarios

    # Fetch VPC data (with graceful fallback)
    vpc_data = {"nodes": [], "edges": [], "scenarios": scenarios}
    try:
        response = requests.get(f"{API_BASE_URL}/vpc", headers={"Accept": "application/json"})
        response.raise_for_status()
        vpc_data = response.json()
    except Exception as e:
        print(f"Warning: Could not fetch VPC data from API ({e}), using sample data")
        # Use sample data (same as before)
        vpc_data = {
            "nodes": [
                {
                    "id": "vpc-demo-1",
                    "type": "vpc",
                    "label": "Demo VPC",
                    "cidr": "10.0.0.0/16",
                    "region": "us-east-1",
                    "secondary_cidrs": ["10.1.0.0/16"],
                    "scenario": "demo",
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "edges": [
                {
                    "source": "vpc-demo-1",
                    "target": "leaf-1",
                    "type": "vpc-hosting"
                },
                {
                    "source": "vpc-demo-1", 
                    "target": "leaf-2",
                    "type": "vpc-hosting"
                }
            ],
            "scenarios": scenarios
        }

    # Read template
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    with open(TEMPLATE_PATH, 'r') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    template_dir = os.path.dirname(TEMPLATE_PATH)

    # Inject JSON data first
    data_script = soup.new_tag("script")
    data_script.string = (
        f"window.STATIC_VPC_DATA = {json.dumps(vpc_data)};\n"
        f"window.STATIC_SCENARIOS = {json.dumps(scenarios)};"
    )
    soup.head.insert(0, data_script)

    # Find the main vpc.js script tag to insert scenario functions before it
    main_script_tag = None
    for script_tag in soup.find_all("script"):
        src = script_tag.get("src", "")
        if "vpc.js" in src:
            main_script_tag = script_tag
            break

    # Inline scenario-specific scripts and wrap as window functions
    for path in SCENARIO_SCRIPTS:
        full_path = os.path.join(template_dir, path)
        func_name = os.path.splitext(os.path.basename(path))[0].replace("scenario_", "renderScenario")
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
            tag = soup.new_tag("script")
            tag.string = wrap_scenario_script(content, func_name)
            if main_script_tag:
                main_script_tag.insert_before(tag)
            else:
                soup.head.append(tag)
        else:
            print(f"Warning: scenario script {path} not found")

    # Inline all other JS scripts
    for script_tag in soup.find_all("script"):
        src = script_tag.get("src")
        if src:
            # Skip scenario scripts since already inlined
            if any(src.endswith(os.path.basename(s)) for s in SCENARIO_SCRIPTS):
                continue
            if src.startswith(("http://", "https://", "//")):
                url = src if src.startswith("http") else "https:" + src
                content = fetch_remote_resource(url)
                if content:
                    script_tag.string = content
                    del script_tag["src"]
            else:
                src_path = os.path.join(template_dir, src)
                if os.path.exists(src_path):
                    with open(src_path, 'r') as f:
                        script_tag.string = f.read()
                    del script_tag["src"]
                else:
                    print(f"Warning: local JS file {src} not found, leaving src as-is.")

    # Inline CSS links
    for link_tag in soup.find_all("link", rel="stylesheet"):
        href = link_tag.get("href")
        if href:
            if href.startswith(("http://", "https://", "//")):
                url = href if href.startswith("http") else "https:" + href
                content = fetch_remote_resource(url)
                if content:
                    style_tag = soup.new_tag("style")
                    style_tag.string = content
                    link_tag.replace_with(style_tag)
            else:
                href_path = os.path.join(template_dir, href)
                if os.path.exists(href_path):
                    with open(href_path, 'r') as f:
                        style_tag = soup.new_tag("style")
                        style_tag.string = f.read()
                    link_tag.replace_with(style_tag)
                else:
                    print(f"Warning: local CSS file {href} not found, leaving link as-is.")

    # Fix logo path for GitHub Pages
    logo_img = soup.find("img", {"class": "logo"})
    if logo_img:
        logo_src = logo_img.get("src")
        if logo_src and logo_src.startswith("/ui/"):
            # Try to inline the SVG
            logo_path = os.path.join(template_dir, logo_src[1:])  # Remove leading /
            if os.path.exists(logo_path):
                with open(logo_path, 'r') as f:
                    svg_content = f.read()
                # Create a new img tag with inline SVG
                logo_img['src'] = f"data:image/svg+xml;base64,{base64.b64encode(svg_content.encode()).decode()}"
                print(f"Inlined logo: {logo_path}")
            else:
                # Fallback to docs path for GitHub Pages
                logo_img['src'] = logo_src.replace("/ui/", "/")
                print(f"Updated logo path for GitHub Pages: {logo_img['src']}")

    # Extract coverage from TESTING.md and inject into HTML
    coverage_data = extract_coverage_from_testing_md()
    if coverage_data:
        # Find the coverage section in the HTML and update it
        coverage_section = soup.find("strong", string=lambda text: text and "Current Coverage:" in text)
        if coverage_section and coverage_section.parent:
            # Build new coverage HTML
            coverage_html = "<strong>Current Coverage (as of commit 3c0c98f):</strong><br/>"
            for component, data in coverage_data.items():
                if component == "overall":
                    coverage_html += f"• <strong>Overall: {data}% 📈 (was 35%)</strong><br/>"
                else:
                    coverage_html += f"• {component}: {data['percentage']}% {data['status']}<br/>"
            coverage_html += "<br/><em>Uncovered: Database initialization, entry points, some gRPC methods</em>"
            
            # Update the div content by replacing the entire div
            coverage_div = coverage_section.parent
            new_div = soup.new_tag("div", style=coverage_div.get("style", ""))
            new_div.append(BeautifulSoup(coverage_html, "html.parser"))
            coverage_div.replace_with(new_div)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "index.html")

    with open(output_path, 'w') as f:
        f.write(str(soup))

    print(f"Fully offline static dashboard written to {os.path.abspath(output_path)}")
    print(f"Contains {len(scenarios)} scenarios, all JS/CSS inlined (local + remote).")
    if coverage_data:
        print(f"Updated coverage from TESTING.md: {coverage_data.get('overall', 'N/A')}% overall")

if __name__ == "__main__":
    export_static_fully_offline()
