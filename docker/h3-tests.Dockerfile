FROM python@sha256:2f17fc044b579bab302c2e8054d3a686e2cb9a83de48e70534b94cd8ebbe06a9
RUN python -m pip install --no-cache-dir pytest==9.0.2 pytest-asyncio==1.3.0 httpx==0.28.1 jsonschema==4.26.0 pydantic==2.12.5 PyYAML==6.0.3
WORKDIR /app
COPY src /app/src
COPY tests/test_linux_cleanup.py /app/tests/test_linux_cleanup.py
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
CMD ["python", "-m", "pytest", "tests/test_linux_cleanup.py", "-q", "-p", "no:cacheprovider", "--tb=short", "--basetemp=/tmp/pytest"]
