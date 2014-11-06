import os
import grp
import yaml

def get_settings():
    """Return the setting information located in the configuration file
    located in the settings/ directory.
    """

    config_file = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_file, 'r') as f:
        data = yaml.load(f)

    return data


def set_permissions(path):
    """
    Set the permissions of the file path to hstlc settings.
    """

    user = os.getuid()
    group = grp.getgrnam("hstlc").gr_gid
    os.chown(path, user, group)
    os.chmod(path, 0770)


SETTINGS = get_settings()