# SWELL Level 0 배포 가이드: Simplified Cloud Architecture

> **목적:** 초기 개발 및 테스트 속도를 극대화하기 위해 AWS의 **Default VPC**와 **Public 리소스**를 활용하는 가장 단순한 배포 과정을 기록한다.
> **아키텍처 다이어그램:** [level0.py](./level0.py)에서 생성된 `level0_architecture.png` 참조.

---

## Phase 0: IAM 사용자 및 권한 구성

> [!IMPORTANT]
> AWS 계정의 Root User(루트 사용자)로 직접 인프라를 조작하는 것은 보안상 매우 위험하다.
> 루트 계정은 모든 권한을 가지고 있어, 실수 한 번이 계정 전체에 영향을 미칠 수 있기 때문이다.
> 따라서 **관리 권한을 가진 별도의 IAM User를 만들어서 사용하는 것이 AWS의 보안 Best Practice**이다.

### 0-1. IAM 그룹 생성

- **내용:** IAM 콘솔에서 **사용자 그룹(User Group)**을 먼저 생성한다.
- **이유:** 개별 사용자에게 직접 정책을 붙이면 나중에 팀원이 추가될 때마다 일일이 반복해야 한다. 그룹에 정책을 붙여두면, 그룹에 사람만 추가하면 되므로 **권한 관리가 일원화**된다.
- **설정:**
  - 그룹 이름: `SWELL-ADMIN` (예시)
  - 연결 정책: **`AdministratorAccess`** (개발 단계에서는 모든 AWS 서비스 접근이 필요하므로 관리자 정책을 부여한다.)

### 0-2. IAM 사용자 생성

- **내용:** 위 그룹 안에 **IAM User**를 생성하고, 이후 모든 AWS 콘솔 작업은 이 사용자로 로그인하여 수행한다.
- **이유:** 루트 계정의 직접 사용을 차단하고, 문제 발생 시 이 사용자의 권한만 회수하면 되므로 **사고 범위를 격리(Blast Radius 최소화)**할 수 있다.
- **설정:**
  - 콘솔 액세스: 활성화 (비밀번호 설정)
  - 소속 그룹: `SWELL-ADMIN`

### 0-3. IAM Access Key 발급

- **내용:** 위에서 만든 IAM User의 **[보안 자격 증명]** 탭에서 **액세스 키(Access Key)**를 생성한다.
- **용도:** 백엔드 서버가 S3에 파일을 업로드(Write)할 수 있는 프로그래밍 방식의 인증 수단이다.
- **주의:** `Access Key ID`와 `Secret Access Key`는 **생성 시 한 번만 보여지므로** 반드시 안전하게 기록해둔다. (백엔드 `.env` 파일에 사용됨)

---

## Phase 1: Default VPC 구성 확인

> [!NOTE]
> Level 0 아키텍처는 복잡한 서브넷 설계 대신 AWS 계정에 기본으로 제공되는 **Default VPC**를 그대로 사용한다.
> Default VPC의 모든 서브넷은 이미 인터넷 게이트웨이(IGW)와 연결되어 소통이 가능한 상태이다.

### 1-1. VPC 확인
- **내용:** AWS 콘솔의 **[VPC] → [사용자 VPC]**에서 '기본 VPC'가 존재하며, 상태가 `사용 가능`인지 확인한다.
- **이유:** 별도의 네트워크 구축 과정 없이 즉시 리소스를 배치할 수 있어 초기 구축 시간을 단축한다.

### 1-2. 서브넷 확인
- **내용:** 기본 VPC 안에 생성된 서브넷들이 모두 **퍼블릭 IP 자동 할당**이 켜져 있는지 확인한다.
- **이유:** Level 0에서는 NAT Gateway 없이 모든 EC2 인스턴스가 직접 인터넷과 통신해야 하므로 퍼블릭 IP가 필수적이다.

---

## Phase 1.5: 보안 그룹 일괄 생성 (Security Groups)

> [!IMPORTANT]
> 보안 그룹은 리소스(RDS, EC2) 생성 시 선택해야 하는 필수 항목이다.
> 그런데 보안 그룹끼리 **서로를 참조**해야 하므로(예: DB는 백엔드만 허용, 백엔드는 프론트엔드만 허용), 리소스와 동시에 만들면 "아직 안 만든 보안 그룹"을 참조해야 하는 **순환 참조 문제**가 발생한다.
> 따라서 **모든 보안 그룹을 먼저 만들어두고**, 각 리소스 생성 시에는 이미 만들어진 보안 그룹을 선택하기만 하면 된다.

### 1.5-1. `swell-db-public-sg` (데이터베이스용)
- **용도:** RDS(PostgreSQL)에 부착할 보안 그룹
- **인바운드 규칙:**
  - **PostgreSQL (5432):** **내 IP (My IP)** — 로컬 DB 툴로(DBeaver 등) 접속용
  - **PostgreSQL (5432):** **`swell-backend-sg`** — 백엔드 서버가 DB에 접속하기 위함

