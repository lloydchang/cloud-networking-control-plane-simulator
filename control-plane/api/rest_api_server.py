# File: control-plane/api/rest_api_server.py
#!/usr/bin/env python3
"""
Cloud Networking REST API Server

FastAPI-based REST API for network operations.
Implements the Network API covering:
- VPCs
- Subnets
- Routes
- Security Groups
- NAT Gateways
- Internet Gateways
"""

import uuid
import asyncio
import time
import os
import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sqlalchemy import create_engine, text, Table, MetaData, select, insert, update
from sqlalchemy.orm import sessionmaker, Session

from bs4 import BeautifulSoup

import logging
logging.basicConfig(level=logging.INFO)

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    from metrics import METRICS
except ImportError:
    METRICS = {}
    PROMETHEUS_AVAILABLE = False

from .models import (
    Base,
    VPC as VPCModel,
    VPCEndpoint as VPCEndpointModel,
    Subnet as SubnetModel,
    SecurityGroup as SGModel,
    NATGateway as NATModel,
    Route as RouteModel,
    InternetGateway as InternetGatewayModel,
    VPNGateway as VPNGatewayModel,
    MeshNode as MeshNodeModel,
    CloudRoutingHub as HubModel,
    StandaloneDataCenter as StandaloneDCModel,
    StandaloneDCSubnet as StandaloneDCSubnetModel,
    VniCounter as VniCounterModel
)
from . import shared_api_logic as services

def get_processed_markdown_content(filename):
    """Generic function to fetch and process any markdown content from docs"""
    # In Vercel, fetch from GitHub since docs are not deployed
    if os.getenv("VERCEL"):
        try:
            import httpx
            # Check if it's a root file (README.md, LICENSE)
            if filename in ["README.md", "LICENSE"]:
                github_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/main/{filename}"
            else:
                github_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/main/docs/{filename}"
            print(f"DEBUG: Fetching {filename} from GitHub: {github_url}")
            
            with httpx.Client() as client:
                response = client.get(github_url)
                if response.status_code == 200:
                    content = response.text
                    print(f"DEBUG: Successfully fetched {len(content)} characters from GitHub")
                    # Convert markdown to HTML (server-side rendering)
                    return convert_markdown_to_html(content, filename)
                else:
                    print(f"DEBUG: GitHub fetch failed: {response.status_code}")
                    return None
                
        except Exception as e:
            print(f"DEBUG: Error fetching {filename} from GitHub: {e}")
            return None
    else:
        # Local development - try multiple possible paths
        if filename in ["README.md", "LICENSE"]:
            # Root directory files
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", filename),
                os.path.join(os.path.dirname(__file__), "..", filename),
                os.path.join(os.getcwd(), filename),
                f"../{filename}",  # Relative path
                filename,  # Direct path
            ]
        else:
            # Docs directory files
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "..", "..", "docs", filename),
                os.path.join(os.path.dirname(__file__), "..", "docs", filename),
                os.path.join(os.getcwd(), "docs", filename),
                f"/tmp/docs/{filename}",  # Vercel might copy files here
                f"docs/{filename}",  # Relative path
                f"../docs/{filename}",  # Another relative path
            ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                print(f"DEBUG: Found {filename} at: {path}")
                break
        
        if not file_path:
            print(f"DEBUG: {filename} not found in any of these paths:")
            for path in possible_paths:
                print(f"  - {path}")
            return None
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            # Convert markdown to HTML (server-side rendering)
            return convert_markdown_to_html(content, filename)
        except Exception as e:
            print(f"DEBUG: Error reading {filename}: {e}")
            return None

def convert_markdown_to_html(content, filename):
    """Convert markdown content to HTML with proper diagram formatting"""
    # Handle LICENSE as plain text in code block
    if filename == "LICENSE":
        return f'<pre style="background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 16px; overflow-x: auto; margin: 15px 0;"><code>{content}</code></pre>'
    
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
        return f"<p>Error rendering markdown content</p>"

def get_processed_architecture_content():
    """Extract and process architecture content with diagram formatting"""
    return get_processed_markdown_content("ARCHITECTURE.md")

def append_markdown_content(soup, tab_id, filename, title, description):
    """Generic function to append markdown content to a specific tab"""
    content = get_processed_markdown_content(filename)
    
    if content:
        tab = soup.find("div", {"id": tab_id})
        if tab:
            # Add CSS for the appended content
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
            /* Fix for codehilite blocks generated by markdown */
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
            
            # Append the new content to the existing tab
            tab.append(BeautifulSoup(new_content, "html.parser"))
            return True
    return False

