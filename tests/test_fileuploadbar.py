import sys
sys.path.append('../')

import unittest

from picasawebsync.fileuploadbar import FileUploadBar

class FileUploadBarTestCase(unittest.TestCase):
    # simple test if there is no exception triggered
    def test_set_name(self):
        bar = FileUploadBar('Testing', max=10)
        for i in range(10):
            bar.filename = str(i)
            bar.next()
        bar.finish()

if __name__ == '__main__':
    unittest.main()
