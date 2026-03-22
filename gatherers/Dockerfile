FROM python:3.12-slim

# Set the working directory to match the relative path structure expected by main.py
WORKDIR /app/gatherers

# Copy the requirements file and install dependencies
COPY gatherers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY gatherers/ .
COPY ops /app/ops

ENV PYTHONPATH=/app:/app/gatherers

# Run the main script
CMD ["python", "main.py"]
