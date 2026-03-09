# Systemd 서비스 등록 레퍼런스

> **목적:** SWELL 백엔드(FastAPI)를 Linux EC2 서버에 영구 등록하여,
> 서버 재부팅이나 앱 크래시 시에도 자동으로 복구되게 하는 Systemd 설정을 상세히 기록한다.

---

## 1. Systemd란?

Linux(Ubuntu)의 **프로세스 관리자**이다. "이 프로그램을 백그라운드에서 계속 실행해줘"라고 OS에 등록할 수 있는 시스템이다.

- 터미널을 닫아도 프로세스가 죽지 않는다.
- 서버가 재부팅되어도 자동으로 다시 시작된다.
- 프로세스가 크래시해도 자동으로 재시작해준다.

Systemd 없이 단순히 `uvicorn main:app`을 터미널에서 실행하면, 터미널 세션이 끊기는 순간 FastAPI도 같이 죽는다.

---

## 2. 서비스 파일 구조

서비스 파일은 `/etc/systemd/system/` 디렉토리에 `.service` 확장자로 저장한다.

### SWELL 백엔드 서비스 파일

```ini
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
```

---

## 3. 각 섹션 상세 설명

### 3-1. `[Unit]` 섹션 — "이 서비스가 뭔지" 소개

| 항목 | 값 | 의미 |
| :--- | :--- | :--- |
| `Description` | `SWELL FastAPI Backend Service` | 서비스 설명. `systemctl status`로 조회할 때 표시된다. |
| `After` | `network.target` | **"네트워크가 올라온 뒤에 이 서비스를 시작해라."** FastAPI가 RDS(DB)와 통신해야 하므로, 네트워크가 먼저 준비되어야 한다. |

### 3-2. `[Service]` 섹션 — "어떻게 실행할지" 구체적인 방법

| 항목 | 값 | 의미 |
| :--- | :--- | :--- |
| `User` | `ubuntu` | 이 서비스를 **`ubuntu` 사용자 권한**으로 실행한다. root로 실행하면 보안 위험이 크므로 일반 사용자로 제한한다. |
| `Group` | `ubuntu` | 마찬가지로 그룹 권한도 `ubuntu`로 설정한다. |
| `WorkingDirectory` | `/home/ubuntu/SWELL/backend` | **작업 디렉토리**. `main.py`가 있는 위치이다. uvicorn이 `main:app`을 찾을 때 이 경로를 기준으로 한다. `.env` 파일도 이 경로에서 읽는다. |
| `Environment` | `PATH=.../venv/bin` | **가상환경의 `bin/` 폴더를 PATH에 등록**한다. 이것이 없으면 시스템 Python(3.12)을 사용해버려서, 우리가 설치한 3.11 가상환경의 패키지들을 찾지 못한다. |
| `ExecStart` | `.../uvicorn main:app ...` | **실제 실행 명령어**. 가상환경 안의 uvicorn을 **절대경로**로 지정하여, `main.py`의 `app` 객체를 8000번 포트에서 서빙한다. `--host 0.0.0.0`은 같은 VPC 내 다른 EC2(프론트엔드)에서도 접근 가능하게 한다. |
| `Restart` | `always` | **🔥 핵심!** 프로세스가 어떤 이유로든 죽으면(크래시, OOM 등) systemd가 **자동으로 다시 살려준다.** |
| `RestartSec` | `3` | 재시작 시 **3초 대기** 후 다시 실행한다. 즉시 재시작하면 연쇄 크래시 시 리소스를 과도하게 소모할 수 있어 쿨다운을 준다. |

### 3-3. `[Install]` 섹션 — "언제 자동 시작할지"

| 항목 | 값 | 의미 |
| :--- | :--- | :--- |
| `WantedBy` | `multi-user.target` | 서버가 **`multi-user.target` 단계에 도달하면** 이 서비스를 자동으로 시작한다. |

---

## 4. Linux 부팅 단계(Target)와 `multi-user.target`

Linux 서버가 부팅되면 다음과 같은 **단계(target)**를 순서대로 거친다:

```
전원 ON → BIOS → 커널 로딩 → sysinit.target → basic.target
    → multi-user.target (✅)  → graphical.target (데스크톱용)
```

