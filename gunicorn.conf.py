import multiprocessing

# Gunicorn configuration for production
bind = "0.0.0.0:10000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "GIIR Conference"

# SSL (if needed)
# keyfile = "path/to/keyfile"
# certfile = "path/to/certfile" 