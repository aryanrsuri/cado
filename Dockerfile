FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
        "fastapi[standard]>=0.125.0" \
        "jinja2>=3.1.6" \
        "sqlmodel>=0.0.27" \
        "pymysql>=1.1.0" \
        "cryptography>=42.0.0"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
