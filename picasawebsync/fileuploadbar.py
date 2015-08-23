
from progress.bar import Bar

class FileUploadBar(Bar):
    suffix = '%(index)d/%(max)d %(filename)s'

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, n):
        self._filename = n
