# Copyright (C) 2009-2013 Kristian B. Oelgaard and Anders Logg
#
# This file is part of FFC.
#
# FFC is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# FFC is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with FFC. If not, see <http://www.gnu.org/licenses/>.
#
# Modified by Garth N. Wells, 2009.
# Modified by Marie Rognes, 2009-2013.
# Modified by Martin Alnaes, 2013
# Modified by Andrew T. T. McRae, 2013
#
# First added:  2009-03-06
# Last changed: 2013-11-03

# Python modules
from numpy import array, polymul, zeros, ones

# UFL and FIAT modules
import ufl
import FIAT

# FFC modules
from ffc.log import debug, error, ffc_assert
from ffc.quadratureelement import QuadratureElement as FFCQuadratureElement
from ffc.timeelements import LobattoElement as FFCLobattoElement
from ffc.timeelements import RadauElement as FFCRadauElement

from ffc.mixedelement import MixedElement
from ffc.restrictedelement import RestrictedElement
from ffc.enrichedelement import SpaceOfReals

# Dictionary mapping from cell to dimension
from ufl.geometry import cell2dim

# Number of entities associated with each cell name
# Need to pass in the full cell for OuterProduct compatibility
# though no useful functionality implemented yet.
def cell_to_num_entities(cell):
    if isinstance(cell, str):
        return cellname_to_num_entities[cell]
    else:
        if isinstance(cell, ufl.OuterProductCell):
            temp_a = cell_to_num_entities(cell._A)
            temp_b = cell_to_num_entities(cell._B)
            temp_list = polymul(temp_a, temp_b)
            # set number of facets to 0 for safety -- we will
            # deal with OP facets separately
            temp_list[-2] = 0
            return tuple(temp_list)
        else:
            return cellname_to_num_entities[cell.cellname()]

cellname_to_num_entities = {
    "cell1D": None,
    "cell2D": None,
    "cell3D": None,
    "interval": (2, 1),
    "triangle": (3, 3, 1),
    "tetrahedron": (4, 6, 4, 1),
    "quadrilateral": (4, 4, 1),
    "hexahedron": (8, 12, 6, 1),
    }

# Element families supported by FFC
supported_families = ("Brezzi-Douglas-Marini",
                      "Brezzi-Douglas-Fortin-Marini",
                      "Crouzeix-Raviart",
                      "Discontinuous Lagrange",
                      "Discontinuous Raviart-Thomas",
                      "Lagrange",
                      "Lobatto",
                      "Nedelec 1st kind H(curl)",
                      "Nedelec 2nd kind H(curl)",
                      "Radau",
                      "Raviart-Thomas",
                      "Real",
                      "Bubble",
                      "Quadrature",
                      "OuterProductElement",
                      "EnrichedElement")

# Mapping from dimension to number of mesh sub-entities. (In principle,
# cellname_to_num_entities contains the same information, but with string keys.)
# DISABLED ON PURPOSE: It's better to use cell name instead of dimension
#                      to stay generic w.r.t. future box elements.
#entities_per_dim = {1: [2, 1], 2: [3, 3, 1], 3: [4, 6, 4, 1]}

# Cache for computed elements
_cache = {}

def reference_cell(cell):
    # really want to be using cells only, but sometimes only cellname is passed
    # in. FIAT handles the cases.
    
    # I hope nothing is still passing in just dimension...
    if isinstance(cell, int):
        error("%s was passed into reference_cell(). Need cell or cellname." % str(cell))

    return FIAT.ufc_cell(cell)

def reference_cell_vertices(cellname):
    "Return dict of coordinates of reference cell vertices for this 'dim'."
    cell = reference_cell(cellname)
    return cell.get_vertices()

def create_element(ufl_element):

    # Create element signature for caching (just use UFL element)
    element_signature = ufl_element

    # Check cache
    if element_signature in _cache:
        debug("Reusing element from cache")
        return _cache[element_signature]

    # Create regular FIAT finite element
    if isinstance(ufl_element, (ufl.FiniteElement, ufl.OuterProductElement, ufl.EnrichedElement)):
        element = _create_fiat_element(ufl_element)

    # Create mixed element (implemented by FFC)
    elif isinstance(ufl_element, ufl.MixedElement):
        elements = _extract_elements(ufl_element)
        element = MixedElement(elements)

    # Create restricted element(implemented by FFC)
    elif isinstance(ufl_element, ufl.RestrictedElement):
        element = _create_restricted_element(ufl_element)

    else:
        error("Cannot handle this element type: %s" % str(ufl_element))

    # Store in cache
    _cache[element_signature] = element

    return element

