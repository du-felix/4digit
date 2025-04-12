# 1. Choose a Base Image: Use an official Python image (using the slim variant for a smaller image)
FROM python:3.12-slim

# 2. Set environment variables to prevent Python from buffering output and writing .pyc files.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system dependencies that will be required for your project.
#    For mysqlclient, you need to install gcc and the MySQL client libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*


# 5. Copy the requirements.txt file into the container
COPY requirements.txt /app/

# 6. Upgrade pip and install the Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# 7. Copy the rest of your Django project code into the container
COPY . /app/
EXPOSE 8000

# Automatically run the development server on container start
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
