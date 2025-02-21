import multiprocessing

# Gunicorn configuration
bind = "0.0.0.0:10000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "giip"

# SSL (if needed)
# keyfile = "/etc/ssl/private/key.pem"
# certfile = "/etc/ssl/certs/cert.pem"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL paths
# ssl_version = "TLS"
# cert_reqs = "CERT_NONE"

# Debug
reload = False
reload_engine = "auto"
spew = False
check_config = False 