def _create_fiat_element(ufl_element):
    "Create FIAT element corresponding to given finite element."

    # Get element data
    family = ufl_element.family()
    domain, = ufl_element.domains() # Assuming single domain
    cell = domain.cell()            # Assuming single cell in domain
    degree = ufl_element.degree()

    # Check that FFC supports this element
    ffc_assert(family in supported_families,
               "This element family (%s) is not supported by FFC." % family)

    # Handle the space of the constant
    if family == "Real":
        dg0_element = ufl.FiniteElement("DG", domain, 0)
        constant = _create_fiat_element(dg0_element)
        element = SpaceOfReals(constant)

    # Handle the specialized time elements
    elif family == "Lobatto" :
        element = FFCLobattoElement(ufl_element.degree())

    elif family == "Radau" :
        element = FFCRadauElement(ufl_element.degree())

    # FIXME: AL: Should this really be here?
    # Handle QuadratureElement
    elif family == "Quadrature":
        element = FFCQuadratureElement(ufl_element)

    else:
        # Check if finite element family is supported by FIAT
        if not family in FIAT.supported_elements:
            error("Sorry, finite element of type \"%s\" are not supported by FIAT.", family)

        # Create FIAT finite element
        ElementClass = FIAT.supported_elements[family]
        
        # Enriched case
        if isinstance(ufl_element, ufl.EnrichedElement):
            A = create_element(ufl_element._elements[0])
            B = create_element(ufl_element._elements[1])
            element = ElementClass(A, B)
        # Tensor Product case
        elif isinstance(ufl_element, ufl.HDiv):
            element = FIAT.Hdiv(create_element(ufl_element._element))
        elif isinstance(ufl_element, ufl.HCurl):
            element = FIAT.Hcurl(create_element(ufl_element._element))
        elif family == "OuterProductElement":
            A = create_element(ufl_element._A)
            B = create_element(ufl_element._B)
            element = ElementClass(A, B)
        else:
            fiat_cell = reference_cell(cell)
            if degree is None:
                element = ElementClass(fiat_cell)
            else:
                element = ElementClass(fiat_cell, degree)

    # Consistency check between UFL and FIAT elements. This will not hold for elements
    # where the reference value shape is different from the global value shape, i.e.
    # RT elements on a triangle in 3D.
    #ffc_assert(element.value_shape() == ufl_element.value_shape(),
    #           "Something went wrong in the construction of FIAT element from UFL element." + \
    #           "Shapes are %s and %s." % (element.value_shape(), ufl_element.value_shape()))

    return element

def create_quadrature(cell, num_points):
    """
    Generate quadrature rule (points, weights) for given shape with
    num_points points in each direction.
    """

    if isinstance(cell, int) and cell == 0:
        return ([()], array([1.0,]))

    if cell2dim(cell) == 0:
        return ([()], array([1.0,]))

    quad_rule = FIAT.make_quadrature(reference_cell(cell), num_points)
    return quad_rule.get_points(), quad_rule.get_weights()

