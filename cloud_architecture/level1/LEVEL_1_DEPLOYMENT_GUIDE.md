# SWELL Level 1 배포 가이드: EC2 Standard Architecture

> **목적:** Level 0의 간소화된 구조를 넘어, 보안이 강화된 **EC2 Standard Architecture**를 구축한다.
> **아키텍처 다이어그램:** [level1.py](./level1.py)에서 생성된 `level1_architecture.png` 참조.
> **핵심 변경 사항:** 데이터 보호를 위해 **백엔드(FastAPI)와 RDS를 프라이빗 서브넷(Private Subnet)으로 이동**시키고, 커스텀 VPC를 통해 네트워크 격리를 구현한다. (CSR 환경이지만 Next.js Rewrite/Proxy를 통해 프론트엔드 서버가 내부 통신을 대행하므로 백엔드 은닉이 가능하다.)

> [!TIP]
> Level 1부터는 네트워크 구조가 복잡해지므로, 리소스 생성 시 "VPC"와 "서브넷" 선택이 올바르게 되었는지 매 단계마다 확인하는 것이 필수적이다.

---

## Phase 0: IAM 사용자, 그룹 및 인스턴스 역할 구성

- **0-1. IAM 사용자 및 그룹:** 관리자 사용자 추가 및 Access Key 발급 과정은 이전 자료를 참고한다.
  - **참고:** [Level 0 배포 가이드 - Phase 0](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L11)
- **0-2. EC2 인스턴스 역할 생성 (Instance Profile):**
  - **목적:** 프라이빗 EC2는 이 역할이 없으면 Session Manager 접속이 불가능하여 서버가 고립된다. EC2 생성 시점에 바로 부착할 수 있도록 미리 생성해둔다.
  - **역할 이름:** `swell-backend-role`
  - **필수 연결 정책:**
    1. **`AmazonSSMManagedInstanceCore`**: 프라이빗 인스턴스 원격 접속(SSM)을 위한 핵심 권한. ([AWS 공식 문서](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonSSMManagedInstanceCore.html))
    2. **`AmazonS3FullAccess`** (Level 2 예정): S3 정적 자산 처리용 권한.
       - **참고:** Level 1에서는 기존 .env의 Access Key 방식을 유지하며, IAM 역할을 통한 보안 접근(Role-based access)은 Level 2에서 다룬다.

---

## Phase 1: 커스텀 VPC 및 서브넷 구성 (Private Network)

> [!IMPORTANT]
> **Level 0 대비 변경점:** 
> - **Default VPC** 대신 **커스텀 VPC**를 생성한다.
> - 모든 리소스가 퍼블릭에 노출되는 대신, 역할을 기준으로 **퍼블릭(Public)**과 **프라이빗(Private)** 서브넷으로 분리한다.

### 1-1. VPC 및 서브넷 생성
- **내용:** AWS 콘솔의 **[VPC 생성] → [VPC 등]** 마법사를 사용하여 아래 구조를 한 번에 생성한다.
  - **이름:** `swell` (예시)
  - **CIDR 블록:** `10.0.0.0/24`
  - **가용 영역(AZ) 개수:** 2개 (RDS 서브넷 그룹 요건 충족을 위해 권장)
  - **퍼블릭 서브넷 개수:** 2개 (프론트엔드 및 NAT Gateway 배치용)
  - **프라이빗 서브넷 개수:** 2개 (**백엔드 및 RDS 배치용**)
  - **NAT 게이트웨이:** **1개의 AZ에서(In 1 AZ)** 또는 **리전별-신규 선택**
  - **VPC 엔드포인트:** **없음 (None)** (S3 Gateway 등은 보안 및 비용 최적화를 위해 다음 단계인 Level 2에서 다룰 예정)
- **이유:** 외부 인터넷과 차단된 프라이빗 서브넷 리소스들이 패키지 설치 및 외부 API(Gemini)와 통신할 수 있는 경로를 확보하기 위함이다.
- **이유:** RDS는 고가용성을 위해 최소 2개의 가용 영역에 걸친 서브넷 그룹을 요구하므로, 프라이빗 서브넷을 복수 가용 영역에 배치한다.

