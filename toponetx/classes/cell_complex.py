"""
Class for creation and manipulation of 2d Cell Complex.
The class also supports attaching arbitrary attributes and data to cells.
"""


import warnings
from collections import Hashable, Iterable
from itertools import zip_longest

import networkx as nx
import numpy as np
from hypernetx import Hypergraph
from hypernetx.classes.entity import Entity
from networkx import Graph
from networkx.algorithms import bipartite
from scipy.sparse import csr_matrix

from toponetx.classes.cell import Cell, CellView
from toponetx.classes.combinatorial_complex import CombinatorialComplex
from toponetx.classes.ranked_entity import (
    CellObject,
    Node,
    RankedEntity,
    RankedEntitySet,
)
from toponetx.exception import TopoNetXError

__all__ = ["CellComplex"]


class CellComplex:

    """

    In TNX cell complexes are implementes to be dynamic in the sense that
    they can change by adding or subtracting objects (nodes, edges, cells)
    from them.
        #Example 0
            >>> # Cell Complex can be empty
            >>> CC = CellComplex( )
        #Example 1
            >>> CX = CellComplex()
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([2,3,4,5],rank=2)
            >>> CX.add_cell([5,6,7,8],rank=2)
        #Example 2
            >>> c1= Cell( (1,2,3))
            >>> c2= Cell( (1,2,3,4) )
            >>> CX = CellComplex( [c1,c2] )
        #Example 3
            >>> G= Graph()
            >>> G.add_edge(1,0)
            >>> G.add_edge(2,0)
            >>> G.add_edge(1,2)
            >>> CX = CellComplex(G)
            >>> CX.add_cells_from([[1,2,4],[1,2,7] ],rank=2)
            >>> CX.cells
        #Example 4
            >>> # non-regular cell complex
            >>> CX = CellComplex(regular=False)
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([2,3,4,5,2,3,4,5],rank=2) #non-regular 2-cell
            >>> c1=Cell((1,2,3,4,5,1,2,3,4,5),regular=False)
            >>> CX.add_cell(c1)
            >>> CX.add_cell([5,6,7,8],rank=2)
            >>> CX.is_regular

    """

    def __init__(self, cells=None, name=None, regular=True, **attr):
        if not name:
            self.name = ""
        else:
            self.name = name

        self._regular = regular
        self._G = Graph()

        self._cells = CellView()
        if cells is not None:
            if isinstance(cells, Graph):
                self._G = cells
            elif isinstance(cells, Iterable) and not isinstance(cells, Graph):
                for c in cells:
                    if isinstance(c, Hashable) and not isinstance(
                        c, Iterable
                    ):  # c is a node
                        self.add_node(c)
                    elif isinstance(c, Iterable):
                        if len(c) == 2:
                            self.add_cell(c, rank=1)
                        elif len(c) == 1:
                            self.add_node(tuple(c)[0])
                        else:
                            self.add_cell(c, rank=2)

            else:
                raise ValueError(
                    f"cells must be iterable, networkx graph or None, got {type(cells)}"
                )
        self.complex = dict()  # dictionary for cell complex attributes
        self.complex.update(attr)

    @property
    def cells(self):
        """
        Object associated with self._cells.

        Returns
        -------

        """
        return self._cells

    @property
    def edges(self):
        """
        Object associated with self._edges.

        Returns
        -------

        """
        return self._G.edges

    @property
    def nodes(self):
        """
        Object associated with self._nodes.

        Returns
        -------
        RankedEntitySet

        """
        return self._G.nodes

    @property
    def maxdim(self):

        if len(self.nodes) == 0:
            return 0
        elif len(self.edges) == 0:
            return 0
        elif len(self.cells) == 0:
            return 1
        else:
            return 2

    @property
    def dim(self):
        return self.maxdim

    @property
    def shape(self):
        """
        (number of cells[i], for i in range(0,dim(CC))  )

        Returns
        -------
        tuple

        """
        return len(self.nodes), len(self.edges), len(self.cells)

    def skeleton(self, k):
        if k == 0:
            return self.nodes
        elif k == 1:
            return self.edges
        elif k == 2:
            return self.cells
        else:
            raise TopoNetXError("Only dimensions 0,1, and 2 are supported.")

    @property
    def is_regular(self):

        """
        Checking the regularity condition of the cell complex

        Returns
        -------
        bool

        Example
        -------
            >>> CX = CellComplex(regular=False)
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([2,3,4,5,2,3,4,5],rank=2) #non-regular 2-cell
            >>> c1=Cell((1,2,3,4,5,1,2,3,4,5),regular=False)
            >>> CX.add_cell(c1)
            >>> CX.add_cell([5,6,7,8],rank=2)
            >>> CX.is_regular
        """

        if self._regular:  # condition is enforced for all cells
            return True
        for c in self.cells:
            if not c.is_regular:
                return False
        return True

    def __str__(self):
        """
        String representation of CX

        Returns
        -------
        str

        """
        return f"Cell Complex with {len(self.nodes)} nodes, {len(self.edges)} edges  and {len(self.cells)} 2-cells "

    def __repr__(self):
        """
        String representation of cell complex

        Returns
        -------
        str

        """
        return f"CellComplex(name={self.name})"

    def __len__(self):
        """
        Number of nodes

        Returns
        -------
        int

        """

        return len(self.nodes)

    def __iter__(self):
        """
        Iterate over the nodes of the cell complex

        Returns
        -------
        dict_keyiterator

        """
        return iter(self.nodes)

    def __contains__(self, item):
        """
        Returns boolean indicating if item is in self.nodes

        Parameters
        ----------
        item : hashable or RankedEntity

        """

        return item in self.nodes

    def __getitem__(self, node):
        """
        Returns the neighbors of node

        Parameters
        ----------
        node : Entity or hashable
            If hashable, then must be uid of node in cell complex

        Returns
        -------
        neighbors(node) : iterator

        """
        return self.neighbors(node)

    def degree(self, node, rank=1):
        """
        The number of cells of certain rank that contain node.

        Parameters
        ----------
        node : hashable
            identifier for the node.
        rank : positive integer, optional, default: 1
            smallest size of cell to consider in degree

        Returns
        -------
         : int

        """
        return self._G.degree[node]

    def size(self, cell, nodeset=None):
        """
        The number of nodes in nodeset that belong to cell.
        If nodeset is None then returns the size of cell

        Parameters
        ----------
        cell : hashable
            The uid of an cell in the cell complex

        Returns
        -------
        size : int

        """
        if nodeset:
            return len(set(nodeset).intersection(set(self.cells[cell])))
        else:
            if cell in self.cells:

                return len(self.cells[cell])
            else:
                raise KeyError(f" the key {cell} is not a key for an existing cell ")

    def number_of_nodes(self, nodeset=None):
        """
        The number of nodes in nodeset belonging to cell complex.

        Parameters
        ----------
        nodeset : an interable of nodes, optional, default: None
            If None, then return the number of nodes in cell complex.

        Returns
        -------
        number_of_nodes : int

        """
        if nodeset:
            return len([n for n in self.nodes if n in nodeset])
        else:
            return len(self.nodes)

    def number_of_edges(self, edgeset=None):
        """
        The number of cells in cellset belonging to cell complex.

        Parameters
        ----------
        cellset : an interable of RankedEntities, optional, default: None
            If None, then return the number of cells in cell complex.

        Returns
        -------
        number_of_cells : int
        """
        if edgeset:
            return len([e for e in self.cells if e in edgeset])
        else:
            return len(self.edges)

    def number_of_cells(self, cellset=None):
        """
        The number of cells in cellset belonging to cell complex.

        Parameters
        ----------
        cellset : an interable of RankedEntities, optional, default: None
            If None, then return the number of cells in cell complex.

        Returns
        -------
        number_of_cells : int
        """
        if cellset:
            return len([e for e in self.cells if e in cellset])
        else:
            return len(self.cells)

    def order(self):
        """
        The number of nodes in CC.

        Returns
        -------
        order : int
        """
        return len(self.nodes)

    def neighbors(self, node):
        """
        The nodes in cell complex which share s cell(s) with node.

        Parameters
        ----------
        node : hashable or Entity
            uid for a node in cell complex or the node Entity

        s : int, list, optional, default : 1
            Minimum rank of cells shared by neighbors with node.

        Returns
        -------
         : list
            List of neighbors

        Example
        -------


        """
        if not node in self.nodes:
            print(f"Node is not in cell complex {self.name}.")
            return

        return self._G[node]

    def cell_neighbors(self, cell, s=1):
        """
        The cells in cell Complex which share s nodes(s) with cells.

        Parameters
        ----------
        cell : hashable or RankedEntity
            uid for a cell in cell complex or the cell RankedEntity

        s : int, list, optional, default : 1
            Minimum number of nodes shared by neighbors cell node.

        Returns
        -------
         : list
            List of cell neighbors

        """
        """
        if not cell in self.cells:
            print(f"cell is not in CC {self.name}.")


        node = self.cells[cell].uid
        return self.dual().neighbors(node, s=s)
        """
        raise NotImplementedError

    def remove_node(self, node):
        """
        Removes node from cells and deletes reference in cell complex nodes

        Parameters
        ----------
        node : hashable or RankedEntity
            a node in cell complex

        Returns
        -------
        Cell Complex : CellComplex
        Example:


        """
        raise NotImplementedError

    def remove_nodes(self, node_set):
        """
        Removes nodes from cells and deletes references in cell complex nodes

        Parameters
        ----------
        node_set : an iterable of hashables or Entities
            Nodes in CC

        Returns
        -------
        cell complex : CombinatorialComplex

        """
        raise NotImplementedError

    def add_node(self, node, **attr):

        self._G.add_node(node, **attr)

    def _add_nodes_from(self, nodes):
        """
        Private helper method instantiates new nodes when cells added to cell complex.

        Parameters
        ----------
        nodes : iterable of hashables or RankedEntities

        """
        for node in nodes:
            self.add_node(node)

    def add_edge(self, u_of_edge, v_of_edge, **attr):
        self._G.add_edge(u_of_edge, v_of_edge, **attr)

    def add_edges_from(self, ebunch_to_add, **attr):
        self._G.add_edge_from(ebunch_to_add, **attr)

    def add_cell(self, cell, rank=None, check_skeleton=False, **attr):
        """

        Adds a single cells to cell complex.

        Parameters
        ----------
        cell : hashable or RankedEntity
            If hashable the cell returned will be empty.
        uid : unique identifier that identifies the cell
        rank : rank of a cell



        Returns
        -------
        Cell Complex : CellComplex

        Example
        -------
        >>> CX = CellComplex()
        >>> c1 = Cell((2,3,4), color = 'black' )
        >>> CX.add_cell(c1,weight=3)
        >>> CX.add_cell([1,2,3,4],rank=2,color='red')
        >>> CX.add_cell([2,3,4,5],rank=2,color='blue')
        >>> CX.add_cell([5,6,7,8],rank=2,color='green')
        >>> CX.cells[(1,2,3,4)]['color']
        'red'


        Notes
        -----
        - Rank must be 0,1,2


        """
        if isinstance(cell, Cell):  # rank check will be ignored, cells by default
            # are assumed to be of rank 2
            if self.is_insertable_cycle(
                cell, check_skeleton=check_skeleton, warnings_dis=True
            ):
                for e in cell.boundary:
                    self._G.add_edge(e[0], e[1])
                if self._regular:
                    if cell.is_regular:
                        self._cells.insert_cell(cell, **attr)
                    else:
                        raise TopoNetXError(
                            "input cell violates the regularity condition."
                        )
                else:
                    self._cells.insert_cell(cell, **attr)
            else:
                print(
                    "Invalid cycle condition, the input cell cannot be inserted to the cell complex"
                )
        else:
            if rank == 0:
                raise TopoNetXError(
                    "Use add_node to insert nodes or zero ranked cells."
                )
            elif rank == 1:
                if len(cell) != 2:
                    raise ValueError("rank 2 cell must have exactly two nodes")
                elif len(set(cell)) == 1:
                    raise ValueError(" invalid insertion : self-loops are not allowed.")
                else:
                    self.add_edge(cell[0], cell[1], **attr)

            elif rank == 2:
                if isinstance(cell, Iterable):
                    if not isinstance(cell, list):
                        cell = list(cell)

                    if self.is_insertable_cycle(
                        cell, check_skeleton=check_skeleton, warnings_dis=True
                    ):

                        edges_cell = set(zip_longest(cell, cell[1:] + [cell[0]]))
                        for e in edges_cell:
                            self._G.add_edges_from(edges_cell)
                        self._cells.insert_cell(
                            Cell(cell, regular=self._regular), **attr
                        )
                    else:
                        print(
                            "Invalid cycle condition, check if edges of the input cells are in the 1-skeleton."
                        )
                        print(" To ignore this check, set check_skeleton = False.")
                else:
                    raise ValueError("invalid input")
            else:
                raise ValueError(
                    f"Add cell only supports adding cells of dimensions 0,1 or 2-- got {rank}",
                )

        return self

    def add_cells_from(self, cell_set, rank=None):
        """
        Add cells to cell complex .

        Parameters
        ----------
        cell_set : iterable of hashables or Cell
            For hashables the cells returned will be empty.

        rank : integer (optional), default is None
               when each element in cell_set is an iterable then
               rank must be a number that indicates the rank
               of the added cells.

        Returns
        -------
        Cell Complex : CellComplex

        """

        for cell in cell_set:
            self.add_cell(cell=cell, rank=rank)
        return self

    def remove_cell(self, cell):
        """
        Removes a single cell from Cell Complex.

        Parameters
        ----------
        cell : cell's node_set or Cell

        Returns
        -------
        Cell Complex : CellComplex

        Notes
        -----

        Deletes reference to cell, keep it boundary edges in the cell complex

        """
        if isinstance(cell, Cell):
            self._cells.delete_cell(cell.elements)
        elif isinstance(cell, tuple):
            self._cells.delete_cell(cell)

        return self

    def remove_cells(self, cell_set):
        """
        Removes cells from CC.

        Parameters
        ----------
        cell_set : iterable of hashables or RankedEntities

        Returns
        -------
        cell complex : CombinatorialComplex

        """
        for cell in cell_set:
            self.remove_cell(cell)
        return self

    def set_node_attributes(self, values, name=None):

        if name is not None:
            # if `values` is a dict using `.items()` => {cell: value}

            for cell, value in values.items():
                try:
                    self.nodes[cell][name] = value
                except KeyError:
                    pass

        else:

            for cell, d in values.items():
                try:
                    self.nodes[cell].update(d)
                except KeyError:
                    pass
            return

    def set_cell_attributes(self, values, name=None):
        """


            Parameters
            ----------
            values : TYPE
                DESCRIPTION.
            name : TYPE, optional
                DESCRIPTION. The default is None.

            Returns
            -------
            None.

            Example
            ------

            After computing some property of the cell of a cell complex, you may want
            to assign a cell attribute to store the value of that property for
            each cell:

            >>> CC = CellComplex()
            >>> CC.add_cell([1,2,3,4], rank=2)
            >>> CC.add_cell([1,2,4], rank=2,)
            >>> CC.add_cell([3,4,8], rank=2)
            >>> d={(1,2,3,4):'red',(1,2,4):'blue'}
            >>> CC.set_cell_attributes(d,name='color')
            >>> CC.cells[(1,2,3,4)]['color']
            'red'

        If you provide a dictionary of dictionaries as the second argument,
        the entire dictionary will be used to update edge attributes::

            Examples
            --------
            >>> G = nx.path_graph(3)
            >>> CC = CellComplex(G)
            >>> CC.add_cell([1,2,3,4], rank=2)
            >>> CC.add_cell([1,2,3,4], rank=2)
            >>> CC.add_cell([1,2,4], rank=2,)
            >>> CC.add_cell([3,4,8], rank=2)
            >>> d={ (1,2,3,4): { 'color':'red','attr2':1 },(1,2,4): {'color':'blue','attr2':3 } }
            >>> CC.set_cell_attributes(d)
            >>> CC.cells[(1,2,3,4)][0]['color']
            'red'

        Note : If the dict contains cells that are not in `self.cells`, they are
        silently ignored.

        """

        if name is not None:
            # if `values` is a dict using `.items()` => {cell: (key,value) } or {cell:value}

            for cell, value in values.items():
                try:

                    if len(cell) == 2:
                        if isinstance(cell[0], Iterable) and isinstance(
                            cell[1], int
                        ):  # input cell has cell key
                            self.cells[cell][cell[0]][name] = value
                        else:
                            self.cells[cell][name] = value

                    elif isinstance(
                        self.cells[cell], list
                    ):  # all cells with same key get same attrs
                        for i in range(len(self.cells[cell])):
                            self.cells[cell][i][name] = value
                    else:
                        self.cells[cell][name] = value

                except KeyError:
                    pass

        else:

            for cell, d in values.items():
                try:

                    if len(cell) == 2:
                        if isinstance(cell[0], Iterable) and isinstance(
                            cell[1], int
                        ):  # input cell has cell key
                            self.cells[cell[0]][cell[1]].update(d)
                        else:  # length of cell is 2
                            self.cells[cell].update(d)
                    elif isinstance(
                        self.cells[cell], list
                    ):  # all cells with same key get same attrs
                        for i in range(len(self.cells[cell])):

                            self.cells[cell][i].update(d)
                    else:
                        self.cells[cell].update(d)
                except KeyError:
                    pass
            return

    def get_node_attributes(self, name):
        """Get node attributes from cell complex

        Parameters
        ----------

        name : string
           Attribute name

        Returns
        -------
        Dictionary of attributes keyed by node.

        Examples
        --------
        >>> G = nx.path_graph(3)
        >>> CC = CellComplex(G)
        >>> d={0: {'color':'red','attr2':1 },1: {'color':'blue','attr2':3 } }
        >>> CC.set_node_attributes(d)
        >>> CC.get_node_attributes('color')
        {0: 'red', 1: 'blue'}

        >>> G = nx.Graph()
        >>> G.add_nodes_from([1, 2, 3], color="blue")
        >>> CC = CellComplex(G)
        >>> nodes_color = CC.get_node_attributes('color')
        >>> nodes_color[1]
        'blue'

        """
        return {n: self.nodes[n][name] for n in self.nodes if name in self.nodes[n]}

    def get_cell_attributes(self, name, k=None):
        """Get node attributes from graph

        Parameters
        ----------

        name : string
           Attribute name

        k : integer rank of the k-cell
        Returns
        -------
        Dictionary of attributes keyed by cell or k-cells if k is not None

        Examples
        --------
        >>> import networkx as nx
        >>> G = nx.path_graph(3)

        >>> d={ ((1,2,3,4),0): { 'color':'red','attr2':1 },(1,2,4): {'color':'blue','attr2':3 } }
        >>> CC = CellComplex(G)
        >>> CC.add_cell([1,2,3,4], rank=2)
        >>> CC.add_cell([1,2,3,4], rank=2)
        >>> CC.add_cell([1,2,4], rank=2,)
        >>> CC.add_cell([3,4,8], rank=2)
        >>> CC.set_cell_attributes(d)
        >>> cell_color=CC.get_cell_attributes('color',2)
        >>> cell_color
        '{((1, 2, 3, 4), 0): 'red', (1, 2, 4): 'blue'}
        """

        if k is not None:
            if k == 0:
                return self.get_cell_attributes(name)
            elif k == 1:
                return nx.get_edge_attributes(self._G, name)
            elif k == 2:
                d = {}
                for n in self.cells:
                    if isinstance(self.cells[n.elements], list):  # multiple cells
                        for i in range(len(self.cells[n.elements])):
                            if name in self.cells[n.elements][i]:
                                d[(n.elements, i)] = self.cells[n.elements][i][name]
                    else:
                        if name in self.cells[n.elements]:
                            d[n.elements] = self.cells[n.elements][name]

                return d
            else:
                raise TopoNetXError(f"k must be 0,1 or 2, got {k}")

    def remove_equivalent_cells(self):
        """
        Remove cells from the cell complex which are homotopic.
        In other words, this is equivalent to identifying cells
        containing the same nodes

         Note
         ------
         Remove all 2d- cells that are homotpic (equivalent to each other)

         Returns
         -------
         None.

         Example
         -------
            >>> import networkx as nx
            >>> G = nx.path_graph(3)
            >>> CC = CellComplex(G)
            >>> CC.add_cell([1,2,3,4], rank=2)
            >>> CC.add_cell([1,2,3,4], rank=2)
            >>> CC.add_cell([2,3,4,1], rank=2)
            >>> CC.add_cell([1,2,4], rank=2,)
            >>> CC.add_cell([3,4,8], rank=2)
            >>> CC.remove_equivalent_cells()

        """
        self.cells.remove_equivalent_cells()

    def is_insertable_cycle(self, cell, check_skeleton=True, warnings_dis=False):

        if isinstance(cell, Cell):
            cell = cell.elements
        if len(cell) <= 1:
            if warnings_dis:
                warnings.warn(f"a cell must contain at least 2 edges, got {len(cell)}")
            return False
        if self._regular:
            if len(set(cell)) != len(cell):
                if warnings_dis:
                    warnings.warn(
                        f"repeating nodes invalidates the 2-cell regular condition"
                    )
                return False
        if check_skeleton:
            enum = zip_longest(cell, cell[1:] + [cell[0]])
            for i in enum:
                if i not in self.edges:
                    if warnings_dis:
                        warnings.warn(
                            f"edge {i} is not a part of the 1 skeleton of the cell complex",
                            stacklevel=2,
                        )
                    return False
        return True

    def incidence_matrix(self, d, signed=True, weight=None, index=False):
        """
        An incidence matrix for the CC indexed by nodes x cells.

        Parameters
        ----------
        weight : bool, default=False
            If False all nonzero entries are 1.
            If True and self.static all nonzero entries are filled by
            self.cells.cell_weight dictionary values.

        index : boolean, optional, default False
            If True return will include a dictionary of node uid : row number
            and cell uid : column number

        Returns
        -------
        incidence_matrix : scipy.sparse.csr.csr_matrix

        row dictionary : dict
            Dictionary identifying rows with nodes

        column dictionary : dict
            Dictionary identifying columns with cells

        Example1
        -------
            >>> CX = CellComplex()
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([3,4,5],rank=2)
            >>> B1 = CX.incidence_matrix(1)
            >>> B2 = CX.incidence_matrix(2)
            >>> B1.dot(B2).todense()

        Example2
        --------
            ## note that in this example, the first three cells are
            ## equivalent and hence they have similar incidence to lower edges
            ## they are incident to
            >>> import networkx as nx
            >>> G = nx.path_graph(3)
            >>> CX = CellComplex(G)
            >>> CX.add_cell([1,2,3,4], rank=2)
            >>> CX.add_cell([4,3,2,1], rank=2)
            >>> CX.add_cell([2,3,4,1], rank=2)
            >>> CX.add_cell([1,2,4], rank=2,)
            >>> CX.add_cell([3,4,8], rank=2)
            >>> B1 = CX.incidence_matrix(1)
            >>> B2 = CX.incidence_matrix(2)
            >>> B1.dot(B2).todense()

        Example3
        -------
            # non-regular complex example
            >>> CX = CellComplex(regular=False)
            >>> CX.add_cell([1,2,3,2],rank=2)
            >>> CX.add_cell([3,4,5,3,4,5],rank=2)
            >>> B1 = CX.incidence_matrix(1)
            >>> B2 = CX.incidence_matrix(2)
            >>> B1.dot(B2).todense()
        """
        weight = None  # not supported at this version
        import scipy as sp
        import scipy.sparse

        if d == 0:

            A = sp.sparse.lil_matrix((1, len(self._G.nodes)))
            for i in range(0, len(self._G.nodes)):
                A[0, i] = 1
            if index:
                if signed:
                    return self._G.nodes, [], A.asformat("csc")
                else:
                    return self._G.nodes, [], abs(A.asformat("csc"))
            else:
                if signed:

                    return A.asformat("csc")
                else:
                    return abs(A.asformat("csc"))

        elif d == 1:
            nodelist = sorted(
                self._G.nodes
            )  # always output boundary matrix in dictionary order
            edgelist = sorted(self._G.edges)
            A = sp.sparse.lil_matrix((len(nodelist), len(edgelist)))
            node_index = {node: i for i, node in enumerate(nodelist)}
            for ei, e in enumerate(edgelist):
                (u, v) = sorted(e[:2])
                ui = node_index[u]
                vi = node_index[v]
                A[ui, ei] = -1
                A[vi, ei] = 1
            if index:
                if signed:
                    return nodelist, edgelist, A.asformat("csc")
                else:
                    return nodelist, edgelist, abs(A.asformat("csc"))
            else:
                if signed:
                    return A.asformat("csc")
                else:
                    return abs(A.asformat("csc"))
        elif d == 2:
            edgelist = sorted(self._G.edges)

            A = sp.sparse.lil_matrix((len(edgelist), len(self.cells)))

            edge_index = {
                tuple(sorted(edge)): i for i, edge in enumerate(edgelist)
            }  # orient edges
            for celli, cell in enumerate(self.cells):
                edge_visiting_dic = {}  # this dictionary is cell dependent
                # mainly used to handle the cell complex non-regular case
                for edge in cell.boundary:
                    ei = edge_index[tuple(sorted(edge))]
                    if ei not in edge_visiting_dic:
                        if edge in edge_index:
                            edge_visiting_dic[ei] = 1
                        else:
                            edge_visiting_dic[ei] = -1
                    else:
                        if edge in edge_index:
                            edge_visiting_dic[ei] = edge_visiting_dic[ei] + 1
                        else:
                            edge_visiting_dic[ei] = edge_visiting_dic[ei] - 1

                    A[ei, celli] = edge_visiting_dic[
                        ei
                    ]  # this will update everytime we visit this edge for non-regular CC
                    # the regular case can be handled more efficiently :
                    # if edge in edge_index:
                    #    A[ei, celli] = 1
                    # else:
                    #    A[ei, celli] = -1
            if index:
                cell_index = {cell: i for i, cell in enumerate(self.cells)}
                if signed:
                    return edge_index, cell_index, A.asformat("csc")
                else:
                    return edge_index, cell_index, abs(A.asformat("csc"))
            else:
                if signed:
                    return A.asformat("csc")
                else:
                    return abs(A.asformat("csc"))
        else:
            raise ValueError(f"Only dimension 0,1 and 2 are supported, got {d}")

    @staticmethod
    def _incidence_to_adjacency(M, weight=False):
        """
        Helper method to obtain adjacency matrix from
        boolean incidence matrix for s-metrics.
        Self loops are not supported.
        The adjacency matrix will define an s-linegraph.

        Parameters
        ----------
        M : scipy.sparse.csr.csr_matrix
            incidence matrix of 0's and 1's

        s : int, optional, default: 1

        # weight : bool, dict optional, default=True
        #     If False all nonzero entries are 1.
        #     Otherwise, weight will be as in product.

        Returns
        -------
        a matrix : scipy.sparse.csr.csr_matrix

        >>> CX = CellComplex()
        >>> CX.add_cell([1,2,3,5,6],rank=2)
        >>> CX.add_cell([1,2,4,5,3,0],rank=2)
        >>> CX.add_cell([1,2,4,9,3,0],rank=2)
        >>> B1 = CX.incidence_matrix(1)
        >>> B2 = CX.incidence_matrix(2)

        """

        M = csr_matrix(M)
        weight = False  ## currently weighting is not supported

        if weight == False:
            A = M.dot(M.transpose())
            A.setdiag(0)
        return A

    def hodge_laplacian_matrix(self, d, signed=True, weight=None, index=False):
        if d == 0:
            B_next = self.incidence_matrix(d + 1)
            L = B_next @ B_next.transpose()
        elif d < 2:
            B_next = self.incidence_matrix(d + 1)
            B = self.incidence_matrix(d)
            L = B_next @ B_next.transpose() + B.transpose() @ B
        elif d == self.maxdim:
            B = self.incidence_matrix(d)
            L = B.transpose() @ B
        else:
            raise ValueError(
                f"d should be larger than 0 and <= {self.maxdim} (maximal dimension cells), got {d}"
            )
        if signed:
            return L
        else:
            return abs(L)

    def up_laplacian_matrix(self, d, signed=True, weight=None, index=False):
        if d == 0:
            B_next = self.incidence_matrix(d + 1)
            L_up = B_next @ B_next.transpose()
        elif d < self.maxdim:
            B_next = self.incidence_matrix(d + 1)
            L_up = B_next @ B_next.transpose()
        else:

            raise ValueError(
                f"d should larger than 0 and <= {self.maxdim-1} (maximal dimension cells-1), got {d}"
            )
        if signed:
            return L_up
        else:
            return abs(L_up)

    def down_laplacian_matrix(self, d, signed=True, weight=None, index=False):
        """
        >>> import networkx as nx
        >>> G = nx.path_graph(3)
        >>> CC = CellComplex(G)
        >>> CC.add_cell([1,2,3,4], rank=2)
        >>> CC.add_cell([1,2,3,4], rank=2)
        >>> CC.add_cell([2,3,4,1], rank=2)
        >>> CC.add_cell([1,2,4], rank=2,)
        >>> CC.add_cell([3,4,8], rank=2)
        >>> CC.down_laplacian_matrix(2)

        """

        if d <= self.maxdim and d > 0:
            B = self.incidence_matrix(d)
            L_down = B.transpose() @ B
        else:
            raise ValueError(
                f"d should be larger than 1 and <= {self.maxdim} (maximal dimension cells), got {d}."
            )
        if signed:
            return L_down
        else:
            return abs(L_down)

    def adjacency_matrix(self, d, signed=False, weight=None, index=False):

        L_up = self.up_laplacian_matrix(d, signed=signed)
        L_up.setdiag(0)

        if signed:
            return L_up
        else:
            return abs(L_up)

    def coadjacency_matrix(self, d, signed=False, weight=None, index=False):

        L_down = self.down_laplacian_matrix(d, signed=signed)
        L_down.setdiag(0)
        if signed:
            return L_down
        else:
            return abs(L_down)

    def k_hop_incidence_matrix(self, d, k):
        Bd = self.incidence_matrix(d, signed=True)
        if d < self.maxdim and d >= 0:
            Ad = self.adjacency_matrix(d, signed=True)
        if d <= self.maxdim and d > 0:
            coAd = self.coadjacency_matrix(d, signed=True)
        if d == self.maxdim:
            return Bd @ np.power(coAd, k)
        elif d == 0:
            return Bd @ np.power(Ad, k)
        else:
            return Bd @ np.power(Ad, k) + Bd @ np.power(coAd, k)

    def k_hop_coincidence_matrix(self, d, k):
        BTd = self.coincidence_matrix(d, signed=True)
        if d < self.maxdim and d >= 0:
            Ad = self.adjacency_matrix(d, signed=True)
        if d <= self.maxdim and d > 0:
            coAd = self.coadjacency_matrix(d, signed=True)
        if d == self.maxdim:
            return np.power(coAd, k) @ BTd
        elif d == 0:
            return np.power(Ad, k) @ BTd
        else:
            return np.power(Ad, k) @ BTd + np.power(coAd, k) @ BTd

    def adjacency_matrix(self, d, signed=True, weight=None, index=False):
        """
        The sparse weighted :term:`s-adjacency matrix`

        Parameters
        ----------
        r,k : two ranks for skeletons in the input cell complex, such that r<k

        s : int, optional, default: 1

        index: boolean, optional, default: False
            if True, will return a rowdict of row to node uid

        weight: bool, default=True
            If False all nonzero entries are 1.
            If True adjacency matrix will depend on weighted incidence matrix,
        index : book, default=False
            indicate weather to return the indices of the adjacency matrix.

        Returns
        -------
        If index is True
            adjacency_matrix : scipy.sparse.csr.csr_matrix

            row dictionary : dict

        If index if False

            adjacency_matrix : scipy.sparse.csr.csr_matrix
        >>> CX = CellComplex()
        >>> CX.add_cell([1,2,3],rank=2)
        >>> CX.add_cell([1,4],rank=1)
        >>> A0 = CX.adjacency_matrix(0)

        """

        if index:
            MP, row, col = self.incidence_matrix(
                d, signed=False, weight=weight, index=index
            )
        else:
            MP = self.incidence_matrix(d + 1, signed=False, weight=weight, index=index)
        weight = False  ## currently weighting is not supported
        A = self._incidence_to_adjacency(MP, weight=weight)
        if index:
            return A, row
        else:
            return A

    def cell_adjacency_matrix(self, signed=True, weight=None, index=False):
        """
        >>> CX = CellComplex()
        >>> CX.add_cell([1,2,3],rank=2)
        >>> CX.add_cell([1,4],rank=1)
        >>> A = CX.cell_adjacency_matrix()


        """

        CC = self.to_combinatorial_complex()
        weight = False  ## Currently default weight are not supported

        M = CC.incidence_matrix(0, None, incidence_type="up", index=index)
        if index:

            A = CC._incidence_to_adjacency(M[0].transpose())

            return A, M[2]
        else:
            A = CC._incidence_to_adjacency(M.transpose())
            return A

    def node_adjacency_matrix(self, index=False, s=1, weight=False):

        CC = self.to_combinatorial_complex()
        weight = False  ## Currently default weight are not supported

        M = CC.incidence_matrix(0, None, incidence_type="up", index=index)
        if index:

            A = CC._incidence_to_adjacency(M[0], s=s)

            return A, M[1]
        else:
            A = CC._incidence_to_adjacency(M, s=s)
            return A

    def restrict_to_cells(self, cellset, name=None):
        """
        Constructs a cell complex using a subset of the cells in cell complex

        Parameters
        ----------
        cellset: iterable of hashables or Cell
            A subset of elements of the cell complex's cells (self.cells)

        name: str, optional

        Returns
        -------
        new cell complex : CellComplex

        Example

        >>> CX = CellComplex()
        >>> c1= Cell((1,2,3))
        >>> c2= Cell((1,2,4))
        >>> c3= Cell((1,2,5))
        >>> CX = CellComplex([c1,c2,c3])
        >>> CX.add_edge(1,0)
        >>> CX1= CX.restrict_to_cells([c1, (0,1) ])
        >>> CX1.cells
        CellView([Cell(1, 2, 3)])

        """
        RNS = []
        edges = []
        for i in cellset:
            if i in self.cells:
                RNS.append(i)
            elif i in self.edges:
                edges.append(i)

        CX = CellComplex(cells=RNS, name=name)
        for i in edges:
            CX.add_edge(i[0], i[1])
        return CX

    def restrict_to_nodes(self, nodeset, name=None):
        """
        Constructs a new cell complex  by restricting the cells in the cell complex to
        the nodes referenced by nodeset.

        Parameters
        ----------
        nodeset: iterable of hashables
            References a subset of elements of self.nodes

        name: string, optional, default: None

        Returns
        -------
        new Cell Complex : Cellcomplex

        Example
        >>> CX = CellComplex()
        >>> c1= Cell((1,2,3))
        >>> c2= Cell((1,2,4))
        >>> c3= Cell((1,2,5))
        >>> CX = CellComplex([c1,c2,c3])
        >>> CX.add_edge(1,0)
        >>> CX.restrict_to_nodes([1,2,3,0])

        """

        _G = Graph(self._G.subgraph(nodeset))
        CX = CellComplex(_G)
        cells = []
        for cell in self.cells:
            if CX.is_insertable_cycle(cell, True):
                cells.append(cell)
        CX = CellComplex(_G)

        for e in cells:
            CX.add_cell(e)
        return CX

    def to_combinatorial_complex(self):
        """
        >>> CX = CellComplex()
        >>> CX.add_cell([1,2,3,4],rank=2)
        >>> CX.add_cell([2,3,4,5],rank=2)
        >>> CX.add_cell([5,6,7,8],rank=2)
        >>> CC= CX.to_combinatorial_complex()
        >>> CC.cells
        """
        all_cells = []

        for n in self.nodes:
            all_cells.append(Node(elements=n, **self.nodes[n]))

        for e in self.edges:
            all_cells.append(CellObject(elements=e, rank=1, **self.edges[e]))
        for cell in self.cells:
            all_cells.append(
                CellObject(elements=cell.elements, rank=2, **self.cells[cell])
            )
        return CombinatorialComplex(RankedEntitySet("", all_cells), name="_")

    def to_hypergraph(self):

        """
        Example
            >>> CX = CellComplex()
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([2,3,4,5],rank=2)
            >>> CX.add_cell([5,6,7,8],rank=2)
            >>> HG = CX.to_hypergraph()
            >>> HG

        """
        from hypernetx.classes.entity import EntitySet

        cells = []
        for n in self.cells:
            cells.append(Entity(str(list(n.elements)), elements=n.elements))
        for n in self.edges:
            cells.append(Entity(str(list(n)), elements=n))
        E = EntitySet("CX_to_HG", elements=cells)
        HG = Hypergraph(E)
        nodes = []
        for n in self.nodes:
            nodes.append(Entity(n, elements=[]))
        HG._add_nodes_from(nodes)
        return HG

    def is_connected(self, s=1, cells=False):
        """
        Determines if cell complex is :term:`s-connected <s-connected, s-node-connected>`.

        Parameters
        ----------
        s: int, optional, default: 1

        cells: boolean, optional, default: False
            If True, will determine if s-cell-connected.
            For s=1 s-cell-connected is the same as s-connected.

        Returns
        -------
        is_connected : boolean

        Notes
        -----

        A CX is s node connected if for any two nodes v0,vn
        there exists a sequence of nodes v0,v1,v2,...,v(n-1),vn
        such that every consecutive pair of nodes v(i),v(i+1)
        share at least s cell.


        """
        import networkx as nx

        return nx.is_connected(self._G)

    def singletons(self):
        """
        Returns a list of singleton cell. A singleton cell is a node of degree 0.

        Returns
        -------
        singles : list
            A list of cells uids.

            >>> CX = CellComplex()
            >>> CX.add_cell([1,2,3,4],rank=2)
            >>> CX.add_cell([2,3,4,5],rank=2)
            >>> CX.add_cell([5,6,7,8],rank=2)
            >>> CX.add_node(0)
            >>> CX.add_node(10)
            >>> CX.singletons()

        """

        return [i for i in self.nodes if self.degree(i) == 0]

    def remove_singletons(self, name=None):
        """
        Constructs clone of cell complex with singleton cells removed.

        Parameters
        ----------
        name: str, optional, default: None

        Returns
        -------
        Cell Complex : CellComplex


        """

        for n in self.singletons():
            self._G.remove_node(n)

    def s_connected_components(self, s=1, cells=True, return_singletons=False):
        """
        Returns a generator for the :term:`s-cell-connected components <s-cell-connected component>`
        or the :term:`s-node-connected components <s-connected component, s-node-connected component>`
        of the cell complex.

        Parameters
        ----------
        s : int, optional, default: 1

        cells : boolean, optional, default: True
            If True will return cell components, if False will return node components
        return_singletons : bool, optional, default : False

        Notes
        -----
        If cells=True, this method returns the s-cell-connected components as
        lists of lists of cell uids.
        An s-cell-component has the property that for any two cells e1 and e2
        there is a sequence of cells starting with e1 and ending with e2
        such that pairwise adjacent cells in the sequence intersect in at least
        s nodes. If s=1 these are the path components of the CC.

        If cells=False this method returns s-node-connected components.
        A list of sets of uids of the nodes which are s-walk connected.
        Two nodes v1 and v2 are s-walk-connected if there is a
        sequence of nodes starting with v1 and ending with v2 such that pairwise
        adjacent nodes in the sequence share s cells. If s=1 these are the
        path components of the cell complex .

        Example
        -------


        Yields
        ------
        s_connected_components : iterator
            Iterator returns sets of uids of the cells (or nodes) in the s-cells(node)
            components of CC.

        """

        if cells:
            A, coldict = self.cell_adjacency_matrix(s=s, index=True)
            G = nx.from_scipy_sparse_matrix(A)

            for c in nx.connected_components(G):
                if not return_singletons and len(c) == 1:
                    continue
                yield {coldict[n] for n in c}
        else:
            A, rowdict = self.node_adjacency_matrix(s=s, index=True)
            G = nx.from_scipy_sparse_matrix(A)
            for c in nx.connected_components(G):
                if not return_singletons:
                    if len(c) == 1:
                        continue
                yield {rowdict[n] for n in c}

    def s_component_subgraphs(self, s=1, cells=True, return_singletons=False):
        """
        Returns a generator for the induced subgraphs of s_connected components.
        Removes singletons unless return_singletons is set to True.
        Parameters
        ----------
        s : int, optional, default: 1

        cells : boolean, optional, cells=False
            Determines if cell or node components are desired. Returns
            subgraphs equal to the CC restricted to each set of nodes(cells) in the
            s-connected components or s-cell-connected components
        return_singletons : bool, optional

        Yields
        ------
        s_component_subgraphs : iterator
            Iterator returns subgraphs generated by the cells (or nodes) in the
            s-cell(node) components of cell complex.

        """
        for idx, c in enumerate(
            self.s_components(s=s, cells=cells, return_singletons=return_singletons)
        ):
            if cells:
                yield self.restrict_to_cells(c, name=f"{self.name}:{idx}")
            else:
                yield self.restrict_to_cells(c, name=f"{self.name}:{idx}")

    def s_components(self, s=1, cells=True, return_singletons=True):
        """
        Same as s_connected_components

        See Also
        --------
        s_connected_components
        """
        return self.s_connected_components(
            s=s, cells=cells, return_singletons=return_singletons
        )

    def connected_components(self, cells=False, return_singletons=True):
        """
        Same as :meth:`s_connected_components` with s=1, but nodes are returned
        by default. Return iterator.

        See Also
        --------
        s_connected_components
        """
        return self.s_connected_components(cells=cells, return_singletons=True)

    def connected_component_subgraphs(self, return_singletons=True):
        """
        Same as :meth:`s_component_subgraphs` with s=1. Returns iterator

        See Also
        --------
        s_component_subgraphs
        """
        return self.s_component_subgraphs(return_singletons=return_singletons)

    def components(self, cells=False, return_singletons=True):
        """
        Same as :meth:`s_connected_components` with s=1, but nodes are returned
        by default. Return iterator.

        See Also
        --------
        s_connected_components
        """
        return self.s_connected_components(s=1, cells=cells)

    def component_subgraphs(self, return_singletons=False):
        """
        Same as :meth:`s_components_subgraphs` with s=1. Returns iterator.

        See Also
        --------
        s_component_subgraphs
        """
        return self.s_component_subgraphs(return_singletons=return_singletons)

    def node_diameters(self, s=1):
        """
        Returns the node diameters of the connected components in cell complex.

        Parameters
        ----------
        list of the diameters of the s-components and
        list of the s-component nodes
        """

        A, coldict = self.node_adjacency_matrix(s=s, index=True)
        G = nx.from_scipy_sparse_matrix(A)
        diams = []
        comps = []
        for c in nx.connected_components(G):
            diamc = nx.diameter(G.subgraph(c))
            temp = set()
            for e in c:
                temp.add(coldict[e])
            comps.append(temp)
            diams.append(diamc)
        loc = np.argmax(diams)
        return diams[loc], diams, comps

    def cell_diameters(self, s=1):
        """
        Returns the cell diameters of the s_cell_connected component subgraphs
        in CC.

        Parameters
        ----------
        s : int, optional, default: 1

        Returns
        -------
        maximum diameter : int

        list of diameters : list
            List of cell_diameters for s-cell component subgraphs in CC

        list of component : list
            List of the cell uids in the s-cell component subgraphs.

        """

        A, coldict = self.cell_adjacency_matrix(s=s, index=True)
        G = nx.from_scipy_sparse_matrix(A)
        diams = []
        comps = []
        for c in nx.connected_components(G):
            diamc = nx.diameter(G.subgraph(c))
            temp = set()
            for e in c:
                temp.add(coldict[e])
            comps.append(temp)
            diams.append(diamc)
        loc = np.argmax(diams)
        return diams[loc], diams, comps

    def diameter(self, s=1):
        """
        Returns the length of the longest shortest s-walk between nodes in cell complex

        Parameters
        ----------
        s : int, optional, default: 1

        Returns
        -------
        diameter : int

        Raises
        ------
        TopoNetXError
            If CC is not s-cell-connected

        Notes
        -----
        Two nodes are s-adjacent if they share s cells.
        Two nodes v_start and v_end are s-walk connected if there is a sequence of
        nodes v_start, v_1, v_2, ... v_n-1, v_end such that consecutive nodes
        are s-adjacent. If the graph is not connected, an error will be raised.

        """

        A = self.node_adjacency_matrix(s=s)
        G = nx.from_scipy_sparse_matrix(A)
        if nx.is_connected(G):
            return nx.diameter(G)
        else:
            raise TopoNetXError(f"CC is not s-connected. s={s}")

    def cell_diameter(self, s=1):
        """
        Returns the length of the longest shortest s-walk between cells in cell complex

        Parameters
        ----------
        s : int, optional, default: 1

        Return
        ------
        cell_diameter : int

        Raises
        ------
        TopoNetXError
            If cell complex is not s-cell-connected

        Notes
        -----
        Two cells are s-adjacent if they share s nodes.
        Two nodes e_start and e_end are s-walk connected if there is a sequence of
        cells e_start, e_1, e_2, ... e_n-1, e_end such that consecutive cells
        are s-adjacent. If the graph is not connected, an error will be raised.

        """

        A = self.cell_adjacency_matrix(s=s)
        G = nx.from_scipy_sparse_matrix(A)
        if nx.is_connected(G):
            return nx.diameter(G)
        else:
            raise TopoNetXError(f"cell complex is not s-connected. s={s}")

    def distance(self, source, target, s=1):
        """
        Returns the shortest s-walk distance between two nodes in the cell complex.

        Parameters
        ----------
        source : node.uid or node
            a node in the CC

        target : node.uid or node
            a node in the CC

        s : positive integer
            the number of cells

        Returns
        -------
        s-walk distance : int

        See Also
        --------
        cell_distance

        Notes
        -----
        The s-distance is the shortest s-walk length between the nodes.
        An s-walk between nodes is a sequence of nodes that pairwise share
        at least s cells. The length of the shortest s-walk is 1 less than
        the number of nodes in the path sequence.

        Uses the networkx shortest_path_length method on the graph
        generated by the s-adjacency matrix.

        """

        if isinstance(source, Cell):
            source = source.uid
        if isinstance(target, Cell):
            target = target.uid
        A, rowdict = self.node_adjacency_matrix(s=s, index=True)
        g = nx.from_scipy_sparse_matrix(A)
        rkey = {v: k for k, v in rowdict.items()}
        try:
            path = nx.shortest_path_length(g, rkey[source], rkey[target])
            return path
        except:
            warnings.warn(f"No {s}-path between {source} and {target}")
            return np.inf

    def cell_distance(self, source, target, s=1):
        """
        Returns the shortest s-walk distance between two cells in the cell complex.

        Parameters
        ----------
        source : cell.uid or cell
            an cell in the cell complex

        target : cell.uid or cell
            an cell in the cell complex

        s : positive integer
            the number of intersections between pairwise consecutive cells



        Returns
        -------
        s- walk distance : the shortest s-walk cell distance
            A shortest s-walk is computed as a sequence of cells,
            the s-walk distance is the number of cells in the sequence
            minus 1. If no such path exists returns np.inf.

        See Also
        --------
        distance

        Notes
        -----
            The s-distance is the shortest s-walk length between the cells.
            An s-walk between cells is a sequence of cells such that consecutive pairwise
            cells intersect in at least s nodes. The length of the shortest s-walk is 1 less than
            the number of cells in the path sequence.

            Uses the networkx shortest_path_length method on the graph
            generated by the s-cell_adjacency matrix.

        """

        if isinstance(source, Cell):
            source = source.uid
        if isinstance(target, Cell):
            target = target.uid
        A, coldict = self.cell_adjacency_matrix(s=s, index=True)
        g = nx.from_scipy_sparse_matrix(A)
        ckey = {v: k for k, v in coldict.items()}
        try:
            path = nx.shortest_path_length(g, ckey[source], ckey[target])
            return path
        except:
            warnings.warn(f"No {s}-path between {source} and {target}")
            return np.inf

    @staticmethod
    def from_trimesh(mesh):
        """
        >>> import trimesh
        >>> mesh = trimesh.Trimesh(vertices=[[0, 0, 0], [0, 0, 1], [0, 1, 0]],
                               faces=[[0, 1, 2]],
                               process=False)
        >>> CX = CellComplex.from_trimesh(mesh)
        >>> print(CX.nodes)
        >>> print(CX.cells)
        >>> CX.nodes[0]['position']

        """
        # try to see the index of the first vertex

        CX = CellComplex(mesh.faces)

        first_ind = np.min(mesh.faces)

        if first_ind == 0:

            CX.set_node_attributes(
                dict(zip(range(len(mesh.vertices)), mesh.vertices)), name="position"
            )
        else:  # first index starts at 1.

            CX.set_node_attributes(
                dict(
                    zip(range(first_ind, len(mesh.vertices) + first_ind), mesh.vertices)
                ),
                name="position",
            )

        return CX

    @staticmethod
    def from_mesh_file(file_path, process=False, force=None):
        """
        file_path: str, the source of the data to be loadeded

        process : bool, trimesh will try to process the mesh before loading it.

        force: (str or None)
            options: 'mesh' loader will "force" the result into a mesh through concatenation
                     None : will not force the above.
        Note:
            file supported : obj, off, glb
        >>> CX = CellComplex.from_file("/path_to_file/bunny.obj")
        >>> CX.nodes

        """
        import trimesh

        mesh = trimesh.load_mesh(file_path, process=process, force=None)
        return CellComplex.from_trimesh(mesh)
