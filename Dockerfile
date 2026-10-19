
# ============================================================
# TELCO CUSTOMER 360 - PYTHON DOCKER IMAGE
# ============================================================

# 1. Use Python 3.14 as the base image
FROM python:3.14-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the Python dependencies
COPY requirements.txt .

# 4. Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy Python and SQL scripts
COPY src/ ./src/
COPY sql/ ./sql/

# 6. Show Python output immediately in Docker logs
ENV PYTHONUNBUFFERED=1

# 7. Define the default command
CMD ["python", "src/15_run_pipeline.py"]