### 1-2. NAT 게이트웨이 및 라우팅 확인
- **내용:** 프라이빗 서브넷의 라우팅 테이블이 인터넷 게이트웨이(IGW)가 아닌 **NAT Gateway**를 향하고 있는지 확인한다.
- **이유:** 프라이빗 서브넷에 배치된 백엔드 EC2가 Gemini API 호출이나 패키지 설치를 위해 인터넷에 접속해야 하기 때문이다. (외부에서 들어오는 것은 차단, 나가는 것만 허용)

---

## Phase 1.5: 보안 그룹 구성 (Security Groups)

> [!IMPORTANT]
> **Level 1의 핵심:** DB 보안 그룹(`swell-db-private-sg`)에서 **내 IP(My IP) 접근 권한을 제거**하고, 오직 백엔드 서버만이 DB에 접속할 수 있도록 폐쇄적인 구조를 만든다. (**VPC 선택:** `swell`)

### 1.5-1. `swell-db-private-sg` (데이터베이스용)
- **용도:** 프라이빗 서브넷의 RDS에 부착
- **인바운드 규칙:**
  - **PostgreSQL (5432):** **`swell-backend-sg`** — 백엔드 서버의 접근만 허용
  - **(제거)** 내 IP 접속 규칙 — 외부에서의 직접 접근을 원천 차단한다.

### 1.5-2. `swell-backend-sg` (백엔드 서버용)
- **용도:** **프라이빗 서브넷**의 백엔드 EC2에 부착 (VPC 외부 직접 접근 차단)
- **인바운드 규칙:**
  - **사용자 지정 TCP (8000):** **`swell-frontend-sg`** — 프론트엔드 서버(Proxy)의 API 요청만 허용

### 1.5-3. `swell-frontend-sg` (프론트엔드 서버용)
- **용도:** 퍼블릭 서브넷의 프론트엔드 EC2에 부착
- **인바운드 규칙:** [Level 0 내용과 동일하게 유지]

---

## Phase 2: RDS (PostgreSQL) 데이터베이스 생성 (Private)

> [!IMPORTANT]
> **Level 0 대비 변경점:** 
> - **퍼블릭 액세스:** **아니요(No)**

### 2-1. 연결 및 네트워크 설정
- **VPC:** Phase 1에서 생성한 커스텀 VPC 선택
- **DB 서브넷 그룹:** **새로운 DB 서브넷 그룹 생성 및 선택** (Phase 1에서 만든 프라이빗 서브넷들 포함)
- **퍼블릭 액세스:** **아니요 (No)** (가장 중요한 설정)
- **가용 영역(AZ):** **`us-east-2a`** (추후 백엔드도 동일하게 선택)
- **보안 그룹:** **`swell-db-private-sg`** 선택

### 2-2. 성능 및 옵션 설정
- 기타 엔진 버전(17.x), 인스턴스 유형(`db.t3.micro`), 초기 데이터베이스 이름(`swell`) 등 기본 설정은 Level 0와 동일하게 유지한다.

### 2-3. 생성 후 작업: 접속 테스트
- RDS가 프라이빗에 있으므로 로컬에서 직접 접속은 불가능하다.
- **테스트 방법:** 추후 백엔드 EC2에 접속(SSM)한 후, `telnet [RDS-엔드포인트] 5432` 명령을 통해 네트워크 연결이 살아있는지 확인한다. (상세 절차는 하단 **Phase 3-6** 참고)

---

## Phase 2-5: S3 버킷 및 IAM 자격 증명 구성

- **내용:** S3 버킷 생성, 퍼블릭 읽기 권한 설정(Bucket Policy), IAM Access Key 발급 과정은 이전 자료를 참고한다.
- **참고:** [Level 0 배포 가이드 - Phase 2-5](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L172)
- **이유:** 정적 자산(이미지) 저장 및 처리를 위한 S3 구성 방식은 Level 1에서도 동일하게 유지된다. (Level 2부터는 CloudFront OAC 등을 통한 보안 강화가 고려된다.)

