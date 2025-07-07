FROM python:3.11

WORKDIR /app

# Copy requirement file first for better caching
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the app
COPY . .

# Expose Flask port
EXPOSE 5000

# Default command
CMD ["python3", "app.py"]

