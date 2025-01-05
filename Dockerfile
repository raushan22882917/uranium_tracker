# Base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies and Chromium
RUN apt-get update && apt-get install -y \
    libpq-dev \
    build-essential \
    curl \
    wget \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright via pip
RUN pip install playwright

# Install Playwright browsers
RUN playwright install

# Copy the application code
COPY . /app/

# Add Chromium to PATH
ENV PATH="/usr/lib/chromium:$PATH"
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER_PATH="/usr/bin/chromedriver"

# Collect static files
# RUN python manage.py collectstatic --noinput

# Expose the port that the app will run on
EXPOSE 8000

# Command to run the application with a timeout
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:8000", "--timeout=130", "uranium_project.wsgi:application"]
