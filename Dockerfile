FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN cp main_v2.py main.py || true

CMD ["functions-framework", "--target", "school_agent_http", "--port", "8080"]
