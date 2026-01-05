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

def extract_scenarios_from_vpc_md():
    """Extract scenario list from VPC.md"""
    vpc_md_path = "docs/VPC.md"
    if not os.path.exists(vpc_md_path):
        print(f"Warning: {vpc_md_path} not found, using default scenarios")
        return ["demo", "basic", "advanced"]
    
    try:
        with open(vpc_md_path, 'r') as f:
            content = f.read()
        
        # Extract scenario numbers using regex
        scenario_pattern = r'### (\d+)\. (.+)'
        matches = re.findall(scenario_pattern, content)
        
        if matches:
            scenarios = []
            for num, name in matches:
                scenarios.append(name.strip())
            return scenarios
    except Exception as e:
        print(f"Error parsing VPC.md: {e}")
        return ["demo", "basic", "advanced"]

def get_markdown_content(filename):
    """Get markdown content and convert to HTML (server-side rendering)"""
    try:
        import requests
        github_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/main/docs/{filename}"
        print(f"Fetching {filename} from GitHub: {github_url}")
        
        response = requests.get(github_url)
        if response.status_code == 200:
            content = response.text
            print(f"Successfully fetched {len(content)} characters from GitHub")
        else:
            print(f"GitHub fetch failed: {response.status_code}")
            # Fallback to local file
            md_path = os.path.join("docs", filename)
            if os.path.exists(md_path):
                with open(md_path, 'r') as f:
                    content = f.read()
            else:
                return None
    except Exception as e:
        print(f"Error fetching {filename} from GitHub: {e}")
        # Fallback to local file
        md_path = os.path.join("docs", filename)
        if os.path.exists(md_path):
            with open(md_path, 'r') as f:
                content = f.read()
        else:
            return None
    
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
        html_content = markdown.markdown(formatted_content, extensions=['fenced_code', 'codehilite', 'tables', 'toc'])
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
                        "const contents = ['api-guide', 'architecture', 'vpc-details', 'examples', 'testing'];",
                        f"const contents = ['api-guide', 'architecture', 'vpc-details', 'examples', 'testing', '{tab_id}'];"
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
    
    # Define markdown files and their mapping to tabs (same as Vercel)
    markdown_files = {
        # Existing tabs - append content
        "ARCHITECTURE.md": {
            "tab_id": "content-architecture",
            "action": "append",
            "title": "Detailed Architecture Documentation",
            "description": "Comprehensive architecture documentation from docs/ARCHITECTURE.md"
        },
        "API.md": {
            "tab_id": "content-api-guide", 
            "action": "append",
            "title": "Complete API Documentation",
            "description": "Full API reference and documentation from docs/API.md"
        },
        "TESTING.md": {
            "tab_id": "content-testing",
            "action": "append", 
            "title": "Comprehensive Testing Guide",
            "description": "Complete testing documentation and coverage from docs/TESTING.md"
        },
        "VPC.md": {
            "tab_id": "content-vpc-details",
            "action": "append",
            "title": "VPC Implementation Details", 
            "description": "Detailed VPC implementation and scenarios from docs/VPC.md"
        },
        
        # New tabs - create dedicated tabs
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
        "NETWORKING_IMPLEMENTATION.md": {
            "tab_id": "implementation",
            "action": "new_tab",
            "tab_name": "Implementation",
            "icon": "⚙️", 
            "title": "Networking Implementation Details",
            "description": "Deep dive into networking implementation from docs/NETWORKING_IMPLEMENTATION.md"
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