### 1.5-2. `swell-backend-sg` (백엔드 서버용)
- **용도:** 백엔드 EC2 인스턴스에 부착할 보안 그룹
- **인바운드 규칙:**
  - **SSH (22):** **내 IP (My IP)** — 관리자 SSH 접속용
  - **사용자 지정 TCP (8000):** **`swell-frontend-sg`** — 프론트엔드 서버가 백엔드 API에 요청하기 위함

### 1.5-3. `swell-frontend-sg` (프론트엔드 서버용)
- **용도:** 프론트엔드 EC2 인스턴스에 부착할 보안 그룹
- **인바운드 규칙:**
  - **SSH (22):** **내 IP (My IP)** — 관리자 SSH 접속용
  - **HTTP (80):** **Anywhere (0.0.0.0/0)** — 일반 사용자가 웹 브라우저로 접속하기 위함

> [!TIP]
> **보안 그룹 ID 참조란?**
> 규칙의 '소스(Source)' 칸에 IP 주소 대신 다른 보안 그룹의 ID(예: `sg-xxxx`)를 입력하는 방식이다. 이렇게 설정하면 해당 보안 그룹을 가진 모든 리소스 간의 통신이 자동으로 허용되어 매우 편리하고 안전하다.

> [!NOTE]
> **3개를 모두 먼저 생성한 후** 인바운드 규칙을 편집해야 한다. 예를 들어 `swell-db-public-sg`의 규칙에 `swell-backend-sg`를 참조하려면 `swell-backend-sg`가 이미 존재해야 검색이 된다. 따라서 **보안 그룹 껍데기를 3개 다 만든 뒤 → 각각의 인바운드 규칙을 편집**하는 순서로 진행한다.

---

## Phase 2: RDS (PostgreSQL) 데이터베이스 생성 (Public)

> [!IMPORTANT]
> Level 0에서는 데이터베이스를 **퍼블릭 액세스 허용**으로 설정한다. 이는 보안상 권장되지 않지만, 로컬 개발 환경에서 직접 DB에 접속하여 데이터를 확인하고 관리하기에는 가장 편리한 방법이다.

### 2-1. 엔진 옵션

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **엔진 유형** | PostgreSQL | SWELL 백엔드가 사용하는 RDBMS |
| **엔진 버전** | `PostgreSQL 17.4-R2` | `pgvector` 확장이 안정적으로 지원되는 최신 버전 |
| **확장 지원(Extended Support)** | **체크 해제** | 최신 버전이므로 유료 연장 지원 불필요 (비용 절감) |

### 2-2. 템플릿 및 설정

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **템플릿** | **프리 티어** | 재해 복구(DR), 고가용성(Multi-AZ) 옵션이 빠져 초기 비용 최소화 |
| **DB 인스턴스 식별자** | `swell-db` | AWS 콘솔에서 해당 리소스를 명확히 식별하기 위함 |
| **마스터 사용자 이름** | (직접 설정) | 백엔드 `.env`의 `DATABASE_URL`에 사용되는 핵심 자격 증명 |
| **마스터 암호** | (직접 설정) | 위와 동일 |
| **자격 증명 관리** | **자체 관리** | 가장 직관적이며 로컬 DB 툴에서 접근하기에 적합 |

### 2-3. 인스턴스 및 스토리지 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **인스턴스 유형** | `db.t3.micro` | 소규모 데이터 및 학습용 환경에 적합, 프리 티어 대상 |
| **스토리지 유형** | gp3 (기본값 유지) | 범용 SSD로 개발 환경에 충분한 성능 |

### 2-4. 연결 (네트워크)

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **VPC** | Default VPC | Phase 1에서 확인한 기본 VPC 사용 |
| **가용 영역(AZ)** | `us-east-2a` | EC2와 같은 AZ 배치로 지연 및 비용 최소화 |
| **퍼블릭 액세스** | **예 (Yes)** | 로컬 환경에서 직접 DB 접속 가능하도록 허용 |
| **보안 그룹** | **`swell-db-public-sg`** | Phase 1.5에서 미리 생성한 보안 그룹 선택 |

> [!NOTE]
> **RDS 접속을 위한 추가 IAM 정책은 필요하지 않는다.**
> 현재 가이드는 AWS의 IAM 인증 대신 **DB 엔진 내부의 암호 인증** 방식을 사용한다. 따라서 네트워크(보안 그룹)와 데이터베이스 계정 정보만 정확하면 로컬 툴(DBeaver 등)에서 즉시 접속이 가능하다.

