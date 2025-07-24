# Use an official Python 3.11 runtime as a parent image
FROM python:3.11-slim

# Set working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY analyse_spacy2.py ./
COPY logs.csv ./
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --timeout 600 -r requirements.txt

# Télécharger le modèle spaCy (déjà utilisé dans votre code)
RUN python -m spacy download en_core_web_md 

# Expose the port used 
EXPOSE 5003

# Start the Ollama server in the background and then run the Python script
CMD ["python3" ,"analyse_spacy2.py"] 
