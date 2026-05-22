From python:3.11
WORKDIR /app
copy requirements.txt .
RUN pip install -r requirements.txt
copy . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]  