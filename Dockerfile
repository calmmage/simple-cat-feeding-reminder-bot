# Start with the official Python image from the Docker Hub
FROM python:3.12-slim-bookworm

# Update and install FFmpeg if using audio or video parsing features
# RUN apt-get update && \
#    apt-get install -y ffmpeg && \
#    rm -rf /var/lib/apt/lists/*
# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./src /app/src
COPY ./pyproject.toml /app/pyproject.toml
COPY ./run.py /app/run.py
COPY ./README.md /app/README.md
COPY ./LICENSE /app/LICENSE

# Install poetry and dependencies
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main

# Make port 80 available to the world outside this container
EXPOSE 80

# Run the command to start your bot
CMD ["python", "run.py"]