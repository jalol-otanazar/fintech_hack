FROM python:3.11-slim
WORKDIR /app
COPY services/brain/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/brain/ .
COPY services/post-call/crm_adapter.py /app/crm_adapter.py
COPY shared/ /app/shared/
ENV PYTHONPATH=/app
CMD ["python", "main.py"]
