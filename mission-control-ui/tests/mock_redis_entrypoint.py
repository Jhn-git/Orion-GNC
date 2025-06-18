import subprocess
import sys
from unittest.mock import patch
import fakeredis
from gunicorn.app.base import BaseApplication

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        config = {key: value for key, value in self.options.items()
                  if key in self.cfg.settings and value is not None}
        for key, value in config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == '__main__':
    with patch('redis.Redis', fakeredis.FakeRedis):
        # The command is now passed as a single string
        command = sys.argv[1]
        # We need to split the command into a list of arguments
        command_args = command.split()
        
        # The application is the part after the --bind option
        app_module = command_args[command_args.index("--bind") + 2]
        
        options = {
            'bind': command_args[command_args.index("--bind") + 1],
            'workers': int(command_args[command_args.index("--workers") + 1]),
            'threads': int(command_args[command_args.index("--threads") + 1]),
        }
        
        # Dynamically import the app
        module, app = app_module.split(':')
        app_instance = getattr(__import__(module), app)
        
        StandaloneApplication(app_instance, options).run()