def map_facet_points(points, facet, facet_type):
    """
    Map points from the e (UFC) reference simplex of dimension d - 1
    to a given facet on the (UFC) reference simplex of dimension d.
    This may be used to transform points tabulated for example on the
    2D reference triangle to points on a given facet of the reference
    tetrahedron.
    """

    # Extract the geometric dimension of the points we want to map
    dim = len(points[0]) + 1

    # Special case, don't need to map coordinates on vertices
    if dim == 1:
        return [[(0.0,), (1.0,)][facet]]

    if facet_type == "facet":
        # Get the FIAT reference cell for this dimension
        # This was a temporary hack that doesn't work with
        # facets on OuterProduct cells!
        # However, facets on OP cells we have facet_type "horiz_facet"
        # or "vert_facet", so don't reach here
        fiat_cell = reference_cell({2: "triangle", 3: "tetrahedron"}[dim])

        # Extract vertex coordinates from cell and map of facet index to
        # indicent vertex indices
        vertex_coordinates = fiat_cell.get_vertices()
        facet_vertices = fiat_cell.get_topology()[dim-1]

        #vertex_coordinates = \
        #    {1: ((0.,), (1.,)),
        #     2: ((0., 0.), (1., 0.), (0., 1.)),
        #     3: ((0., 0., 0.), (1., 0., 0.),(0., 1., 0.), (0., 0., 1))}

        # Facet vertices
        #facet_vertices = \
        #    {2: ((1, 2), (0, 2), (0, 1)),
        #     3: ((1, 2, 3), (0, 2, 3), (0, 1, 3), (0, 1, 2))}

        # Compute coordinates and map the points
        coordinates = [vertex_coordinates[v] for v in facet_vertices[facet]]
        new_points = []
        for point in points:
            w = (1.0 - sum(point),) + tuple(point)
            x = tuple(sum([w[i]*array(coordinates[i]) for i in range(len(w))]))
            new_points += [x]

    elif facet_type == "horiz_facet":
        # A horiz_facet must be on the bottom (0) or top (1) of an
        # extruded cell. Simply take the point and append a final
        # coordinate of 0.0 or 1.0, as appropriate.
        if facet == 0:
            new_points = zeros((points.shape[0], points.shape[1]+1))
            new_points[:,:-1] = points
        elif facet == 1:
            new_points = ones((points.shape[0], points.shape[1]+1))
            new_points[:,:-1] = points
        else:
            raise Exception("facet number must be 0 or 1 for horiz_facet")

    elif facet_type == "vert_facet":
        # A vert_facet is one of the sides of the extruded cell. In particular,
        # the vertical facets are themselves OuterProductCells.
        # To do the mapping, we temporarily ignore the last coordinate
        # of each point. We send the remaining coordinates back through
        # this function as a normal facet of one degree less,
        # then append the last coordinate back on.
        temp_points = map_facet_points(points[:,:-1], facet, "facet")
        new_points = zeros((points.shape[0], points.shape[1]+1))
        new_points[:,:-1] = temp_points
        new_points[:,-1] = points[:,-1]
    else:
        raise Exception("facet type not recognised")

    return new_points

def _extract_elements(ufl_element, domain=None):
    "Recursively extract un-nested list of (component) elements."

    elements = []
    if isinstance(ufl_element, ufl.MixedElement):
        for sub_element in ufl_element.sub_elements():
            elements += _extract_elements(sub_element, domain)
        return elements

    # Handle restricted elements since they might be mixed elements too.
    if isinstance(ufl_element, ufl.RestrictedElement):
        base_element = ufl_element.element()
        restriction = ufl_element.cell_restriction()
        return _extract_elements(base_element, restriction)

    if domain:
        ufl_element = ufl.RestrictedElement(ufl_element, domain)

    elements += [create_element(ufl_element)]

    return elements

def _create_restricted_element(ufl_element):
    "Create an FFC representation for an UFL RestrictedElement."

    if not isinstance(ufl_element, ufl.RestrictedElement):
        error("create_restricted_element expects an ufl.RestrictedElement")

    base_element = ufl_element.element()
    restriction_domain = ufl_element.cell_restriction()

    # If simple element -> create RestrictedElement from fiat_element
    if isinstance(base_element, ufl.FiniteElement):
        element = _create_fiat_element(base_element)
        return RestrictedElement(element, _indices(element, restriction_domain), restriction_domain)

    # If restricted mixed element -> convert to mixed restricted element
    if isinstance(base_element, ufl.MixedElement):
        elements = _extract_elements(base_element, restriction_domain)
        return MixedElement(elements)

    error("Cannot create restricted element from %s" % str(ufl_element))

def _indices(element, restriction_domain, dim=0):
    "Extract basis functions indices that correspond to restriction_domain."

    # FIXME: The restriction_domain argument in FFC/UFL needs to be re-thought and
    # cleaned-up.

    # If restriction_domain is "interior", pick basis functions associated with
    # cell.
    if restriction_domain == "interior" and dim:
        return element.entity_dofs()[dim][0]

    # If restriction_domain is a ufl.Cell, pick basis functions associated with
    # the topological degree of the restriction_domain and of all lower
    # dimensions.
    if isinstance(restriction_domain, ufl.Cell):
        dim = restriction_domain.topological_dimension()
        entity_dofs = element.entity_dofs()
        indices = []
        for dim in range(restriction_domain.topological_dimension() + 1):
            entities = entity_dofs[dim]
            for (entity, index) in entities.iteritems():
                indices += index
        return indices

    # Just extract all indices to make handling in RestrictedElement
    # uniform.
    #elif isinstance(restriction_domain, ufl.Measure):
    #    indices = []
    #    entity_dofs = element.entity_dofs()
    #    for dim, entities in entity_dofs.items():
    #        for entity, index in entities.items():
    #            indices += index
    #    return indices

    else:
        error("Restriction to domain: %s, is not supported." % repr(restriction_domain))
