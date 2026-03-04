FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create directory for sample data (mounted at runtime)
RUN mkdir -p /app/sample_data

CMD ["python", "main.py"]