### 2-5. 추가 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **초기 데이터베이스 이름** | `swell` | 반드시 입력해야 함 (빈칸이면 DB가 생성되지 않음) |
| **성능 개선 도우미** | **비활성화** | 초기 개발 단계에서 불필요한 모니터링 비용 절감 |
| **자동 백업** | **비활성화** | 데이터 재주입 스크립트가 있으므로 불필요한 백업 비용 방지 |

### 2-6. 생성 후 작업

#### 외부 접속 테스트 (Connectivity Check)
- DB 접속 도구(DBeaver, TablePlus 등)를 사용하여 RDS에 정상적으로 연결되는지 확인한다.
- [RDS 콘솔] → [swell-db] → **'연결 및 보안'** 탭에서 **엔드포인트**를 복사하여 호스트로 사용한다.
- 만약 접속이 되지 않는다면, Phase 1.5의 `swell-db-public-sg` 인바운드 규칙에 본인의 현재 IP가 등록되어 있는지 확인한다.

> **DB 접속 주소 규칙 (Connection URL Format):**
> ```
> postgresql://[USER]:[PASSWORD]@[ENDPOINT]:5432/[DB_NAME]
> ```
> | 변수 | 값 | 출처 |
> | :--- | :--- | :--- |
> | `USER` | 마스터 사용자 이름 (예: `postgres`) | Phase 2-2 |
> | `PASSWORD` | 마스터 암호 | Phase 2-2 |
> | `ENDPOINT` | RDS 엔드포인트 주소 | RDS 콘솔 '연결 및 보안' 탭 |
> | `PORT` | `5432` | 기본값 |
> | `DB_NAME` | `swell` | Phase 2-5 |

#### pgvector 확장 활성화
- SWELL의 아이템 추천 시스템은 벡터 유사도 검색을 수행하며, 이를 위해 `pgvector` 확장이 반드시 필요하다.
- DBeaver 또는 TablePlus의 SQL 편집기에서 아래 쿼리를 실행한다.
  ```sql
  -- swell 데이터베이스로 접속된 상태에서 실행
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

---

## Phase 2-5: S3 버킷 및 IAM 자격 증명 구성 (Storage)

> [!IMPORTANT]
> SWELL 백엔드는 사용자 사진과 가상 피팅 결과 이미지를 저장하기 위해 AWS S3를 사용한다. 
> Level 0에서는 단순함을 위해 **버킷의 퍼블릭 액세스를 허용**하여 브라우저에서 직접 이미지를 볼 수 있도록 설정한다.

### 2.5-1. S3 버킷 생성
- **버킷 이름:** 전역적으로 고유한 이름 (예: `swell-storage-yeonguk`)
- **리전:** **`us-east-2` (Ohio)** (EC2, RDS와 동일하게 설정 권장)
- **객체 소유권:** **ACL 비활성화됨 (권장)**
  - 버킷 정책(Bucket Policy)으로만 접근을 제어하며, 개별 객체마다 ACL을 설정할 필요가 없어 관리가 단순해진다.
- **이 버킷의 퍼블릭 액세스 차단 설정:** **모두 체크 해제**
  - "보완적으로 객체가 공개될 수 있음을 알고 있습니다"에 체크한다.
- **이유:** Level 0에서는 CloudFront 없이 S3 URL로 직접 이미지를 서빙하므로 퍼블릭 읽기 권한이 필요하다.

### 2.5-2. 버킷 정책 (Bucket Policy) 설정
1. 생성된 버킷의 **[권한(Permissions)]** 탭으로 이동한다.
2. **[버킷 정책]** 편집을 누르고 아래 JSON을 입력한다 (버킷 이름 수정 필수).
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "PublicReadGetObject",
               "Effect": "Allow",
               "Principal": "*",
               "Action": "s3:GetObject",
               "Resource": "arn:aws:s3:::니-버킷-이름/*"
           }
       ]
   }
   ```

> [!NOTE]
> S3에 파일을 업로드하기 위한 **IAM Access Key**는 Phase 0-3에서 이미 발급을 완료했다. 해당 키를 백엔드 `.env` 파일에 입력하면 된다.

---

## Phase 3: 백엔드 서버 구축 및 실행 (Backend EC2)

> [!NOTE]
> 프론트엔드와 백엔드를 모두 퍼블릭 서브넷에 배치하여 NAT Gateway 없이 통신하는 구조이다.
> 이번 단계에서는 **EC2 인스턴스 생성 → 환경 설정 → 서비스 시작**까지 백엔드 전체 과정을 다룬다.

### Part A: 인스턴스 생성 (AWS 콘솔)

#### 3-1. 인스턴스 이름 및 AMI

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **인스턴스 이름** | `swell-backend` | AWS 콘솔에서 식별하기 위함 |
| **AMI** | **Ubuntu Server 24.04 LTS** | ML 패키지(torch, mediapipe 등) 호환성 검증 사례가 가장 풍부 |

