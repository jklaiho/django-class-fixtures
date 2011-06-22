import sys
from contextlib import contextmanager
from StringIO import StringIO

@contextmanager
def string_stdout():
    output = StringIO()
    sys.stdout = output
    yield output
    sys.stdout = sys.__stdout__
