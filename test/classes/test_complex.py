"""Test Complex class."""

import unittest
from abc import ABC, abstractmethod

from toponetx.classes.complex import Complex


class TestComplex(unittest.TestCase):
    """Test the Complex abstract class."""

    class ConcreteComplex(Complex):
        """Concrete implementation of the Complex abstract class for tests."""

        @property
        def nodes(self):
            """Nodes of the complex."""
            raise NotImplementedError

        @property
        def dim(self):
            """Dimension of the complex."""
            raise NotImplementedError

        def shape(self):
            """Shape of the complex."""
            raise NotImplementedError

        def skeleton(self, rank):
            """Rank-skeleton of the complex."""
            raise NotImplementedError

        def __str__(self):
            raise NotImplementedError

        def __repr__(self):
            raise NotImplementedError

        def __len__(self):
            raise NotImplementedError

        def clone(self):
            """Clone the complex."""
            raise NotImplementedError

        def __iter__(self):
            raise NotImplementedError

        def __contains__(self, item):
            raise NotImplementedError

        def __getitem__(self, node):
            raise NotImplementedError

        def remove_nodes(self, node_set):
            """Remove nodes from the complex."""
            raise NotImplementedError

        def add_node(self, node):
            """Add a node to the complex."""
            raise NotImplementedError

        def incidence_matrix(self):
            """Compute the incidence matrix of the complex."""
            raise NotImplementedError

        def adjacency_matrix(self):
            """Compute the adjacency matrix of the complex."""
            raise NotImplementedError

        def coadjacency_matrix(self):
            """Compute the coadjacency matrix of the complex."""
            raise NotImplementedError

    def test_abstract_methods(self):
        """Test that abstract methods raise NotImplementedError."""
        complex_obj = self.ConcreteComplex()

        with self.assertRaises(NotImplementedError):
            complex_obj.nodes

        with self.assertRaises(NotImplementedError):
            complex_obj.dim

        with self.assertRaises(NotImplementedError):
            complex_obj.shape()

        with self.assertRaises(NotImplementedError):
            complex_obj.skeleton(0)

        with self.assertRaises(NotImplementedError):
            str(complex_obj)

        with self.assertRaises(NotImplementedError):
            repr(complex_obj)

        with self.assertRaises(NotImplementedError):
            len(complex_obj)

        with self.assertRaises(NotImplementedError):
            complex_obj.clone()

        with self.assertRaises(NotImplementedError):
            iter(complex_obj)

        with self.assertRaises(NotImplementedError):
            1 in complex_obj

        with self.assertRaises(NotImplementedError):
            complex_obj["node"]

        with self.assertRaises(NotImplementedError):
            complex_obj.remove_nodes([1, 2, 3])

        with self.assertRaises(NotImplementedError):
            complex_obj.add_node("node")

        with self.assertRaises(NotImplementedError):
            complex_obj.incidence_matrix()

        with self.assertRaises(NotImplementedError):
            complex_obj.adjacency_matrix()

        with self.assertRaises(NotImplementedError):
            complex_obj.coadjacency_matrix()

    def test_clear_cache(self):
        """Test the _clear_cache method."""
        complex_obj = self.ConcreteComplex()

        with self.assertRaises(AttributeError):
            complex_obj.cache  # Cache attribute should not exist initially

        complex_obj._clear_cache()

        self.assertEqual(
            complex_obj.cache, {}
        )  # Cache attribute should be an empty dictionary


if __name__ == "__main__":
    unittest.main()
