# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain a
# copy of the License at:
#
#            http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Functions used for testing"""

from unittest import TestCase

from .domutils import StringToDOM


class XmlTestCase(TestCase):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.addTypeEqualityFunc(bytes, 'assertBytesEqual')

    def assertBytesEqual(self, first, second, msg=None):
        if first == second:
            return
        if first.startswith(b"<") and second.startswith(b"<"):
            # assume XML documents
            try:
                fd = StringToDOM(first)
                sd = StringToDOM(second)
            except Exception: pass
            else:
                self.assertDOMEqual(fd, sd, msg)
                return
        self._baseAssertEqual(first, second, msg)

    def assertDOMEqual(self, d1, d2, msg=None):
        """assert DOMs *d1* and *d2* are equivalent."""

        def fail(txt):
            raise self.failureException(msg or txt)

        def node_name(n):
            return (f"{{{n.namespaceURI}}}" if n.namespaceURI else "") + f"{n.localName}"

        def eq_element(e1, e2, path):
            """assert elements *e1* and *e2* at *path* are equivalent."""
            t1 = node_name(e1)
            t2 = node_name(e2)
            if t1 != t2:
                fail(f"different elements {t1}/{t2} at {path}")
            path += "/" + t1
            a1 = {node_name(a): a.value for a in e1.attributes}
            a2 = {node_name(a): a.value for a in e2.attributes}
            if a1 != a2:
                fail(f"different attributes {a1}/{a2} at {path}")
            c1 = e1.childNodes
            c2 = e2.childNodes
            if len(c1) != len(c2):
                fail(f"different child numbers {len(c1)}/{len(c2)} at {path}")
            for i in range(len(c1)):
                n1 = c1[i]; n2 = c2[i]
                if n1.nodeType != n2.nodeType:
                    fail(f"different type for child {i} at {path}")
                disp[n1.nodeType](n1, n2, path + f"[{i}]")

        def eq_value(e1, e2, path):
            if e1.value != e2.value:
                fail(f"different value `{e1.value}`/`{e2.value}` at {path}")

        disp = {1: eq_element,
                3: eq_value,
                # maybe more to come
                }

        eq_element(d1.documentElement, d2.documentElement, "")