#### 3-2. 인스턴스 유형 및 키 페어

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **인스턴스 유형** | **`t3.medium`** | 벡터 검색 및 이미지 처리에 최소 4GB RAM 필요 |
| **키 페어** | `swell-backend-key` | 생성 및 선택 (`.pem` 파일 안전 보관) |

#### 3-3. 네트워크 및 보안 그룹

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **VPC** | Default VPC | Phase 1에서 확인한 기본 VPC |
| **서브넷** | `us-east-2a` | RDS와 동일한 가용 영역 배치 (지연 최소화) |
| **퍼블릭 IP 자동 할당** | **활성화 (Enable)** | 외부 접속 및 패키지 다운로드 필수 |
| **보안 그룹** | **`swell-backend-sg`** | Phase 1.5에서 미리 생성한 보안 그룹 선택 |

#### 3-4. 스토리지 및 기타 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **스토리지** | **25GB (gp3)** | ML 패키지 및 임시 데이터 저장을 위해 확장 |
| **크레딧** | **표준(Standard)** | 테스트용이므로 예기치 못한 비용 방지 |

#### 3-5. 사용자 데이터 (User Data) 스크립트

- **내용:** EC2 생성 시 **[고급 세부 정보]** 하단의 사용자 데이터 필드에 아래 스크립트를 입력한다.
- **이유:** 인스턴스 부팅 시 자동으로 Python 3.11 설치, 소스코드 클론, 가상환경 구성 등을 완료하여 수동 작업 부담을 줄인다.
- **주의사항:** 패키지 설치 및 환경 구성에 **약 3~5분 정도** 시간이 소요된다. 
- **진행 확인:** 서버 접속 후 `sudo cat /var/log/swell-user-data.log` 명령어를 통해 실시간 진행 상황 및 성공 여부를 확인할 수 있다.

```bash
#!/bin/bash

# ============================================================
# 로그 설정
# ============================================================
LOG_FILE="/var/log/swell-user-data.log"

log_step() {
    local step_name="$1"
    local status="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$status] $step_name" >> "$LOG_FILE"
}

echo "========== SWELL User Data Script Started ==========" > "$LOG_FILE"

# ============================================================
# [1] 시스템 패키지 업데이트
#     → 보안 패치 및 최신 패키지 목록 동기화
# ============================================================
if apt-get update -y && apt-get upgrade -y; then
    log_step "[1] System package update" "SUCCESS"
else
    log_step "[1] System package update" "FAILED"
    exit 1
fi

# ============================================================
# [2] Python 3.11 설치 (deadsnakes PPA 활용)
#     → Ubuntu 24.04의 기본 Python은 3.12이지만, 
#       SWELL 백엔드는 ML 패키지(mediapipe 등) 호환성을 위해 3.11을 사용한다.
# ============================================================
if apt-get install -y software-properties-common && \
   add-apt-repository -y ppa:deadsnakes/ppa && \
   apt-get update -y && \
   apt-get install -y python3.11 python3.11-venv python3.11-dev; then
    log_step "[2] Python 3.11 install" "SUCCESS"
else
    log_step "[2] Python 3.11 install" "FAILED"
    exit 1
fi

# ============================================================
# [3] 필수 시스템 패키지 설치
#     - git: 소스코드 클론용
#     - build-essential: C/C++ 컴파일러 (pip 패키지 빌드)
#     - libpq-dev: PostgreSQL 연결 라이브러리
#     - libgl1, libglib2.0-0t64: mediapipe(OpenCV) 서버 구동용 필수 라이브러리
# ============================================================
if apt-get install -y git build-essential libpq-dev curl unzip \
   libgl1 libglib2.0-0t64; then
    log_step "[3] System packages install" "SUCCESS"
else
    log_step "[3] System packages install" "FAILED"
    exit 1
fi

# ============================================================
# [4] uv 설치 (초고속 Python 패키지 매니저)
#     → pip 대비 월등히 빠른 설치 속도를 제공한다.
# ============================================================
if curl -LsSf https://astral.sh/uv/install.sh | sh; then
    export PATH="/root/.local/bin:$PATH"
    log_step "[4] uv install" "SUCCESS"
else
    log_step "[4] uv install" "FAILED"
    exit 1
fi

# ============================================================
# [5] ~ [7] 소스코드 클론 및 환경 구성
#     → User Data는 root로 실행되지만, 서비스는 ubuntu 사용자 권한으로 
#       구동되어야 편집하기 쉬우니 sudo -u ubuntu를 사용한다.
# ============================================================
sudo -u ubuntu bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'

if sudo -u ubuntu bash <<'USEREOF'
set -e
export PATH="$HOME/.local/bin:$PATH"
cd /home/ubuntu
git clone https://github.com/SWELL-HYU/SWELL.git
cd SWELL/backend
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
USEREOF
then
    log_step "[5-7] Git clone, uv venv, uv pip install, .env copy" "SUCCESS"
else
    log_step "[5-7] Git clone, uv venv, uv pip install, .env copy" "FAILED"
    exit 1
fi

# ============================================================
# [8] Systemd 서비스 등록 (root 권한 필요)
#     → 서버 재부팅 시에도 FastAPI가 자동으로 복구되도록 설정한다.
#     → 상세 설정 및 명령어는 SYSTEMD_REFERENCE.md 문서를 참고한다.
#       (참고: ./SYSTEMD_REFERENCE.md)
# ============================================================
cat <<'EOF' > /etc/systemd/system/swell-backend.service
[Unit]
Description=SWELL FastAPI Backend Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/SWELL/backend
Environment="PATH=/home/ubuntu/SWELL/backend/.venv/bin"
ExecStart=/home/ubuntu/SWELL/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

if systemctl daemon-reload && systemctl enable swell-backend.service; then
    log_step "[8] Systemd service register" "SUCCESS"
else
    log_step "[8] Systemd service register" "FAILED"
    exit 1
fi

echo "========== SWELL User Data Script Completed ==========" >> "$LOG_FILE"
```

