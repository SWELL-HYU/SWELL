from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.storage import S3
from diagrams.aws.network import VPC, PublicSubnet, PrivateSubnet, InternetGateway, NATGateway
from diagrams.aws.general import User
from diagrams.aws.management import SystemsManager

# SWELL Architecture Level 1: Standard EC2 Architecture
# Aesthetics improved version

graph_attr = {
    "splines": "curved", # 직각보다 부드러운 곡선 사용
    "nodesep": "1.2",
    "ranksep": "1.0",
    "bgcolor": "#F9F9F9", # 부드러운 배경색
    "fontsize": "24",
    "fontname": "Arial-Bold"
}

cluster_attr = {
    "penwidth": "1.5",
    "fontsize": "14",
    "fontname": "Arial-Bold",
    "style": "rounded,filled",
    "fillcolor": "#FFFFFF"
}

node_attr = {
    "fontsize": "11",
    "fontname": "Arial"
}

edge_attr = {
    "fontsize": "10",
    "fontname": "Arial-Italic",
    "penwidth": "1.2"
}

with Diagram(
    "SWELL Level 1: Secured VPC Architecture",
    filename="level1_architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    # External Entities
    user = User("Client Browser")
    admin = User("Developer\n(Admin)")
    ssm = SystemsManager("AWS SSM\n(Session Manager)")
    
    # Storage & API
    s3 = S3("S3 Bucket\n(Images/Assets)")
    gemini = S3("Gemini AI API") # External API representation

    with Cluster("AWS Region: us-east-2", graph_attr={"fillcolor": "#EBF3FB", "style": "filled,rounded"}):
        
        with Cluster("VPC: swell (10.0.0.0/24)", graph_attr={"fillcolor": "#E2E2E2", "bgcolor": "#E2E2E2"}):
            igw = InternetGateway("Internet Gateway")
            
            with Cluster("Availability Zone: us-east-2a", graph_attr={"fillcolor": "#F0F4F8"}):
                
                with Cluster("Public Subnet", graph_attr={"fillcolor": "#D4EDDA"}): # Greenish for Public
                    frontend = EC2("Frontend\n(Next.js Server)")
                    nat = NATGateway("NAT Gateway")
                
                with Cluster("Private Subnet", graph_attr={"fillcolor": "#F8D7DA"}): # Redish for Private
                    backend = EC2("Backend\n(FastAPI Server)")
                    db = RDS("RDS PostgreSQL\n(pgvector enabled)")

            # Standby area for DB Subnet Group
            with Cluster("Availability Zone: us-east-2b", graph_attr={"fillcolor": "#F9F9F9"}):
                PrivateSubnet("DB Subnet\n(Secondary)")

    # Connections
    # 1. User Traffic
    user >> Edge(label="HTTPS (80/443)", color="#2C3E50") >> igw >> frontend
    
    # 2. Admin Access
    admin >> Edge(color="#E67E22", style="dashed") >> ssm >> backend
    
    # 3. Internal Traffic
    frontend >> Edge(label="Internal API Call\n(Backend Private IP:8000)", color="#2980B9") >> backend
    backend >> Edge(label="SQL Connection\n(Port 5432)", color="#8E44AD") >> db
    
    # 4. Outbound Traffic
    backend >> Edge(label="Outbound (HTTPS)", color="#7F8C8D", style="dotted") >> nat >> igw >> gemini
    
    # 5. Storage Access
    backend >> Edge(label="Upload/Manage") >> s3
    frontend >> Edge(label="Read Assets", style="dashed") >> s3
