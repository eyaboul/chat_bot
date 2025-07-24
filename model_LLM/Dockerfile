# Use an official Python 3.11 runtime as a parent image
FROM python:3.11.12-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies for Ollama (if needed)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY model_llm_14b-back.py ./
COPY final_merged_data.csv ./

# Install Python dependencies
RUN pip install --no-cache-dir --timeout 600 flask pandas requests tabulate prometheus_client 

# Expose the port used by the Ollama server (default is 11434)
EXPOSE 8000

# Start the Ollama server in the background and then run the Python script
CMD ["python3" ,"model_llm_14b-back.py"]
