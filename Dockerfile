FROM python:3.13-alpine

RUN pip install uv

RUN uv --version

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --no-dev

COPY . .

EXPOSE 3000

CMD ["uv", "run", "gunicorn", "--workers", "3", \
     "--bind", "0.0.0.0:3000", "wsgi:app"]
