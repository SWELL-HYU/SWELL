from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.storage import S3
from diagrams.aws.network import InternetGateway
from diagrams.aws.general import Users

# SWELL Architecture Level 0: Simplified Version
# - Default VPC 사용 (Public/Private 구분 없음)
# - RDS 및 S3 공개 설정 반영

graph_attr = {
    "splines": "ortho",
    "nodesep": "1.0",
    "ranksep": "1.5",
    "bgcolor": "#FFFFFF",
    "fontsize": "24",
    "fontname": "Arial-Bold"
}

cluster_attr = {
    "penwidth": "2.0",
    "fontsize": "16",
    "fontname": "Arial-Bold"
}

node_attr = {
    "width": "0.8",
    "height": "0.8",
    "fontsize": "12",
    "fontname": "Arial-Bold"
}

edge_attr = {
    "fontsize": "11",
    "fontname": "Arial-Bold",
    "penwidth": "2.0",
    "color": "#333333"
}

with Diagram(
    "SWELL Level 0 Architecture: Simple & Open",
    filename="level0_architecture",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
    node_attr=node_attr,
    edge_attr=edge_attr
):
    users = Users("Client / User")

    with Cluster("AWS Cloud", graph_attr=cluster_attr):
        
        # S3는 글로벌 서비스이며 '오픈' 상태를 강조하기 위해 VPC 외부 배치
        s3 = S3("Public S3 Bucket\n(Asset/Image)")
        
        # RDS도 '오픈' 상태(Public Access)를 시각화하기 위해 VPC 외부 혹은 경계에 배치
        # 여기서는 가장 단순한 형태를 위해 VPC 외부에 배치하여 접근 용이성을 강조함
        db = RDS("Global RDS\n(PostgreSQL - Open)")

        with Cluster("Default VPC", graph_attr=cluster_attr):
            igw = InternetGateway("Internet Gateway")
            
            # 단일 subnet 환경처럼 구성 (Public Subnet)
            with Cluster("Public Subnet (Default)", graph_attr=cluster_attr):
                frontend = EC2("Frontend\n(Next.js)")
                backend = EC2("Backend\n(FastAPI)")

    # Flow
    users >> Edge(label="HTTPS") >> igw >> frontend
    frontend >> Edge(label="API Gateway/Call") >> backend
    
    # 오픈된 리소스들에 대한 직접 연결
    backend >> Edge(label="Direct Access") >> db
    backend >> Edge(label="Direct Upload/Download") >> s3
    frontend >> Edge(label="Static Assets", style="dashed") >> s3