---

## Phase 3: 백엔드 서버 구축 및 실행 (Backend EC2)

### Part A: 인스턴스 생성 (AWS 콘솔)

> [!IMPORTANT]
> **Level 1 보안 강화 핵심:** 외부 노출을 원천 차단하기 위해 **프라이빗 서브넷**에 배치하며, SSH 대신 **SSM Session Manager**를 통한 접속 체계로 전환한다.

#### 3-1. 서버 위치 및 네트워크 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **VPC** | `swell` | 커스텀 VPC 선택 |
| **서브넷** | `Private Subnet in us-east-2a` | 외부 노출 방지 및 RDS와 동일 AZ 권장 |
| **퍼블릭 IP 자동 할당** | **비활성화 (Disable)** | 프라이빗 서브넷 원칙 준수 |
| **보안 그룹** | **`swell-backend-sg`** | Phase 1.5에서 생성한 보안 그룹 선택 |

#### 3-2. IAM 및 시스템 관리 구성

| 항목 | 설정값 | 이유 |
| :--- | :--- | :--- |
| **IAM 인스턴스 프로파일** | `swell-backend-role` | **Phase 0-2에서 만든 역할 (SSM 접속 필수)** |

> [!TIP]
> **보안 그룹 통신 확인 (설정 이유):**
> - **EC2 ↔ SSM (아웃바운드 통신 확인):** SSM Agent는 EC2에서 AWS 서비스로 먼저 연결을 시도(Outbound)한다. 보안 그룹의 **기본 아웃바운드 규칙(모든 트래픽 0.0.0.0/0)**이 유지되고 있다면 별도 설정 없이 작동한다. 단, 보안 강화를 위해 기본 규칙을 삭제한 경우 **아웃바운드 443(HTTPS)**은 모든 대상(`0.0.0.0/0`)에 대해 반드시 열려 있어야 Session Manager 접속이 가능하다. (인바운드 규칙은 필요 없음)

- **설정 안내:** AMI(Ubuntu 24.04), 인스턴스 유형(t3.medium), 스토리지(25GB) 및 전체 설치 스크립트 등 세부 구성은 Level 0 자료를 참고한다.
- **주의 사항:** RDS 접속 테스트(psql) 및 관리를 위해, 인스턴스 생성 시 **사용자 데이터(User Data)** 스크립트의 패키지 설치 목록(`apt install`)에 `postgresql-client`를 추가로 포함하여 생성한다. (수동 설치의 번거로움을 줄이기 위함)
- **참고:** [Level 0 배포 가이드 - Phase 3 Part A](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L210)

### Part B: 서버 설정 및 실행 (SSM 접속 후)

> [!IMPORTANT]
> 백엔드 EC2가 프라이빗 서브넷에 위치하므로, 기존의 SSH 방식(22번 포트)이 아닌 **AWS SSM Session Manager**를 통해 접속한다. 서버 접속 후의 설정 과정은 Level 0와 유사하지만, 네트워크 격리에 따른 차이점에 유의한다.

#### 3-4. 서버 접속 (SSM Session Manager)
- AWS 콘솔의 EC2 인스턴스 목록에서 백엔드 인스턴스를 선택하고 **[연결]** 버튼을 클릭한다.
- **[세션 관리자(Session Manager)]** 탭을 선택하고 **[연결]**을 클릭하여 브라우저 기반의 터미널을 연다.
- SSM은 기본적으로 `ssm-user`라는 별도 계정으로 접속되기 때문에, `sudo su - ubuntu` 명령어를 통해 프로젝트가 설치된 `ubuntu` 계정으로 전환해야 원활한 작업이 가능하다. 그래야 `/home/ubuntu`에 설치된 소스 코드와 권한이 일치한다.

