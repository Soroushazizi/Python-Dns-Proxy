# Use the official Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the DNS proxy server script into the container
COPY dns.py /app/dns.py

# Install the required dependencies
RUN pip install dnslib

# Expose the port on which the DNS proxy will listen
EXPOSE 53/udp

# Run the DNS proxy server when the container starts
CMD ["python", "dns.py"]
