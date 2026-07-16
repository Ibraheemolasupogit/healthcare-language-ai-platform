FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HEALTHCARE_LANGUAGE_AI_ENVIRONMENT=local \
    HEALTHCARE_LANGUAGE_AI_SYNTHETIC_DATA_ONLY=true

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md LICENSE ./
COPY config ./config
COPY dashboard ./dashboard
COPY docs ./docs
COPY reports ./reports
COPY schemas ./schemas
COPY src ./src
COPY tests/fixtures ./tests/fixtures

RUN mkdir -p data outputs reports \
    && chown -R app:app /app

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

USER app

CMD ["healthcare-language-ai", "validate-environment"]