> [!TIP]
> **개발자 생산성(DX) 개선 팁:** 
> 웹 콘솔 터미널이 불편하다면, 로컬 PC의 SSH 설정을 통해 **VS Code Remote SSH**로 프라이빗 서버에 직접 접속할 수 있다. (기존 SSH 방식이 아니므로 22번 포트를 열 필요가 없어 안전하다.) 상세 설정 방법은 아래 **Phase 7**의 과제 항목을 참고한다.

#### 3-5. 설치 진행 상황 확인 (중요)
- Level 1은 프라이빗 서브넷 환경이므로 NAT Gateway를 통한 외부 통신(패키지 설치 등)이 정상적으로 완료되었는지 확인이 필수적이다.
- 아래 명령어를 통해 User Data 스크립트의 실행 로그를 확인한다.
- `sudo tail -f /var/log/swell-user-data.log`
- 로그 마지막에 `SUCCESS` 메시지들이 출력되고 설치가 완료되었는지 확인한다.

#### 3-6. RDS 연결 확인 (Connectivity Test)
- `.env` 파일을 설정하기 전, 프라이빗 백엔드 EC2에서 RDS로의 네트워크 통신이 가능한지 먼저 확인한다.
- **명령어:** `telnet [RDS-엔드포인트] 5432` 또는 `nc -zv [RDS-엔드포인트] 5432`
- **성공 시:** `Connected to ...` 또는 `open` 메시지가 출력된다. 만약 타임아웃이 발생한다면 보안 그룹(Phase 1.5-1) 설정을 재점검해야 한다.
- **참고 (telnet 종료):** 연결 성공 후 빠져나오려면 `Ctrl + ]`를 누른 뒤 `quit`을 입력하고 `Enter`를 친다. (또는 `nc`를 사용하면 자동으로 종료되어 더 편리하다.)

#### 3-7. RDS 확장(Extension) 활성화 (필수)
- SWELL의 핵심 기능인 벡터 검색을 위해 PostgreSQL의 `pgvector` 확장을 활성화해야 한다. 이 작업은 데이터베이스 생성 후 최초 1회만 수행한다.
- **RDS 접속:** (ubuntu 계정 전환 상태에서)
  - `psql -h [RDS-엔드포인트] -U [사용자명] -d swell`
- **쿼리 실행:**
  - `CREATE EXTENSION IF NOT EXISTS vector;`
- **확인 및 종료:**
  - `\dx` 명령으로 `vector`가 목록에 있는지 확인한 뒤 `\q`로 빠져나온다.

#### 3-8. 환경 변수(`.env`) 설정

- 백엔드 디렉토리로 이동하여 `.env` 파일을 편집한다.
- `cd ~/SWELL/backend && nano .env`
- **설정 항목:** 각 변수값은 [Level 0 배포 가이드](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L394)와 동일하다. 단, `DATABASE_URL`은 Phase 2-1에서 확인한 **RDS 엔드포인트**를 사용해야 함에 유의한다.
- 편집 완료 후 `Ctrl+O`, `Enter`, `Ctrl+X` 명령어로 저장하고 빠져나온다.

#### 3-9. 서비스 시작 및 상태 확인
- **내용:** 서비스 가동 및 관리를 위한 `systemctl` 명령어는 [Level 0 배포 가이드](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L416)와 동일하게 사용한다.
- **차이점 (중요):** 백엔드가 프라이빗 서브넷에 위치하므로, 브라우저에서 인스턴스 IP를 통해 API 문서(`docs`)에 직접 접속하여 확인하는 것은 불가능하다.
- **성공 여부 판단:** `sudo journalctl -u swell-backend.service -f` 명령어 실행 시, 로그에 `Application startup complete.` 메시지가 출력되고 에러가 없는지 확인한다. 최종적인 동작 확인은 Phase 4 프론트엔드 배포 후 수행한다.

---

## Phase 4: 데이터 주입 (Data Injection)

