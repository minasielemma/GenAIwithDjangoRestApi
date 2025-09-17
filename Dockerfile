# Use an official Python runtime as the base image
FROM python

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code
# Install dependencies
COPY requirements.txt /code/
RUN pip install -r requirements.txt

# Copy the project code into the container
COPY . /code/



# Expose the Django development server port
EXPOSE 8000
