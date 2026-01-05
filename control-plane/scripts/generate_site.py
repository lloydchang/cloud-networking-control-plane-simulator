#!/usr/bin/env python3
"""
Cloud Networking Control Plane Simulator - Static Site Generator

This script generates a fully-offline, portable 'docs/index.html' dashboard.
It inlines all CSS/JS resources and extracts scenario data from VPC.md.

Deployment Strategy:
1. Local: Generates docs/index.html for offline use or preview.
2. GitHub: docs/index.html is committed and served via GitHub Pages.
3. Vercel: FastAPI (rest_api_server.py) fetches and serves the raw index.html 
   from GitHub. This ensures the dashboard is always available at the root 
   domain without requiring manual Vercel builds for every small change.

Usage:
    python control-plane/scripts/generate_site.py
"""

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

def fetch_remote_resource(url):
    """Fetch remote JS or CSS content from a URL."""
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Warning: Could not fetch {url}: {e}")
        return None

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

def extract_coverage_from_testing_md_html():
    """Get coverage data formatted as a compact HTML block"""
    data = extract_coverage_from_testing_md()
    if not data:
        return None
        
    # Build new coverage HTML
    coverage_html = "<div style='font-size: 11px; line-height: 1.4; color: #444; border: 1px solid #eee; padding: 10px; border-radius: 4px; background: #fafafa; margin: 10px 0;'>"
    coverage_html += "<strong>Current Coverage (Baseline):</strong><br/>"
    for component, val in data.items():
        if component == "overall":
            coverage_html += f"• <strong>Overall: {val}% 📈</strong><br/>"
        else:
            coverage_html += f"• {component}: {val['percentage']}% {val['status']}<br/>"
    coverage_html += "<em>Uncovered: Database initialization and entry points</em></div>"
    
    return coverage_html

def preprocess_markdown(content):
    """Support GitHub-style alerts and other custom formatting before markdown conversion"""
    if not content:
        return content
        
    # Pattern for GitHub alerts: > [!TYPE]\n> Content
    # Types: NOTE, TIP, IMPORTANT, WARNING, CAUTION
    alert_types = {
        "NOTE": {"icon": "ℹ️", "title": "Note", "color": "#0969da"},
        "TIP": {"icon": "💡", "title": "Tip", "color": "#1a7f37"},
        "IMPORTANT": {"icon": "📢", "title": "Important", "color": "#8250df"},
        "WARNING": {"icon": "⚠️", "title": "Warning", "color": "#9a6700"},
        "CAUTION": {"icon": "🚫", "title": "Caution", "color": "#d1242f"}
    }
    
    # Also support [!TYPE] on a line by itself if it's within a quote
    lines = content.split('\n')
    processed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        alert_match = re.match(r'^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]', line.strip())
        
        if alert_match:
            alert_type = alert_match.group(1).upper()
            config = alert_types[alert_type]
            
            # Start of alert block
            processed_lines.append(f'<div class="markdown-alert markdown-alert-{alert_type.lower()}">')
            processed_lines.append(f'<p class="markdown-alert-title">{config["icon"]} {config["title"]}</p>')
            
            # Continue reading quoted lines for this alert
            i += 1
            while i < len(lines):
                if lines[i].strip().startswith('>'):
                    # Remove the '>' and optional trailing space
                    content_line = re.sub(r'^>\s?', '', lines[i])
                    if content_line.strip():
                        processed_lines.append(content_line)
                    else:
                        processed_lines.append('')
                    i += 1
                else:
                    break
            
            processed_lines.append('</div>')
        else:
            processed_lines.append(line)
            i += 1
            
    return '\n'.join(processed_lines)

