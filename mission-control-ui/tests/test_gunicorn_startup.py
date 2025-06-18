import os
import psutil
def test_gunicorn_worker_count():
    """
    Verify that the number of Gunicorn worker processes matches the
    GUNICORN_WORKERS environment variable.
    """
    expected_workers = int(os.environ.get("GUNICORN_WORKERS", 1))

    # Find processes running our mock_redis_entrypoint.py with gunicorn
    gunicorn_processes = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
        if (p.info['name'] == 'python' and
            'mock_redis_entrypoint.py' in ' '.join(p.info['cmdline']) and
            'gunicorn' in ' '.join(p.info['cmdline'])):
            gunicorn_processes.append(p)
    
    # Sort by PID to get consistent ordering (master should have lowest PID)
    gunicorn_processes.sort(key=lambda x: x.pid)
    
    assert len(gunicorn_processes) > 0, "No Gunicorn processes found"
    
    # The master is the first process, workers are the rest
    master_process = gunicorn_processes[0]
    worker_processes = gunicorn_processes[1:]
    


    assert len(worker_processes) == expected_workers, \
        f"Expected {expected_workers} workers, but found {len(worker_processes)}"