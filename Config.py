from configparser import ConfigParser


class Config(ConfigParser):
    def __init__(self, path='config.ini'):
        super().__init__()
        self._path = path

    def read(self):
        super().read(self._path)

    def set(self, section, option, value):
        super().set(section, option, value)
        with open(self._path, 'w') as f:
            super().write(f)
        print('Configuration written to {}'.format(self._path))