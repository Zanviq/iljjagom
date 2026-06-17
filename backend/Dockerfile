# 일짜곰 백엔드 컨테이너 — 무상태(stateless), 워커 다중화 안전.
# 근거: 03-추가기능/01 §5.1. 실제 배포는 보류, 즉시 배포 가능 상태만 준비.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 의존성 먼저(레이어 캐시). pyproject 의 [project].dependencies 설치.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# 앱 소스만 복사(.env/tests 등은 .dockerignore 로 제외).
COPY app ./app

EXPOSE 8000

# 포트는 호스팅이 PORT 로 주입. --reload 금지(운영). 프록시 뒤 X-Forwarded 처리.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --proxy-headers"]