def create_new_tab(soup, tab_id, tab_name, icon, filename, title, description):
    """Create a new tab with markdown content"""
    content = get_processed_markdown_content(filename)
    
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
            /* Fix for codehilite blocks generated by markdown */
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

app = FastAPI(
    title="Cloud Networking Control Plane Simulator - Control Plane API",
    description="Cloud Networking Control Plane Simulator - Control Plane API",
    version="1.0.0",
    redoc_url=None,  # Disable built-in ReDoc
)

# Add CORS middleware for GitHub Pages integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lloydchang.github.io",
        "http://localhost:8000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if os.path.exists(SCRIPTS_DIR):
    app.mount("/scripts", StaticFiles(directory=SCRIPTS_DIR), name="scripts")

ASSETS_DIR = "/app/assets"
UI_DIR = os.path.join(os.path.dirname(__file__), "ui")

# Only create assets directory if not in Vercel (read-only filesystem)
if not os.getenv("VERCEL"):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Mount UI assets directory for logo and other static files
if os.path.exists(UI_DIR):
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

DB_DIR = "/tmp" if os.getenv("VERCEL") else os.getenv("DB_DIR", "/app/data")
DB_PATH = os.getenv("DB_PATH", f"{DB_DIR}/network.db")
if not DB_PATH.startswith(":memory:"):
    os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def initialize_database_and_metrics():
    db = SessionLocal()
    try:
        # Initialize vni_counter table if it doesn't exist
        try:
            db.execute(text("CREATE TABLE IF NOT EXISTS vni_counter (id INTEGER PRIMARY KEY, current INTEGER NOT NULL);"))
            db.commit()
        except Exception as e:
            logging.warning(f"Could not create vni_counter table: {e}")

        # Initialize vni_counter row if it doesn't exist
        try:
            metadata = MetaData()
            vni_counter = Table("vni_counter", metadata, autoload_with=engine)
            row = db.execute(select(vni_counter).where(vni_counter.c.id == 1)).fetchone()
            if not row:
                db.execute(insert(vni_counter).values(id=1, current=1003))
                db.commit()
                logging.info("Inserted initial vni_counter row with id=1 and current=1003")
            else:
                logging.info(f"vni_counter exists with current={row['current']}")
        except Exception as e:
            logging.warning(f"Could not initialize vni_counter: {e}")

        # Initialize metrics if available
        if PROMETHEUS_AVAILABLE:
            try:
                METRICS["vpcs_total"].set(db.query(VPCModel).count())
                METRICS["subnets_total"].set(db.query(SubnetModel).count())
                METRICS["routes_total"].set(db.query(RouteModel).count())
                METRICS["security_groups_total"].set(db.query(SGModel).count())
                METRICS["nat_gateways_total"].set(db.query(NATModel).count())
                METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
            except Exception as e:
                logging.warning(f"Could not initialize metrics: {e}")

        # Generate OpenAPI spec
        try:
            if not os.getenv("VERCEL"):
                openapi_path = os.path.join(ASSETS_DIR, "openapi.json")
                with open(openapi_path, "w") as f:
                    json.dump(app.openapi(), f)
        except Exception as e:
            logging.warning(f"Could not generate OpenAPI spec: {e}")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class VPCCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cidr: str
    region: str = "us-east-1"
    secondary_cidrs: List[str] = Field(default_factory=list)
    scenario: Optional[str] = None

class VPC(BaseModel):
    id: str
    name: str
    cidr: str
    region: str
    secondary_cidrs: List[str]
    scenario: Optional[str]
    status: str
    created_at: datetime

class VPCEndpointCreate(BaseModel):
    name: str
    ip: str

class VPCEndpoint(BaseModel):
    id: str
    vpc_id: str
    name: str
    ip: str
    subnet_id: str
    status: str
    created_at: datetime

class SecurityRuleCreate(BaseModel):
    direction: str
    protocol: str
    port_from: Optional[int] = None
    port_to: Optional[int] = None
    cidr: str = "0.0.0.0/0"

class SecurityGroupCreate(BaseModel):
    name: str
    description: str = ""
    rules: List[SecurityRuleCreate] = Field(default_factory=list)

