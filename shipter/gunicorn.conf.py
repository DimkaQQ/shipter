# Gunicorn configuration file for Shipter

import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Process naming
proc_name = "shipter"

# Server mechanics
daemon = False
pidfile = "/var/run/shipter/gunicorn.pid"
umask = 0
user = "www-data"
group = "www-data"
tmp_upload_dir = "/tmp"

# Logging
errorlog = "/var/log/shipter/gunicorn_error.log"
accesslog = "/var/log/shipter/gunicorn_access.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# SSL (if needed)
# keyfile = "/etc/ssl/private/shipter.key"
# certfile = "/etc/ssl/certs/shipter.crt"
