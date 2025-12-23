# AWS Monitoring

AWS 서버의 시스템 상태(CPU, 메모리, 디스크), 네트워크 트래픽, 그리고 특정 프로세스의 상태를 모니터링하여 텔레그램으로 알림을 보내는 Python 스크립트입니다.

## 주요 기능

*   **시스템 모니터링**: CPU, 메모리, 디스크 사용량을 실시간으로 확인합니다.
*   **네트워크 모니터링**: 데이터 송수신량을 확인합니다.
*   **프로세스 감시**: 특정 키워드(예: `NS`)가 포함된 프로세스를 필터링하여 상태(CPU, 메모리 점유율)를 보여줍니다.
*   **텔레그램 알림**: 수집된 정보를 보기 좋은 HTML 형식으로 텔레그램 봇을 통해 전송합니다.

## 설치 방법

1.  저장소를 클론합니다.
    ```bash
    git clone https://github.com/dspshin/aws-monitoring.git
    cd aws-monitoring
    ```

2.  필요한 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

## 설정 방법

1.  `.env.example` 파일을 복사하여 `.env` 파일을 생성합니다.
    ```bash
    cp .env.example .env
    ```

2.  `.env` 파일을 열어 텔레그램 봇 토큰와 채팅 ID, 감시할 프로세스 키워드를 입력합니다.
    ```ini
    TELEGRAM_BOT_TOKEN=your_bot_token
    CHAT_ID=your_chat_id
    PROCESS_FILTER=NS
    ```
    *   `PROCESS_FILTER`: 감시하고 싶은 프로세스 이름의 일부(키워드)를 입력합니다. (기본값: NS)

## 사용 방법

스크립트를 직접 실행하여 모니터링 리포트를 전송합니다.

```bash
python screenshot.py
```

주기적으로 실행하려면 `crontab`이나 윈도우 스케줄러에 등록하여 사용할 수 있습니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.
