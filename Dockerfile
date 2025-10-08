# Dockerfile for USB-Beamer-server

# Use Ubuntu 22.04 as base image to match the host kernel family.
FROM ubuntu:22.04

# Set environment variables to non-interactive to avoid prompts during installation.
ENV DEBIAN_FRONTEND=noninteractive
ENV TUNNEL_PORT=8007

# Update package lists and install necessary packages.
# - linux-tools-generic & linux-cloud-tools-generic: Provides usbip and other tools
#   that match the host kernel when running inside a container.
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    avahi-daemon \
    avahi-utils \
    dbus \
    linux-tools-generic \
    linux-cloud-tools-generic \
    iproute2 \
    python3-flask \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user 'tunnel', and then explicitly lock its password
# to allow key-based login while preventing password-based login.
# RUN useradd --create-home --shell /bin/bash tunnel && \
#     echo "nopasswordlogin" | passwd --stdin tunnel && \
#     mkdir -p /home/tunnel/.ssh && \
#     touch /home/tunnel/.ssh/authorized_keys

# Create a directory for the SSH daemon and generate host keys.
RUN mkdir /var/run/sshd && ssh-keygen -A

# Copy our custom sshd_config file into the container.
COPY sshd_config /etc/ssh/sshd_config

# Expose ports for SSH and the web application.
EXPOSE ${TUNNEL_PORT}
EXPOSE 5000

# Set the working directory for the application.
WORKDIR /app

# Copy the application code into the container.
# NOTE: The web app itself (app.py, templates, etc.) is not yet created.
COPY . /app

# Make the entrypoint script executable and set it as the entrypoint.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"] 