### Part B: 서버 설정 및 실행 (SSH 접속 후)

> [!IMPORTANT]
> User Data 스크립트는 환경만 준비할 뿐, 데이터베이스 정보가 담긴 `.env` 파일이 구성되지 않았으므로 서비스가 자동으로 시작되지는 않는다. 수동으로 `.env`를 완성하고 서비스를 시작해야 한다.

#### 3-6. 서버 접속 (SSH)
- 앞서 생성한 키 페어와 퍼블릭 DNS를 사용하여 서버에 접속한다. 
- (예시) `ssh -i swell-backend-key.pem ubuntu@ec2-18-117-142-206.us-east-2.compute.amazonaws.com`

#### 3-7. 환경 변수(`.env`) 설정

> [!TIP]
> 각 값이 무엇인지 모르겠다면 팀원이나 가이드 작성자에게 물어보는 것을 권장한다.

- 백엔드 디렉토리로 이동하여 `.env` 파일을 편집한다.
- `cd ~/SWELL/backend && nano .env`
- **필수 입력 항목:**

| 환경 변수 | 값 | 출처 |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://[USER]:[PW]@[ENDPOINT]:5432/swell` | Phase 2-2, 2-6 |
| `STORAGE_TYPE` | `s3` | 고정값 |
| `AWS_ACCESS_KEY_ID` | (발급받은 키 ID) | Phase 0-3 |
| `AWS_SECRET_ACCESS_KEY` | (발급받은 비밀 키) | Phase 0-3 |
| `AWS_REGION` | `us-east-2` | 고정값 |
| `AWS_S3_BUCKET_NAME` | (생성한 버킷 이름) | Phase 2.5-1 |
| `GOOGLE_API_KEY` | (본인 Gemini API 키) | Google AI Studio |
| `GEMINI_MODEL_ID` | `gemini-2.5-flash-image` | 사용 가능한 모델 ID |
| `CORS_ORIGINS` | `http://localhost:3000` | 나중에 프론트엔드 IP로 변경 |

#### 3-8. 서비스 시작 및 상태 확인

| 명령어 | 용도 |
| :--- | :--- |
| `sudo systemctl start swell-backend.service` | 서비스 시작 |
| `sudo systemctl status swell-backend.service` | 상태 확인 |
| `sudo journalctl -u swell-backend.service -f` | 실시간 로그 확인 |
| `sudo systemctl stop swell-backend.service` | 서비스 중단 |
| `sudo systemctl restart swell-backend.service` | 서비스 재시작 |

- 백엔드 API가 정상 동작하는지 브라우저에서 `http://[EC2-IP]:8000/docs` 접속을 통해 확인한다.

---

## Phase 5: 데이터 주입 및 검증 (Data Injection & Verification)

### 5-1. 데이터 주입 실행
1. 백엔드 서버에서 `scripts/inject_data.sh`를 실행한다. (권한 부여가 안 되어 있으니 `bash` 명령어를 앞에 붙여 실행)
2. 주입 순서: `태그` → `코디` → `테스트 유저` 순서로 진행된다.

### 5-2. 퍼블릭 접속 테스트
- RDS가 퍼블릭이므로 로컬 DBeaver 또는 pgAdmin에서 직접 RDS 엔드포인트로 접속하여 데이터 주입 결과를 확인할 수 있다.

---

## Phase 6: 프론트엔드 서버 구축 및 배포 (Frontend EC2)

> [!NOTE]
> Next.js 프론트엔드를 호스팅할 웹 서버를 구축한다. 백엔드와 마찬가지로 퍼블릭 서브넷에 배치한다.
> 이번 단계에서는 **EC2 인스턴스 생성 → 환경 설정 → 빌드 → 서비스 시작**까지 프론트엔드 전체 과정을 다룬다.