### 4-1. 데이터 주입 실행
- **내용:** 백엔드 서비스 가동 후, 초기 데이터(태그, 코디, 테스트 유저 등)를 주입하는 과정은 [Level 0 배포 가이드 - 5-1](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L429)과 동일하게 수행한다.
- **실행 위치:** SSM으로 접속한 백엔드 EC2 내부 (`~/SWELL/backend/scripts`)
- **수행 방법:** `.env` 설정이 완료된 상태에서 `bash inject_data.sh` 명령어를 실행한다.

---

## Phase 5: 프론트엔드 서버 구축 및 실행 (Frontend EC2)

### 5-1. 인스턴스 생성 및 네트워크 설정
- **기본 가이드:** AMI, 인스턴스 유형(t3.medium 권장), 사용자 데이터 등은 [Level 0 가이드](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L450)를 참고한다.
- **네트워크 차이점:**
  - **VPC:** `swell` (커스텀 VPC) 선택
  - **서브넷:** **Public Subnet 1** (`us-east-2a`) 선택
  - **퍼블릭 IP 자동 할당:** **활성화 (Enable)** (사용자가 직접 접속해야 하므로 필수)
  - **보안 그룹:** **`swell-frontend-sg`** 선택

### 5-2. 서버 접속 및 환경 설정
- **접속 방법:** 퍼블릭 서브넷에 있으므로 기존과 동일하게 **SSH**로 접속한다.
- **환경 변수(`.env`) 설정:**
  - `cd ~/SWELL/frontend && nano .env`
  - **`NEXT_PUBLIC_API_URL`**: 백엔드 EC2의 **Private IP**를 입력한다. (예: `http://10.0.0.x:8000`)
  - **이유:** CSR 환경임에도 Private IP가 가능한 이유는 **Next.js Rewrite(Proxy)** 기능을 통해 프론트엔드 서버(Node.js)가 백엔드와 직접 통신을 대행하기 때문이다. 두 인스턴스는 **동일한 VPC 내부**에 존재하므로, 인터넷을 거치지 않고 AWS 가상 네트워크 망 내에서 Private IP를 통해 훨씬 빠르고 안전하게 데이터를 주고받을 수 있다.

