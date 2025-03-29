# Use official Python image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY ./requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV FLASK_APP=app/main.py
ENV FLASK_ENV=production
ENV PORT=8000

# Expose port
EXPOSE $PORT

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app.main:app"]