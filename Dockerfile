FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
COPY alembic.ini ./alembic.ini
COPY alembic ./alembic

RUN pip install --upgrade pip && pip install -e .

CMD ["uvicorn", "research_pulse_cn.main:app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