### Part A: 인스턴스 생성 (AWS 콘솔)

#### 6-1. 인스턴스 이름 및 AMI

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **인스턴스 이름** | `swell-frontend` | AWS 콘솔에서 식별하기 위함 |
| **AMI** | **Ubuntu Server 24.04 LTS** | 백엔드와 동일하게 유지하여 관리 편의성 증대 |

#### 6-2. 인스턴스 유형 및 키 페어

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **인스턴스 유형** | **`t3.medium`** | `npm run build`가 매우 무거워 4GB RAM 미만이면 현기증 |
| **키 페어** | `swell-backend-key` | 기존 키 재사용 또는 새 키 생성 |

> [!WARNING]
> `t3.micro`(1GB)나 `t3.small`(2GB) 사양에서는 빌드 도중 멈추거나 속도가 너무 느려서 **현기증이 날 수 있다.** 반드시 **`t3.medium` (4GB RAM)** 이상을 사용할 것.

#### 6-3. 네트워크 및 보안 그룹

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **서브넷** | `us-east-2a` | 백엔드/RDS와 동일한 가용 영역 배치 |
| **퍼블릭 IP 자동 할당** | **활성화 (Enable)** | 외부 접속 필수 |
| **보안 그룹** | **`swell-frontend-sg`** | Phase 1.5에서 미리 생성한 보안 그룹 선택 |

#### 6-4. 스토리지 및 기타 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **스토리지** | **20GB (gp3)** | `node_modules`와 빌드 결과물(`.next`) 용량 고려 |
| **크레딧** | **표준(Standard)** | 테스트용이므로 예기치 못한 비용 방지 |

#### 6-5. 사용자 데이터 (User Data) 스크립트

- **내용:** EC2 생성 시 **[고급 세부 정보]** 하단의 사용자 데이터 필드에 아래 스크립트를 입력한다.
- **이유:** Node.js v22 LTS 및 최신 빌드 도구를 수동 설치 없이 준비한다.
- **주의사항:** 패키지 설치 및 의존성 라이브러리 구성에 **약 1~2분 정도** 시간이 소요된다.
- **진행 확인:** 서버 접속 후 `sudo cat /var/log/swell-frontend-init.log` 명령어를 통해 실시간 진행 상황 및 성공 여부를 확인할 수 있다.

```bash
#!/bin/bash

# ============================================================
# 로그 설정
#     → 스크립트 실행 과정 및 오류를 추적하기 위해 로그를 남긴다.
#       서버 접속 후 'sudo cat /var/log/swell-frontend-init.log'로 확인 가능.
# ============================================================
LOG_FILE="/var/log/swell-frontend-init.log"

log_step() {
    local step_name="$1"
    local status="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$status] $step_name" >> "$LOG_FILE"
}

echo "========== SWELL Frontend Setup Started ==========" > "$LOG_FILE"

# ============================================================
# [1] 시스템 패키지 업데이트
#     → 보안 패치 및 최신 패키지 목록 동기화
# ============================================================
if apt-get update -y && apt-get upgrade -y; then
    log_step "[1] System package update" "SUCCESS"
else
    log_step "[1] System package update" "FAILED"
    exit 1
fi

# ============================================================
# [2] Node.js 22 LTS 설치 (Nodesource 활용)
#     → Next.js 15 및 최신 기능을 안정적으로 구동하기 위해
#       LTS 버전인 Node.js v22를 설치한다.
# ============================================================
if curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
   apt-get install -y nodejs; then
    log_step "[2] Node.js 22 LTS install" "SUCCESS"
else
    log_step "[2] Node.js 22 LTS install" "FAILED"
    exit 1
fi

# ============================================================
# [3] 필수 빌드 도구 설치
#     - git: 프로젝트 소스코드 클론용
#     - build-essential: npm 패키지 중 네이티브 모듈 컴파일 시 필요
# ============================================================
if apt-get install -y git build-essential; then
    log_step "[3] Tools (git, build-essential) install" "SUCCESS"
else
    log_step "[3] Tools (git, build-essential) install" "FAILED"
    exit 1
fi

# ============================================================
# [4] 소스코드 클론 및 환경 구성 (ubuntu 사용자 권한)
#     → -i 옵션을 사용하여 ubuntu 사용자의 환경 변수를 완전히 로드한다.
# ============================================================
if sudo -i -u ubuntu bash <<'USEREOF'
set -e
cd /home/ubuntu
git clone https://github.com/SWELL-HYU/SWELL.git
cd SWELL/frontend
npm install
cp .env.example .env
USEREOF
then
    log_step "[4] Git clone & npm install" "SUCCESS"
else
    log_step "[4] Git clone & npm install" "FAILED"
    exit 1
fi

# ============================================================
# [5] Systemd 서비스 등록 (root 권한 필요)
#     → 서버 재부팅 시에도 Next.js가 자동으로 복구되도록 설정한다.
#     → 단, .env 설정과 npm run build는 수동 완료 후 서비스를 시작해야 함.
# ============================================================
cat <<'EOF' > /etc/systemd/system/swell-frontend.service
[Unit]
Description=SWELL Next.js Frontend Service
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/SWELL/frontend
Environment="NODE_ENV=production"
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

if systemctl daemon-reload && systemctl enable swell-frontend.service; then
    log_step "[5] Systemd service register" "SUCCESS"
else
    log_step "[5] Systemd service register" "FAILED"
    exit 1
fi

# ============================================================
# [6] Nginx 리버스 프록시 설정 (80 -> 3000)
#     → 사용자가 포트 번호(:3000) 없이 80번 포트로 접속할 수 있도록
#       Nginx를 설치하고 리버스 프록시를 구성한다.
#     → 기존 기본 설정과의 충돌을 방지하기 위해 설정을 강제로 초기화한다.
# ============================================================
if apt-get install -y nginx; then
    # 기존 설정 파일 제거 및 새로 작성
    rm -f /etc/nginx/sites-enabled/default
    cat <<'EOF' > /etc/nginx/sites-available/default
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF
    # 심볼릭 링크 생성 (활성화) 및 Nginx 재시작
    ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    nginx -t && systemctl restart nginx
    log_step "[6] Nginx reverse proxy setup" "SUCCESS"
else
    log_step "[6] Nginx reverse proxy setup" "FAILED"
    exit 1
fi

log_step "========== SWELL Frontend Setup Completed ==========" "SUCCESS"
```

