# The positive cases of patch are extensively tested in test_diff.py because a
# sensible way to validate a diff of two objects is to check that when you apply
# the patch to the first object you get the second.
# Here the testing mainly focuses on patch operations which would fail and some
# of the obscure positive cases. For example you should be able to apply a patch
# to an object that isn't one of the ones involved in the diff under certain
# conditions.
import unittest
from collections import namedtuple, OrderedDict
from copy import deepcopy
from differ import diff, patch
from differ.patch import (
    patch_sequence,
    patch_named_tuple,
    patch_mapping,
    patch_ordered_mapping,
    patch_set)


class PatchSequenceTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        a = [1, 2, 3]
        copy_of_a = deepcopy(a)
        b = [3, 2, 1]
        d = diff(a, b)
        self.assertEqual(patch(a, d), b)
        self.assertEqual(a, copy_of_a)


class PatchNamedTupleTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        ThreeDPoint = namedtuple('ThreeDPoint', ('x', 'y', 'z'))
        a = ThreeDPoint(1, 2, 3)
        copy_of_a = deepcopy(a)
        b = ThreeDPoint(2, 3, 4)
        d = diff(a, b)
        self.assertEqual(patch(a, d), b)
        self.assertEqual(a, copy_of_a)
        self.assertTrue(False)


class PatchMappingTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        pass


class PatchOrderedMappingTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        pass


class PatchSetTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        pass


class PatchTests(unittest.TestCase):
    def patch_has_no_side_effects(self):
        pass