class SecurityGroup(BaseModel):
    id: str
    name: str
    description: str
    rules: List[dict]
    created_at: datetime

class SubnetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cidr: str
    availability_zone: str = "us-east-1a"
    data_center: str = "CDC-1"

class Subnet(BaseModel):
    id: str
    vpc_id: str
    name: str
    cidr: str
    availability_zone: str
    data_center: str
    status: str
    created_at: datetime

class RouteCreate(BaseModel):
    destination: str
    next_hop: str
    next_hop_type: str

class Route(BaseModel):
    id: str
    vpc_id: str
    destination: str
    next_hop: str
    next_hop_type: str
    status: str
    created_at: datetime

class NATGatewayCreate(BaseModel):
    subnet_id: str

class NATGateway(BaseModel):
    id: str
    vpc_id: str
    subnet_id: str
    public_ip: str
    status: str
    created_at: datetime

class InternetGateway(BaseModel):
    id: str
    vpc_id: str
    status: str
    created_at: datetime

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    if not PROMETHEUS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prometheus client not installed")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    if PROMETHEUS_AVAILABLE:
        METRICS["api_requests"].labels(method=request.method, endpoint=request.url.path).inc()
    start = time.time()
    response = await call_next(request)
    _ = (time.time() - start) * 1000
    return response