def extract_architecture_from_md():
    """Extract architecture content from ARCHITECTURE.md and format diagrams as code blocks"""
    arch_md_path = "docs/ARCHITECTURE.md"
    if not os.path.exists(arch_md_path):
        print(f"Warning: {arch_md_path} not found, using default content")
        return "<p>Architecture documentation not found</p>"
    
    try:
        with open(arch_md_path, 'r') as f:
            content = f.read()
        
        # Convert text diagrams to properly formatted code blocks
        lines = content.split('\n')
        formatted_lines = []
        in_code_block = False
        in_diagram = False
        
        for line in lines:
            # Detect diagram blocks (start with ```text or contain diagram patterns)
            if line.strip().startswith('```text'):
                formatted_lines.append(line)
                in_code_block = True
                in_diagram = True
            elif line.strip() == '```' and in_diagram:
                formatted_lines.append(line)
                in_code_block = False
                in_diagram = False
            # Detect ASCII diagram patterns (box drawing characters, arrows, etc.)
            elif any(char in line for char in ['┌', '┐', '└', '┘', '─', '│', '├', '┤', '┬', '┴', '┼', '▶', '───']):
                if not in_code_block:
                    formatted_lines.append('```text')
                    in_code_block = True
                    in_diagram = True
                formatted_lines.append(line)
            elif in_diagram and (line.strip() == '' or line.strip().startswith('```')):
                if line.strip() == '```':
                    formatted_lines.append(line)
                    in_code_block = False
                    in_diagram = False
                else:
                    formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        # Close any open code block
        if in_code_block:
            formatted_lines.append('```')
        
        formatted_content = '\n'.join(formatted_lines)
        
        # Convert markdown to HTML
        import markdown
        html_content = markdown.markdown(formatted_content, extensions=['fenced_code', 'codehilite', 'tables', 'toc'])
        
        return html_content
    except Exception as e:
        print(f"Error parsing ARCHITECTURE.md: {e}")
        return "<p>Error loading architecture documentation</p>"

def extract_scenarios_from_vpc_md(vpc_md_path="docs/VPC.md"):
    """Extract scenario list from VPC.md"""
    if not os.path.exists(vpc_md_path):
        print(f"Warning: {vpc_md_path} not found, using default scenarios")
        return [{"title": s, "description": "", "resources": []} for s in ["demo", "basic", "advanced"]]
    
    try:
        with open(vpc_md_path, 'r') as f:
            content = f.read()
        
        # Split content by scenario headers: ### N. Title
        # We capture the number and title in groups to preserve them
        parts = re.split(r'\n### (\d+)\. ([^\n]+)', content)
        
        # parts[0] is the header before the first scenario
        # then we have: number, title, content, number, title, content, ...
        scenarios = []
        for i in range(1, len(parts), 3):
            num = parts[i].strip()
            full_title = parts[i+1].strip()
            block = parts[i+2]
            
            description = ""
            resources = []
            
            # Extract Goal as description
            goal_match = re.search(r'\* \*\*Goal\*\*: (.*?)$', block, re.MULTILINE)
            if goal_match:
                description = goal_match.group(1).strip()
            
                # Extract Architecture and infer resources
                arch_match = re.search(r'\* \*\*Architecture\*\*: (.*?)$', block, re.MULTILINE)
                if arch_match:
                    arch_text = arch_match.group(1).strip()
                    
                    # Best effort at resource inference for visual icons
                    # Look for specific names like "Web VPC", "Production VPC", etc.
                    vpc_names = re.findall(r'([A-Z][\w\s]+ VPC)', arch_text)
                    if vpc_names:
                        for name in vpc_names:
                            resources.append({"type": "vpc", "label": name.strip()})
                    elif "VPC" in arch_text:
                        resources.append({"type": "vpc", "label": "VPC"})
                        
                    if "Hub" in arch_text or "hub" in arch_text.lower():
                        resources.append({"type": "hub", "label": "Cloud Routing Hub"})
                    if "Data Center" in arch_text or "on-prem" in arch_text.lower():
                        resources.append({"type": "standalone_dc", "label": "Data Center"})
                    if "VPN" in arch_text:
                        resources.append({"type": "vpc", "label": "VPN Gateway"})
                    if "mesh" in arch_text.lower():
                        resources.append({"type": "vpc", "label": "Mesh Node"})
            
            scenarios.append({
                "title": f"{num}. {full_title}",
                "description": description,
                "resources": resources,
                "clean_title": full_title
            })
            
        if scenarios:
            return scenarios
        else:
            print("Warning: No scenarios found in VPC.md, using default")
            return [{"title": s, "description": "", "resources": []} for s in ["demo", "basic", "advanced"]]
    except Exception as e:
        print(f"Error parsing VPC.md: {e}")
        return ["demo", "basic", "advanced"]

