"""Utilities for writing code that runs on Python 2 and 3

Change from 'six' to 'sal' because six quit working in at Python 3.12.4 or sooner
and Python 2.x has passed its end of life. The concept here is to support only
the know trouble items as python evolves rather a "compete" unit for all changes
from 2.x to 3.x. Instead of uisng PEP compliant code to squeeze the transistions
into the python space, just use a Software Abstraction Layer (sal) to handle just
the evolving code that pyxb needs.
"""

# Copyright (c) 2010-2015 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import

import functools
import itertools
import operator
import sys
import types
# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3
PY34 = sys.version_info[0:2] >= (3, 4)

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    none_type = type(None)
    boolean_type = bool
    float_type = float
    int_type = int
    long_type = int
    list_type = list
    tuple_type = tuple
    dictionary_type = dict

    MAXSIZE = sys.maxsize

    import io
    import pickle as cPickle
    from builtins import exec as exec_
    from builtins import range as xrange
    from sys import intern
    from urllib import parse as urlparse
    from urllib import request as urllib_request
    from urllib.request import urlopen

    def iterkeys(d, **kw):
        return iter(d.keys(**kw))
    def itervalues(d, **kw):
        return iter(d.values(**kw))
    def iteritems(d, **kw):
        return iter(d.items(**kw))
    def iterlists(d, **kw):
        return iter(d.lists(**kw))
    viewkeys = operator.methodcaller("keys")
    viewvalues = operator.methodcaller("values")
    viewitems = operator.methodcaller("items")
    def b(s): return s.encode("latin-1")
    def u(s): return s
    unichr = chr
    import struct
    int2byte = struct.Struct(">B").pack
    del struct
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
    file = io.IOBase
    _assertCountEqual = "assertCountEqual"
    if sys.version_info[1] <= 1:
        _assertRaisesRegex = "assertRaisesRegexp"
        _assertRegex = "assertRegexpMatches"
    else:
        _assertRaisesRegex = "assertRaisesRegex"
        _assertRegex = "assertRegex"
    Iterator = object
else:
    raise TypeError("Python 2 no longer supported")

def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if PY2:
        if '__str__' not in klass.__dict__:
            raise ValueError("@python_2_unicode_compatible cannot be applied "
                             "to %s because it doesn't define __str__()." %
                             klass.__name__)
        klass.__unicode__ = klass.__str__
        import pyxb
        klass.__str__ = lambda self: self.__unicode__().encode(pyxb._OutputEncoding)
    return klass
