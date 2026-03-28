FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gitlab_reviewer.py .

EXPOSE 5050

CMD ["python", "gitlab_reviewer.py"]