def get_markdown_content(filename):
    """Get markdown content and convert to HTML (server-side rendering)"""
    # Prefer local files for stability and consistency with current repository state
    content = None
    
    # Root files vs docs files
    if filename in ["README.md", "LICENSE"]:
        md_path = filename  # Root directory
    else:
        md_path = os.path.join("docs", filename)
    
    # Try local path
    if os.path.exists(md_path):
        try:
            with open(md_path, 'r') as f:
                content = f.read()
                print(f"Loaded {filename} from local file: {md_path}")
        except Exception as e:
            print(f"Error reading local file {md_path}: {e}")

    # Fallback to GitHub if local file not found
    if content is None:
        try:
            import requests
            if filename in ["README.md", "LICENSE"]:
                github_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/main/{filename}"
            else:
                github_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/main/docs/{filename}"
            print(f"Fetching {filename} from GitHub as fallback: {github_url}")
            
            response = requests.get(github_url)
            if response.status_code == 200:
                content = response.text
                print(f"Successfully fetched {len(content)} characters from GitHub")
            else:
                print(f"GitHub fetch failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching {filename} from GitHub: {e}")
            return None
    
    if content is None:
        return None
    
    # Handle LICENSE as plain text in code block
    if filename == "LICENSE":
        import html
        import re
        # Escape HTML to prevent XSS or mangling
        escaped_content = html.escape(content)
        # Linkify URLs (refined to avoid capturing trailing punctuation or HTML entities)
        url_pattern = re.compile(r'(https?://[^\s<>"]+?)(?=[.,;:]?\s|&gt;|&lt;|"|\'|$)')
        linkified_content = url_pattern.sub(r'<a href="\1" target="_blank" style="color: #2196f3; text-decoration: underline;">\1</a>', escaped_content)
        return f'<pre style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 16px; overflow-x: auto; margin: 15px 0; white-space: pre-wrap;"><code>{linkified_content}</code></pre>'
    
    # Convert markdown to HTML (server-side rendering)
    try:
        import markdown
        # Format text diagrams as code blocks first
        lines = content.split('\n')
        formatted_lines = []
        in_code_block = False
        in_diagram = False
        
        for line in lines:
            # Detect diagram blocks (start with ```text or contain diagram patterns)
            if line.strip().startswith('```text'):
                formatted_lines.append(line)
                in_code_block = True
                in_diagram = True
            elif line.strip() == '```' and in_diagram:
                formatted_lines.append(line)
                in_code_block = False
                in_diagram = False
            # Detect ASCII diagram patterns (box drawing characters, arrows, etc.)
            elif any(char in line for char in ['┌', '┐', '└', '┘', '─', '│', '├', '┤', '┬', '┴', '┼', '▶', '───']):
                if not in_code_block:
                    formatted_lines.append('```text')
                    in_code_block = True
                    in_diagram = True
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        # Close any open code block
        if in_code_block:
            formatted_lines.append('```')
        
        formatted_content = '\n'.join(formatted_lines)
        
        # Pre-process for GitHub alerts and extras
        preprocessed_content = preprocess_markdown(formatted_content)
        
        # Convert markdown to HTML (server-side rendering)
        import markdown
        # Add extensions for better formatting (same as Vercel)
        # nl2br preserves line breaks as <br> tags
        html_content = markdown.markdown(preprocessed_content, extensions=['fenced_code', 'codehilite', 'tables', 'toc', 'nl2br'])
        
        return html_content
        
    except Exception as e:
        print(f"Error converting markdown to HTML: {e}")
        return f"<p>Error rendering {filename}</p>"

def append_markdown_to_tab(soup, tab_id, filename, title, description):
    """Append markdown content to existing tab for GitHub Pages"""
    content = get_markdown_content(filename)
    
    if content:
        tab = soup.find("div", {"id": tab_id})
        if tab:
            # Add CSS and content
            new_content = f"""
            <style>
            .markdown-content {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
            }}
            .markdown-content h1, .markdown-content h2, .markdown-content h3, .markdown-content h4 {{
                color: #232f3e;
                margin: 20px 0 10px 0;
            }}
            .markdown-content pre {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 16px;
                overflow-x: auto;
                margin: 15px 0;
            }}
            .markdown-content code {{
                background: #f8f9fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-size: 0.9em;
            }}
            .markdown-content pre code {{
                background: transparent;
                padding: 0;
                font-family: 'Courier New', Consolas, monospace;
                font-size: 0.85em;
                line-height: 1.4;
            }}
            .markdown-content .codehilite {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 16px;
                overflow-x: auto;
                margin: 15px 0;
            }}
            .markdown-content .codehilite pre {{
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
            .markdown-content .codehilite code {{
                background: transparent;
                padding: 0;
                font-family: 'Courier New', Consolas, monospace;
                font-size: 0.85em;
                line-height: 1.4;
            }}
            .markdown-content blockquote {{
                border-left: 4px solid #00897b;
                padding-left: 16px;
                margin: 15px 0;
                color: #666;
            }}
            .markdown-content table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }}
            .markdown-content th, .markdown-content td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            .markdown-content th {{
                background: #f5f5f5;
                font-weight: bold;
            }}
            </style>
            
            <!-- Divider between original content and {filename} -->
            <div style="margin: 30px 0; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 8px; border-left: 4px solid #2196f3;">
                <h3 style="margin: 0 0 10px 0; color: #1976d2;">📖 {title}</h3>
                <p style="margin: 0; color: #555;">{description}</p>
            </div>
            
            <div class="markdown-content">
                {content}
            </div>
            """
            
            tab.append(BeautifulSoup(new_content, "html.parser"))
            return True
    return False