### Part B: 프론트엔드 설정 및 배포 (SSH 접속 후)

> [!IMPORTANT]
> User Data 스크립트는 환경만 준비할 뿐, `.env` 설정과 `npm run build`를 완료하기 전까지는 서비스가 자동으로 시작되지 않는다.

#### 6-6. 환경 변수(`.env`) 설정
- 프론트엔드 서버에 SSH 접속 후 `.env` 파일을 백엔드 주소로 수정한다.
- `cd ~/SWELL/frontend && nano .env`
- **필수 입력 항목:**

| 환경 변수 | 값 | 출처 |
| :--- | :--- | :--- |
| `BACKEND_API_URL` | `http://[백엔드-EC2-IP]:8000` | Phase 3 EC2 퍼블릭 IP |

#### 6-7. 빌드 및 서비스 시작

> [!IMPORTANT]
> Next.js는 **빌드 시점에 환경변수를 고정(Baking)**하므로, `.env`를 수정한 후 반드시 빌드해야 한다.

```bash
# 1. 빌드 (약 1~3분 소요)
cd ~/SWELL/frontend && npm run build

# 2. 서비스 시작
sudo systemctl start swell-frontend.service
```

#### 6-8. 서비스 관리 명령어

| 명령어 | 용도 |
| :--- | :--- |
| `sudo systemctl start swell-frontend.service` | 서비스 시작 |
| `sudo systemctl status swell-frontend.service` | 상태 확인 |
| `sudo journalctl -u swell-frontend.service -f` | 실시간 로그 확인 |
| `sudo systemctl stop swell-frontend.service` | 서비스 중단 |
| `sudo systemctl restart swell-frontend.service` | 서비스 재시작 (소스 수정 후 재빌드 시) |

#### 6-9. 접속 확인
- 브라우저에서 `http://[프론트엔드-EC2-IP]` 주소로 접속한다.

> [!TIP]
> **"Welcome to nginx!" 페이지가 나타날 경우:**
> Nginx의 기본 설정이 프록시 설정보다 우선순위를 가질 때 발생한다. 아래 명령어로 설정을 강제 동기화한다.
> ```bash
> sudo rm -f /etc/nginx/sites-enabled/default
> sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
> sudo systemctl restart nginx
> ```

#### 6-10. 백엔드 CORS 설정 업데이트 (보안)
- 프론트엔드 서버가 정상 작동한다면, 백엔드 서버에서도 해당 주소만 허용하도록 설정을 강화해야 한다.
1. **백엔드 서버** 접속: `cd ~/SWELL/backend && nano .env`
2. **환경 변수 수정:**
   - `CORS_ORIGINS=http://[프론트엔드-EC2-IP]` (기존 `localhost:3000` 대신 실제 IP 입력. 80번 포트는 생략 가능)
3. **서비스 재시작:**
   ```bash
   sudo systemctl restart swell-backend.service
   ```

---

## Phase 7: 통합 테스트 및 검증

### 7-1. 통합 테스트 순서

