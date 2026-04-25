FROM python:3.11-slim
WORKDIR /app
COPY services/brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/brain/ .
COPY shared/ /app/shared/
ENV PYTHONPATH=/app
CMD ["python", "main.py"]
