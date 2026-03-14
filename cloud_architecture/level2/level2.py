from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.storage import S3
from diagrams.aws.network import VPC, PublicSubnet, PrivateSubnet, InternetGateway, NATGateway, CloudFront, Endpoint
from diagrams.aws.general import User
from diagrams.aws.management import SystemsManager

# SWELL Architecture Level 2: Secured Infrastructure & DX Optimized
# Focusing on S3 security (OAC, Pre-signed URL) and SSM Proxy Access

graph_attr = {
    "splines": "curved",
    "nodesep": "1.2",
    "ranksep": "1.0",
    "bgcolor": "#F9F9F9",
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
    "SWELL Level 2: Secured Infrastructure & DX Infrastructure",
    filename="/Users/jang-yeong-uk/github/SWELL/cloud_architecture/level2/level2_architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    # External Entities
    user = User("Client Browser")
    admin = User("Developer\n(Admin)")
    
    # CDN Layer
    cloudfront = CloudFront("CloudFront\n(OAC Enabled)")
    
    # Storage & External Services
    s3 = S3("S3 Bucket\n(Private)")
    gemini = S3("Gemini AI API") # External API

    with Cluster("AWS Region: us-east-2", graph_attr={"fillcolor": "#EBF3FB", "style": "filled,rounded"}):
        
        ssm = SystemsManager("AWS SSM\n(Session Manager)")
        
        with Cluster("VPC: swell (10.0.0.0/24)", graph_attr={"fillcolor": "#E2E2E2", "bgcolor": "#E2E2E2"}):
            igw = InternetGateway("Internet Gateway")
            s3_endpoint = Endpoint("S3 Gateway\nEndpoint")
            
            with Cluster("Availability Zone: us-east-2a", graph_attr={"fillcolor": "#F0F4F8"}):
                
                with Cluster("Public Subnet", graph_attr={"fillcolor": "#D4EDDA"}):
                    frontend = EC2("Frontend\n(Next.js Server)")
                    nat = NATGateway("NAT Gateway")
                
                with Cluster("Private Subnet", graph_attr={"fillcolor": "#F8D7DA"}):
                    backend = EC2("Backend\n(FastAPI Server)")
                    db = RDS("RDS PostgreSQL")

    # Connections
    # 1. User Traffic (Public Assets via CDN)
    user >> Edge(label="1. Site Access", color="#2C3E50") >> igw >> frontend
    user >> Edge(label="2. Public Assets (CDN)", color="#D35400") >> cloudfront >> s3
    
    # 2. Private Data Access (Pre-signed URL)
    backend >> Edge(label="3. Issue Pre-signed URL (6m)", color="#16A085", style="dashed") >> user
    user >> Edge(label="4. Access Private Object", color="#16A085") >> s3
    
    # 3. Admin Access (DX: SSM ProxyCommand)
    admin >> Edge(label="SSH over SSM Proxy", color="#E67E22", style="bold") >> ssm >> backend
    
    # 4. Internal & Storage Traffic
    frontend >> Edge(label="Internal API", color="#2980B9") >> backend
    backend >> Edge(label="SQL", color="#8E44AD") >> db
    backend >> Edge(label="S3 Private Access", color="#27AE60") >> s3_endpoint >> s3
    
    # 5. Outbound
    backend >> Edge(label="Gemini API", color="#7F8C8D", style="dotted") >> nat >> igw >> gemini
