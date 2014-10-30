import os
import yaml

def get_settings():
    """Return the setting information located in the configuration file
    located in the settings/ directory.
    """

    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_file, 'r') as f:
        data = yaml.load(f)

    return data

SETTINGS = get_settings()