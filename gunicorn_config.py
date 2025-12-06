"""
Gunicorn configuration for Quiz Global production deployment.

To use with systemd:
    gunicorn --config gunicorn_config.py quiz2.wsgi:application

To use with direct invocation:
    gunicorn quiz2.wsgi:application --config gunicorn_config.py
"""
import multiprocessing
import os

# Server socket
bind = "unix:/srv/quiz.global/gunicorn.sock"
backlog = 2048

# Worker processes
# Rule: (2 x CPU cores) + 1
workers = max(3, multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
worker_connections = 1000
threads = 1
timeout = 30
keepalive = 5

# Process naming
proc_name = 'quiz-gunicorn'

# Server mechanics
daemon = False
pidfile = None
tmp_upload_dir = None

# Logging - output to stdout/stderr for journalctl
accesslog = "-"
errorlog = "-"
loglevel = "info"
capture_output = True
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# SSL configuration (if using SSL directly with gunicorn, otherwise use nginx)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Request handling
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 30
preload_app = True

# Server hooks
def on_starting(server):
    """Hook called before the master process is started."""
    pass

def on_exit(server):
    """Hook called after the master process has exited."""
    pass

def pre_fork(server, worker):
    """Hook called just before a new worker is forked."""
    pass

def post_fork(server, worker):
    """Hook called just after a new worker is forked."""
    pass

def pre_exec(server):
    """Hook called before the new master process is executed."""
    pass

def post_worker_int(worker):
    """Hook called just after a worker has been interrupted."""
    pass

def worker_abort(worker):
    """Hook called when a worker is aborted."""
    pass

def pre_request(worker, req):
    """Hook called just prior to the request being serviced."""
    pass

def post_request(worker, req, environ, resp):
    """Hook called after the request has been fully processed."""
    pass

def child_exit(server, worker):
    """Hook called just after a worker has been exited."""
    pass

def server_alive(server):
    """Hook called after the server has been running for some time."""
    pass