def create_new_tab_static(soup, tab_id, tab_name, icon, filename, title, description):
    """Create a new tab with markdown content for GitHub Pages"""
    content = get_markdown_content(filename)
    
    if content:
        # Find the navigation tabs container
        nav_tabs = soup.find("div", style=lambda x: x and "display: flex" in x and "gap: 10px" in x and "border-bottom" in x)
        if nav_tabs:
            # Find the ReDoc button to insert before it
            redoc_button = None
            for button in nav_tabs.find_all("button"):
                if "ReDoc" in button.get_text():
                    redoc_button = button
                    break
            
            # Add new tab button before ReDoc button or at the end if not found
            new_tab_button = soup.new_tag("button", 
                onclick=f"showTab('{tab_id}')",
                style="background: none; border: none; padding: 10px; cursor: pointer;",
                id=f"tab-{tab_id}"
            )
            new_tab_button.string = f"{icon} {tab_name}"
            
            if redoc_button:
                redoc_button.insert_before(new_tab_button)
            else:
                nav_tabs.append(new_tab_button)
        
        # Find the content container (after the last content div)
        last_content = soup.find_all("div", id=lambda x: x and x.startswith("content-"))[-1]
        if last_content:
            # Create new content div
            new_content_div = soup.new_tag("div", 
                id=f"content-{tab_id}",
                style="display: none;"
            )
            
            # Add markdown content to the new tab
            markdown_html = f"""
            <h3>{icon} {title}</h3>
            <p>{description}</p>
            
            <style>
            .markdown-content {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
            }}
            .markdown-content h1, .markdown-content h2, .markdown-content h3, .markdown-content h4 {{
                color: #232f3e;
                margin: 20px 0 10px 0;
            }}
            .markdown-content pre {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 16px;
                overflow-x: auto;
                margin: 15px 0;
            }}
            .markdown-content code {{
                background: #f8f9fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-size: 0.9em;
            }}
            .markdown-content pre code {{
                background: transparent;
                padding: 0;
                font-family: 'Courier New', Consolas, monospace;
                font-size: 0.85em;
                line-height: 1.4;
            }}
            .markdown-content .codehilite {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 4px;
                padding: 16px;
                overflow-x: auto;
                margin: 15px 0;
            }}
            .markdown-content .codehilite pre {{
                background: transparent;
                border: none;
                padding: 0;
                margin: 0;
            }}
            .markdown-content .codehilite code {{
                background: transparent;
                padding: 0;
                font-family: 'Courier New', Consolas, monospace;
                font-size: 0.85em;
                line-height: 1.4;
            }}
            .markdown-content blockquote {{
                border-left: 4px solid #00897b;
                padding-left: 16px;
                margin: 15px 0;
                color: #666;
            }}
            .markdown-content table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }}
            .markdown-content th, .markdown-content td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            .markdown-content th {{
                background: #f5f5f5;
                font-weight: bold;
            }}
            </style>
            
            <div class="markdown-content">
                {content}
            </div>
            """
            
            new_content_div.append(BeautifulSoup(markdown_html, "html.parser"))
            last_content.insert_after(new_content_div)
            
            # Update the tab switching JavaScript to include the new tab
            scripts = soup.find_all("script")
            for script in scripts:
                if "showTab" in script.string and "contents =" in script.string:
                    # Update the contents array
                    old_contents = script.string
                    new_contents = old_contents.replace(
                        "const contents = ['api-guide', 'architecture', 'vpc', 'examples', 'testing'];",
                        f"const contents = ['api-guide', 'architecture', 'vpc', 'examples', 'testing', '{tab_id}'];"
                    )
                    script.string = new_contents
                    break
            
            return True
    return False

