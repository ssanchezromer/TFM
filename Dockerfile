# Description: Dockerfile for the Flask app
# Author: Sergio Sánchez
# Date: 2024-12-01

# Use the official Python image
FROM python:3.11

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy scripts files to the container
COPY ./scripts /usr/src/app

# Copy requirements files to the container
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libgbm-dev \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxrandr2 \
    libxi6 \
    libxdamage1 \
    libxtst6 \
    libcups2 \
    libxshmfence1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Goggle Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Verify Google Chrome installation
RUN google-chrome --version || (echo "Google Chrome is not installed correctly" && exit 1)

# ChromeDriver
RUN apt-get update && apt-get install -y wget unzip \
    && GOOGLE_CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) \
    && CHROMEDRIVER_VERSION=$(curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${GOOGLE_CHROME_VERSION}) \
    && wget -q https://storage.googleapis.com/chrome-for-testing-public/${CHROMEDRIVER_VERSION}/linux64/chromedriver-linux64.zip \
    && unzip chromedriver-linux64.zip -d /usr/local/bin \
    && ln -s /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm chromedriver-linux64.zip

# Verify ChromeDriver installation
RUN chromedriver --version || (echo "ChromeDriver is not installed correctly" && exit 1)

# Install dependencies
RUN pip install --no-cache-dir -r /usr/src/app/crawler/requirements.txt

# Export the port where the app runs
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