@app.post("/vpcs", response_model=VPC, status_code=201)
def create_vpc(vpc: VPCCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_vpc = services.create_vpc_logic(db, vpc.name, vpc.cidr, vpc.region, vpc.secondary_cidrs, vpc.scenario)
    background_tasks.add_task(services.provision_vpc_task, SessionLocal, new_vpc.id)
    return new_vpc

@app.get("/vpcs", response_model=List[VPC])
def list_vpcs(db: Session = Depends(get_db)):
    return db.query(VPCModel).all()

@app.get("/vpcs/{vpc_id}", response_model=VPC)
def get_vpc(vpc_id: str, db: Session = Depends(get_db)):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    return vpc

@app.delete("/vpcs/{vpc_id}")
def delete_vpc(vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    vpc = services.delete_vpc_logic(db, vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    background_tasks.add_task(services.deprovision_vpc_task, SessionLocal, vpc_id)
    return {"message": "VPC deletion initiated"}

@app.get("/vpc", include_in_schema=False)
async def get_vpc_data():
    """Get all VPC data for the VPC view"""
    db = SessionLocal()
    try:
        vpcs = db.query(VPCModel).all()
        
        # If no VPCs exist, fetch static data from GitHub Pages
        if not vpcs:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.get("https://lloydchang.github.io/cloud-networking-control-plane-simulator/")
                    if response.status_code == 200:
                        # Extract STATIC_VPC_DATA from the GitHub Pages HTML
                        import re
                        match = re.search(r'window\.STATIC_VPC_DATA\s*=\s*({.+?});', response.text)
                        if match:
                            import json
                            static_data = json.loads(match.group(1))
                            return static_data
            except Exception as e:
                logging.warning(f"Could not fetch static data from GitHub Pages: {e}")
        
        # Transform VPCs into nodes format
        nodes = []
        edges = []
        
        for vpc in vpcs:
            nodes.append({
                "id": vpc.id,
                "type": "vpc",
                "label": vpc.name,
                "cidr": vpc.cidr,
                "region": vpc.region,
                "secondary_cidrs": vpc.secondary_cidrs or [],
                "scenario": vpc.scenario,
                "status": vpc.status,
                "created_at": vpc.created_at.isoformat() if vpc.created_at else None
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "scenarios": []
        }
    finally:
        db.close()

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return JSONResponse(app.openapi())

@app.get("/", include_in_schema=False)
async def vpc_view():
    """Serve the VPC view HTML page with all markdown content"""
    vpc_html_path = os.path.join(os.path.dirname(__file__), "ui", "vpc.html")
    try:
        with open(vpc_html_path, "r") as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Define markdown files and their mapping to tabs
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
                "description": "MIT License terms and conditions"
            }
        }
        
        # Process each markdown file
        for filename, config in markdown_files.items():
            if config["action"] == "append":
                # Append to existing tab
                append_markdown_content(
                    soup, 
                    config["tab_id"], 
                    filename, 
                    config["title"], 
                    config["description"]
                )
            elif config["action"] == "new_tab":
                # Create new tab
                create_new_tab(
                    soup,
                    config["tab_id"],
                    config["tab_name"], 
                    config["icon"],
                    filename,
                    config["title"],
                    config["description"]
                )
        
        return HTMLResponse(str(soup))
    except FileNotFoundError:
        return HTMLResponse("<h1>VPC View Not Found</h1><p>The VPC view HTML file could not be found.</p>", status_code=404)

@app.get("/redoc", include_in_schema=False)
async def redoc(request: Request):
    openapi_path = "/openapi.json"
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Cloud Networking Control Plane Simulator - ReDoc</title>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <link href='https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700' rel='stylesheet'>
      <style>
        body {{ margin: 0; padding: 0; }}
        redoc {{ height: 100vh; }}
      </style>
    </head>
    <body>
      <redoc spec-url='{openapi_path}'></redoc>
      <script src='https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js'></script>
    </body>
    </html>
    """)

@app.get("/docs", include_in_schema=False)
async def docs(request: Request):
    openapi_path = "/openapi.json"
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Cloud Networking Control Plane Simulator - Swagger UI</title>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui.css" />
      <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin:0; background: #fafafa; }}
      </style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui-bundle.js"></script>
      <script src="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui-standalone-preset.js"></script>
      <script>
        window.onload = function() {{
          SwaggerUIBundle({{
            url: '{openapi_path}',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            plugins: [
              SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            tryItOutEnabled: true
          }});
        }}
      </script>
    </body>
    </html>
    """)

# Subnet endpoints
@app.post("/vpcs/{vpc_id}/subnets", response_model=Subnet, status_code=201)
def create_subnet(vpc_id: str, subnet: SubnetCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_subnet = services.create_subnet_logic(db, vpc_id, subnet.name, subnet.cidr, subnet.availability_zone)
    background_tasks.add_task(services.provision_subnet_task, SessionLocal, new_subnet.id)
    return new_subnet

@app.get("/vpcs/{vpc_id}/subnets", response_model=List[Subnet])
def list_subnets(vpc_id: str, db: Session = Depends(get_db)):
    return services.list_subnets(vpc_id)

@app.delete("/subnets/{subnet_id}")
def delete_subnet(subnet_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    subnet = services.delete_subnet_logic(db, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    background_tasks.add_task(services.deprovision_subnet_task, SessionLocal, subnet_id)
    return {"message": "Subnet deletion initiated"}

# Route endpoints
@app.post("/vpcs/{vpc_id}/routes", response_model=Route, status_code=201)
def create_route(vpc_id: str, route: RouteCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_route = services.create_route_logic(db, vpc_id, route.destination, route.next_hop, route.next_hop_type)
    background_tasks.add_task(services.provision_route_task, SessionLocal, new_route.id)
    return new_route

@app.get("/vpcs/{vpc_id}/routes", response_model=List[Route])
def list_routes(vpc_id: str, db: Session = Depends(get_db)):
    return services.list_routes(vpc_id)

@app.delete("/routes/{route_id}")
def delete_route(route_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    route = services.delete_route_logic(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    background_tasks.add_task(services.deprovision_route_task, SessionLocal, route_id)
    return {"message": "Route deletion initiated"}

# Security Group endpoints
@app.post("/security-groups", response_model=SecurityGroup, status_code=201)
def create_security_group(security_group: SecurityGroupCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_sg = services.create_security_group_logic(db, security_group.name, security_group.description, security_group.rules)
    return new_sg

@app.get("/security-groups", response_model=List[SecurityGroup])
def list_security_groups(db: Session = Depends(get_db)):
    return services.list_security_groups()

# Gateway endpoints
@app.post("/vpcs/{vpc_id}/internet-gateways", response_model=InternetGateway, status_code=201)
def create_internet_gateway(vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    igw = services.create_internet_gateway_logic(db, vpc_id)
    background_tasks.add_task(services.provision_internet_gateway_task, SessionLocal, igw.id)
    return igw

@app.post("/vpcs/{vpc_id}/nat-gateways", response_model=NATGateway, status_code=201)
def create_nat_gateway(vpc_id: str, nat: NATGatewayCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    nat_gw = services.create_nat_logic(db, vpc_id, nat.subnet_id)
    background_tasks.add_task(services.provision_nat_gateway_task, SessionLocal, nat_gw.id)
    return nat_gw