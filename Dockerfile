FROM python:3.11-slim

WORKDIR /app

# Configure pip to use Chinese mirror
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]