### 5-3. 서비스 시작 및 검증
- [Level 0 가이드](../level0/LEVEL_0_DEPLOYMENT_GUIDE.md#L570)의 절차에 따라 빌드 및 서비스를 시작한다.
- 브라우저에서 프론트엔드 EC2의 **Public IP**로 접속하여 정상 동작 여부를 확인한다.

---

## Phase 6: 통합 테스트 및 검증

### 6-1. 통합 테스트 순서

| 순서 | 테스트 항목 | 확인 방법 및 주의사항 |
| :--- | :--- | :--- |
| 1 | **프론트엔드 서비스 접속** | 브라우저에서 `http://[프론트엔드-Public-IP]` 접속 확인 |
| 2 | **백엔드 API 연결 확인** | 프론트엔드 페이지에서 로그인, 아이템 조회 등이 정상인지 확인. <br>※ 백엔드가 프라이빗에 있으므로 직접 Swagger(`docs`) 접속은 불가능하다. |
| 3 | **프라이빗 리소스 간 통신** | 프론트엔드(Public) → 백엔드(Private) → RDS(Private) 경로가 정상인지 확인. |
| 4 | **S3 이미지 렌더링** | 아이템 이미지 등이 정상 표시되는지 확인. |
| 5 | **CORS 검증** | 브라우저 F12 콘솔에서 에러가 없는지 확인. |

> [!TIP]
> **디버깅 가이드 (접속 안 될 때):**
> 1. **프론트엔드 EC2:** `sudo journalctl -u swell-frontend.service -f` 로그 확인.
> 2. **백엔드 EC2 (SSM 접속):** `sudo journalctl -u swell-backend.service -f` 로그 확인.
> 3. **보안 그룹:** 프론트엔드 SG의 아웃바운드와 백엔드 SG의 8000번 인바운드 설정 재확인.

---

## Phase 7: Next — Level 2에서 해결할 것들

> [!NOTE]
> Level 1은 표준 VPC 구조를 완성한 단계이다. 여전히 남아있는 S3 보안 및 통신 평문 전송 문제는 Level 2 전환 시 순차적으로 해결한다.

- [ ] **S3 퍼블릭 액세스 완전 차단** — 현재 버킷 정책이 퍼블릭 읽기를 허용하고 있다. → CloudFront + OAC(Origin Access Control)를 연동하여 정적으로 노출되는 URL을 보호한다.
- [ ] **IAM Access Key 제거 및 Instance Profile 적용** — 현재 백엔드 `.env`에 하드코딩된 Access Key를 제거한다. EC2에 부여된 `swell-backend-role`을 통해 애플리케이션이 투명하게 S3 권한을 획득하도록 개선한다.
- [ ] **S3 VPC 엔드포인트(Gateway) 도입** — 백엔드 EC2가 S3와 통신할 때 NAT Gateway를 거치지 않고 AWS 내부망을 직접 이용하도록 개선하여 보안과 성능(비용 절감)을 동시에 챙긴다.
- [ ] **개발 환경 DX(Developer Experience) 개선**
  - **SSM + ProxyCommand:** 로컬 PC의 `~/.ssh/config` 설정을 통해 AWS CLI를 거쳐 VS Code로 프라이빗 서버에 접속한다. ([AWS 공식 블로그 참고](https://aws.amazon.com/ko/blogs/aws/new-port-forwarding-using-aws-systems-manager-sessions-manager/))
  - **EC2 Instance Connect Endpoint 도입:** NAT Gateway 없이도 프라이빗 서버에 안전하게 SSH 터널을 뚫을 수 있는 최신 방식을 테스트한다.

---

## Appendix: 리소스 전체 삭제 가이드 (Teardown)

> [!CAUTION]
> **NAT Gateway와 RDS는 생성만으로 비용이 발생한다.** 실습이 끝났다면 반드시 아래 순서에 따라 삭제를 진행한다. 특히 **커스텀 VPC** 리소스는 의존성으로 인해 삭제가 까다로우니 주의한다.

### 삭제 순서 (의존성 역순)

| 순서 | 리소스 카테고리 | 삭제 항목 | 주의 사항 |
| :---: | :--- | :--- | :--- |
| **1** | **EC2** | 인스턴스 2대 (`terminate`) | 종료 후 보안 그룹 삭제가 가능해진다. |
| **2** | **RDS** | DB 인스턴스 (`swell-db`) | 삭제 시 "최종 스냅샷 생성" 체크 해제. |
| **3** | **Network** | **NAT Gateway** | **가장 먼저 명시적으로 삭제**해야 하며, 상태가 `Deleted`가 될 때까지 기다린다. |
| **4** | **IP** | **Elastic IP (탄력적 IP)** | NAT Gateway 삭제 후 반드시 **릴리스(Release)** 해야 비용이 안 나간다. |
| **5** | **Security** | 보안 그룹 3개 | 다른 리소스를 참조하는 규칙이 있다면 규칙 먼저 삭제. |
| **6** | **VPC** | 커스텀 VPC (`swell`) | NAT Gateway가 완전히 삭제된 후에야 VPC 전체 삭제가 가능하다. |
| **7** | **Storage** | S3 버킷 | 반드시 "버킷 비우기" 후 삭제. |
| **8** | **IAM/Key** | IAM 역할, 유저, 키 페어 | 독립 리소스이므로 언제든 삭제 가능. |

> [!IMPORTANT]
> **VPC 삭제 팁:** AWS VPC 콘솔에서 해당 VPC를 선택하고 **[작업] → [VPC 삭제]**를 누르면 서브넷, 라우팅 테이블, 인터넷 게이트웨이 등을 한꺼번에 지워준다. 단, **NAT Gateway가 `Deleted` 상태**여야 하며, 연결된 EC2/RDS가 없어야 한다.

---
