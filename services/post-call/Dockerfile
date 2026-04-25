FROM python:3.11-slim
WORKDIR /app
COPY services/post-call/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/post-call/ /app/services/post_call/
COPY shared/ /app/shared/
COPY config/ /app/config/
ENV PYTHONPATH=/app
WORKDIR /app/services/post_call
CMD ["python", "main.py"]