| target | 상태 | 설명 |
| :--- | :--- | :--- |
| `sysinit.target` | 최초 단계 | 파일시스템 마운트, 하드웨어 초기화 |
| `basic.target` | 기본 준비 | 타이머, 소켓 등 기본 서비스 준비 |
| **`multi-user.target`** | **일반 서버 상태** | **네트워크, 로그인, 사용자 서비스가 모두 준비된 상태. EC2 서버가 "정상 가동"에 도달한 시점.** |
| `graphical.target` | GUI 상태 | 데스크톱 환경 로드 (서버에는 해당 없음) |

> [!IMPORTANT]
> **`WantedBy=multi-user.target`** 과 **`systemctl enable`** 은 반드시 **둘 다** 있어야 재부팅 시 자동 시작이 동작한다.
>
> - `WantedBy=multi-user.target` = "서버가 정상 가동 상태에 도달하면 나를 같이 시작해줘"라고 **희망사항을 서비스 파일에 기록**하는 것.
> - `systemctl enable` = 그 희망사항을 **실제로 활성화**하는 명령. 내부적으로 심볼릭 링크(symbolic link)를 생성하여 부팅 순서에 이 서비스를 편입시킨다.
>
> 하나라도 빠지면 재부팅 후 수동으로 `systemctl start`를 쳐야 한다.

---

## 5. 주요 systemctl 명령어 정리

| 명령어 | 용도 |
| :--- | :--- |
| `systemctl daemon-reload` | 서비스 파일을 새로 만들거나 수정한 뒤, systemd에게 "설정 파일 다시 읽어"라고 알린다. |
| `systemctl enable swell-backend.service` | 부팅 시 자동 시작을 **활성화**한다. |
| `systemctl start swell-backend.service` | 서비스를 **지금 바로 시작**한다. |
| `systemctl stop swell-backend.service` | 서비스를 **정지**한다. |
| `systemctl restart swell-backend.service` | 서비스를 **재시작**한다. (코드 업데이트 후 사용) |
| `systemctl status swell-backend.service` | 서비스의 **현재 상태**, 최근 로그를 확인한다. |
| `journalctl -u swell-backend.service -f` | 서비스의 **실시간 로그**를 tail한다. 디버깅 시 필수. |

---

## 6. SWELL에서의 사용 흐름

```
[1] User Data 스크립트가 서비스 파일 생성 + daemon-reload + enable
        ↓
[2] SSM으로 접속하여 .env 파일 편집 (DATABASE_URL, API Key 등)
        ↓
[3] sudo systemctl start swell-backend.service  ← 이 한 줄로 서비스 가동!
        ↓
[4] systemctl status swell-backend.service  ← 정상 동작 확인
        ↓
[5] 이후 서버 재부팅되면? → enable이 걸려있으므로 자동 시작됨 ✅
[6] 이후 앱이 크래시하면? → Restart=always이므로 3초 후 자동 복구됨 ✅
```

---

## 7. 참고 자료

### 공식 문서

- [systemd.service — Service Unit Configuration (freedesktop.org)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — `[Service]` 섹션의 모든 옵션 사전
- [systemd.unit — Unit Configuration (freedesktop.org)](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html) — `[Unit]`, `[Install]` 섹션 옵션 사전
- [systemctl(1) — Manual Page](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html) — `systemctl` 명령어의 공식 사용법
- [journalctl(1) — Manual Page](https://www.freedesktop.org/software/systemd/man/latest/journalctl.html) — 로그 조회 명령어 공식 사용법

### 튜토리얼 & 가이드

- [DigitalOcean — Understanding Systemd Units and Unit Files](https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files) — Systemd 전반을 이해하기 좋은 입문 가이드
- [DigitalOcean — How To Use Systemctl to Manage Systemd Services](https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units) — `systemctl` 명령어 실전 활용법
- [Uvicorn Deployment — Running with Systemd](https://www.uvicorn.org/deployment/#running-behind-nginx) — Uvicorn을 Systemd로 등록하는 공식 가이드

### 검색 키워드

- `systemd service file tutorial`
- `systemctl enable vs start difference`
- `WantedBy multi-user.target explained`
- `uvicorn systemd deployment fastapi`
- `journalctl follow service logs`
