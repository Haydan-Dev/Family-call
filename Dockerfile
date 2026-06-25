# Step 1: Base Linux image with Python 3.11
FROM python:3.11-slim

# Step 2: Container ka main root folder set karo
WORKDIR /app

# Step 3: requirements.txt copy karke dependencies install karo (Cache Layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Pura project (backend + frontend) /app ke andar copy karo
COPY . .

# Step 5: CONTEXT SWITCH - Command chalane se pehle backend folder mein ghuso
WORKDIR /app/backend

# Step 6: Engine Ignition - Sahi path se FastAPI server start karo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]