# export_vpc_static_fully_offline.py
import json
import os
import requests
import sys
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

def export_static_fully_offline():
    """Export a single-file static VPC dashboard with all JS/CSS inlined, local and remote."""

    # Fetch scenarios
    try:
        response = requests.get(f"{API_BASE_URL}/scenarios")
        response.raise_for_status()
        scenarios = response.json()
    except Exception as e:
        print(f"Error fetching scenarios: {e}")
        sys.exit(1)

    # Fetch VPC data
    try:
        response = requests.get(f"{API_BASE_URL}/vpc", headers={"Accept": "application/json"})
        response.raise_for_status()
        vpc_data = response.json()
    except Exception as e:
        print(f"Error fetching VPC data: {e}")
        sys.exit(1)
    
    # Smart fallback: If no VPCs exist, use sample data instead of empty
    if not vpc_data.get("nodes") or not vpc_data.get("nodes", []):
        print("No VPCs found in database, using sample data for demo")
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
            "scenarios": ["demo"]
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

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "index.html")

    with open(output_path, 'w') as f:
        f.write(str(soup))

    print(f"Fully offline static dashboard written to {os.path.abspath(output_path)}")
    print(f"Contains {len(scenarios)} scenarios, all JS/CSS inlined (local + remote).")

if __name__ == "__main__":
    export_static_fully_offline()