| 순서 | 테스트 항목 | 확인 방법 |
| :--- | :--- | :--- |
| 1 | **백엔드 API 단독 확인** | `http://[백엔드-IP]:8000/docs`에서 Swagger UI 정상 로딩 |
| 2 | **프론트엔드 → 백엔드 API 연결** | 프론트엔드에서 로그인, 아이템 목록 조회 등 API 요청이 정상 전달되는지 확인 |
| 3 | **S3 이미지 표시** | 아이템 이미지, 프로필 사진 등이 정상적으로 브라우저에 렌더링되는지 확인 |
| 4 | **데이터 주입 확인** | Phase 5에서 주입한 태그, 코디, 테스트 유저 데이터가 프론트엔드에 정상 표시되는지 확인 |
| 5 | **CORS 검증** | 브라우저 개발자 도구(F12) → Console에서 CORS 관련 에러가 없는지 확인 |

> [!TIP]
> 문제가 발생하면 아래 순서로 디버깅한다:
> 1. `sudo systemctl status swell-backend.service` — 백엔드 서비스 상태 확인
> 2. `sudo journalctl -u swell-backend.service -f` — 백엔드 실시간 로그
> 3. `sudo journalctl -u swell-frontend.service -f` — 프론트엔드 실시간 로그
> 4. 브라우저 F12 → Network 탭에서 요청 URL과 응답 코드 확인

---

## Phase 8: Next — Level 1에서 해결할 것들

> [!NOTE]
> Level 0은 빠른 프로토타이핑을 위한 구조이다. 아래 보안 이슈는 인지한 상태로 두고, Level 1 전환 시 순차적으로 해결한다.

- [ ] **S3 퍼블릭 액세스 제거** — 현재 버킷이 퍼블릭으로 공개되어 있어, 누구나 URL만 알면 객체에 접근 가능하다. → CloudFront + OAC로 전환
- [ ] **IAM Access Key → IAM Role 전환** — 현재 백엔드 코드가 Access Key로 S3 버킷에 접근하고 있다. EC2에 IAM Role(Instance Profile)을 부착하면 키 없이도 접근이 가능하며 보안이 강화된다.
- [ ] **HTTP → HTTPS 도입** — 현재 모든 통신이 평문(HTTP)으로 전송되고 있다. → ACM 인증서 + ALB를 통해 HTTPS를 적용한다.
- [ ] **RDS 퍼블릭 액세스 제거** — 현재 인터넷에서 직접 DB에 접속할 수 있는 상태이다. → Private Subnet으로 이동하고 Bastion Host 또는 SSM을 통해서만 접근하도록 변경한다.

---

## Appendix: 리소스 전체 삭제 가이드 (Teardown)

> [!CAUTION]
> AWS 리소스는 **의존성의 역순**으로 삭제해야 한다. 순서를 틀리면 "이 리소스를 참조하는 다른 리소스가 있습니다" 에러가 발생하여 삭제가 거부된다.

### 삭제 순서

| 순서 | 리소스 | 삭제 위치 | 왜 이 순서인가? |
| :---: | :--- | :--- | :--- |
| **1** | EC2 인스턴스 2대 (backend, frontend) | EC2 콘솔 → 인스턴스 → 인스턴스 상태 → **종료** | 보안 그룹을 참조 중이므로 먼저 제거 |
| **2** | RDS 인스턴스 (swell-db) | RDS 콘솔 → 데이터베이스 → **삭제** | 보안 그룹을 참조 중이므로 먼저 제거 |
| **3** | 보안 그룹 3개 | EC2 콘솔 → 보안 그룹 → **삭제** | EC2/RDS가 제거된 후에야 삭제 가능 |
| **4** | S3 버킷 | S3 콘솔 → **버킷 비우기** → **버킷 삭제** | 객체가 남아있으면 삭제 불가, 반드시 비우기 먼저 |
| **5** | 키 페어 | EC2 콘솔 → 키 페어 → **삭제** | 독립 리소스, 언제든 삭제 가능 |
| **6** | IAM Access Key | IAM 콘솔 → 사용자 → 보안 자격 증명 → **삭제** | 독립 리소스 |

> [!WARNING]
> - **EC2 "종료" vs "중지"**: "중지(Stop)"는 서버를 끄는 것이고, **"종료(Terminate)"**가 완전 삭제이다. 반드시 **종료**를 선택할 것.
> - **RDS 삭제 시**: "최종 스냅샷 생성" 체크를 해제해야 불필요한 스냅샷 비용이 발생하지 않는다. "자동 백업 보존" 체크도 해제.
> - **S3 삭제 시**: 버킷을 삭제하기 전에 **반드시 "버킷 비우기"**를 먼저 수행해야 한다. 객체가 하나라도 남아있으면 삭제가 거부된다.
> - **보안 그룹 삭제 팁**: 서로를 참조하는 인바운드 규칙이 있으므로, **각 보안 그룹의 인바운드 규칙을 먼저 전부 삭제**한 뒤 보안 그룹 자체를 삭제하면 수월하다.

---