def export_static_fully_offline():
    """Export a single-file static VPC dashboard with all JS/CSS inlined, local and remote."""

    # Fetch scenarios (with graceful fallback)
    scenarios = extract_scenarios_from_vpc_md()
    print(f"Using scenarios from VPC.md: {scenarios}")
    
    # Try to load static scenarios fixture if it exists
    scenarios_fixture = "tests/fixtures/known_good_scenarios.json"
    if os.path.exists(scenarios_fixture):
        try:
            with open(scenarios_fixture, 'r') as f:
                scenarios = json.load(f)
                print(f"Using known-good scenario list from fixture: {scenarios_fixture}")
        except Exception as e:
            print(f"Warning: Could not load scenarios fixture: {e}")

    # Fetch VPC data (with graceful fallback)
    vpc_data = {"nodes": [], "edges": [], "scenarios": scenarios}
    
    # Try to load local fixture if it exists (for regression matching)
    fixture_path = "tests/fixtures/known_good_vpc_data.json"
    if os.path.exists(fixture_path):
        try:
            with open(fixture_path, 'r') as f:
                vpc_data = json.load(f)
                print(f"Using known-good VPC data from fixture: {fixture_path}")
        except Exception as e:
            print(f"Warning: Could not load fixture {fixture_path}: {e}")
    else:
        try:
            response = requests.get(f"{API_BASE_URL}/vpc", headers={"Accept": "application/json"})
            response.raise_for_status()
            vpc_data = response.json()
        except Exception as e:
            print(f"Warning: Could not fetch VPC data from API ({e}), using sample data")
            # Use sample data (same as before)
            # Improved fallback sample data with subnets so visual isn't empty
            vpc_data = {
                "nodes": [
                    {
                        "id": "vpc-demo-1",
                        "type": "vpc",
                        "label": "Demo VPC",
                        "cidr": "10.0.0.0/16",
                        "status": "active"
                    },
                    {
                        "id": "subnet-demo-1",
                        "type": "subnet",
                        "label": "Public Subnet",
                        "cidr": "10.0.1.0/24",
                        "parent": "vpc-demo-1"
                    },
                    {
                        "id": "subnet-demo-2",
                        "type": "subnet",
                        "label": "Private Subnet",
                        "cidr": "10.0.2.0/24",
                        "parent": "vpc-demo-1"
                    }
                ],
                "edges": [
                    {
                        "source": "vpc-demo-1",
                        "target": "leaf-1",
                        "type": "vpc-hosting"
                    }
                ]
            }
    
    # Always ensure vpc_data has the scenarios we extracted/loaded
    if not vpc_data.get('scenarios') or len(vpc_data.get('scenarios', [])) == 0:
        vpc_data['scenarios'] = scenarios

    # Read template
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: Template not found at {TEMPLATE_PATH}")
        sys.exit(1)

    with open(TEMPLATE_PATH, 'r') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")
    template_dir = os.path.dirname(TEMPLATE_PATH)

    # Inject JSON data first
    # STATIC_SCENARIOS should be a list of strings (titles) for original navigation logic
    # STATIC_VPC_DATA.scenarios should be a list of objects for resource rendering
    scenario_titles = [s.get('clean_title', s['title']) if isinstance(s, dict) else s for s in scenarios]
    
    data_script = soup.new_tag("script")
    data_script.string = (
        f"window.STATIC_VPC_DATA = {json.dumps(vpc_data)};\n"
        f"window.STATIC_SCENARIOS = {json.dumps(scenario_titles)};"
    )
    soup.head.insert(0, data_script)

    # Inline all JS scripts
    for script_tag in soup.find_all("script"):
        src = script_tag.get("src")
        if src:
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
            logo_path = os.path.join(template_dir, logo_src[4:])  # Remove leading /ui/
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
    coverage_html_content = extract_coverage_from_testing_md_html()
    if coverage_html_content:
        # Find the coverage section in the HTML and update it
        coverage_section = soup.find("strong", string=lambda text: text and "Current Coverage:" in text)
        if coverage_section and coverage_section.parent:
            # Replace the entire parent element (e.g., a <p> tag) with the new HTML
            new_coverage_tag = BeautifulSoup(coverage_html_content, "html.parser")
            coverage_section.parent.replace_with(new_coverage_tag)
            print("Updated coverage section in HTML.")
    
    # Define markdown files and their mapping to tabs (same as Vercel)
    markdown_files = {
        # Existing tabs - append content
        "ARCHITECTURE.md": {
            "tab_id": "content-architecture",
            "action": "append",
            "title": "Detailed Architecture Documentation",
            "description": "Comprehensive architecture documentation from docs/ARCHITECTURE.md"
        },
        "API_GUIDE.md": {
            "tab_id": "content-api-guide", 
            "action": "append",
            "title": "Complete API Documentation",
            "description": "Full API reference and documentation from docs/API_GUIDE.md"
        },
        "TESTING.md": {
            "tab_id": "content-testing",
            "action": "append", 
            "title": "Comprehensive Testing Guide",
            "description": "Complete testing documentation and coverage from docs/TESTING.md"
        },
        "VPC.md": {
            "tab_id": "content-vpc",
            "action": "append",
            "title": "VPC Implementation Details", 
            "description": "Detailed VPC implementation and scenarios from docs/VPC.md"
        },
        
        # New tabs - create dedicated tabs
        "README.md": {
            "tab_id": "readme",
            "action": "new_tab",
            "tab_name": "README",
            "icon": "🏠",
            "title": "Project README",
            "description": "Main project documentation and getting started guide from README.md"
        },
        "API_EXAMPLES.md": {
            "tab_id": "api-examples",
            "action": "new_tab",
            "tab_name": "API Examples",
            "icon": "📚",
            "title": "API Usage Examples",
            "description": "Comprehensive API examples and use cases from docs/API_EXAMPLES.md"
        },
        "IDEAS.md": {
            "tab_id": "ideas",
            "action": "new_tab", 
            "tab_name": "Ideas",
            "icon": "💡",
            "title": "Project Ideas and Future Development",
            "description": "Ideas for future features and improvements from docs/IDEAS.md"
        },
        "NETWORKING.md": {
            "tab_id": "networking",
            "action": "new_tab",
            "tab_name": "Networking",
            "icon": "⚙️", 
            "title": "Networking Implementation Details",
            "description": "Deep dive into networking implementation from docs/NETWORKING.md"
        },
        "LICENSE": {
            "tab_id": "license",
            "action": "new_tab",
            "tab_name": "License",
            "icon": "📄",
            "title": "Project License",
            "description": "GNU Affero General Public License terms and conditions"
        }
    }
    
    # Process each markdown file
    for filename, config in markdown_files.items():
        if config["action"] == "append":
            # Append to existing tab
            append_markdown_to_tab(
                soup, 
                config["tab_id"], 
                filename, 
                config["title"], 
                config["description"]
            )
        elif config["action"] == "new_tab":
            # Create new tab
            create_new_tab_static(
                soup,
                config["tab_id"],
                config["tab_name"], 
                config["icon"],
                filename,
                config["title"],
                config["description"]
            )

    # Universal Image Inlining pass (Base64)
    # This ensures images in markdown (like the logo in README) are visible offline
    for img_tag in soup.find_all("img"):
        src = img_tag.get("src")
        if src and not src.startswith("data:"):
            # Resolve path relative to project root
            # Images like 'control-plane/api/ui/assets/images/cncps_logo.svg'
            # should be found if this script runs from root
            img_path = src
            if not os.path.exists(img_path):
                # Try relative to template_dir if not found in root
                img_path = os.path.join(template_dir, src.replace("/ui/", ""))
                
            if os.path.exists(img_path):
                try:
                    with open(img_path, 'rb') as f:
                        img_data = f.read()
                    
                    mime_type = "image/png"
                    if img_path.endswith(".svg"): mime_type = "image/svg+xml"
                    elif img_path.endswith(".jpg") or img_path.endswith(".jpeg"): mime_type = "image/jpeg"
                    
                    b64_data = base64.b64encode(img_data).decode()
                    img_tag['src'] = f"data:{mime_type};base64,{b64_data}"
                    print(f"Inlined image: {img_path}")
                except Exception as e:
                    print(f"Warning: Could not inline image {img_path}: {e}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "index.html")

    with open(output_path, 'w') as f:
        f.write(str(soup) + '\n')

    print(f"Fully offline static dashboard written to {os.path.abspath(output_path)}")
    print(f"Contains {len(scenarios)} scenarios, all JS/CSS inlined (local + remote).")
    coverage_data = extract_coverage_from_testing_md()
    if coverage_data:
        print(f"Updated coverage from TESTING.md: {coverage_data.get('overall', 'N/A')}% overall")

if __name__ == "__main__":
    export_static_fully_offline()
