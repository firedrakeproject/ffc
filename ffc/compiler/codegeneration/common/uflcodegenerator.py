__author__ = "Anders Logg (logg@simula.no)"
__date__ = "2007-03-06 -- 2009-03-08"
__copyright__ = "Copyright (C) 2007-2009 Anders Logg"
__license__  = "GNU GPL version 3 or any later version"

# Code generation modules
from dofmap import *
from finiteelement import *
from form import *

def generate_common_code(form_data, format):
    "Generate common form code according to given format."

    code = {}

    # Generate code for finite elements
    code["finite_elements"] = _generate_finite_elements(form_data.ffc_elements, format)

    # Generate code for dof maps
    code["dof_maps"] = _generate_dof_maps(form_data.ffc_dof_maps, format)

    # Generate code for form
    debug("Generating code for form...")
    code["form"] = generate_form(form_data, format)
    debug("done")

    return code

def _generate_finite_elements(elements, format):
    "Generate code for finite elements, including recursively nested sub elements."

    debug("Generating code for finite elements...")
    code = []

    # Iterate over form elements
    for i in range(len(elements)):

        # Extract sub elements
        sub_elements = _extract_sub_elements(elements[i], (i,))

        # Generate code for each element
        for (label, sub_element) in sub_elements:
            code += [(label, generate_finite_element(sub_element, format))]
                
    debug("done")
    return code

def _generate_dof_maps(dof_maps, format):
    "Generate code for dof maps, including recursively nested dof maps."
    
    debug("Generating code for finite dof maps...")
    code = []

    # Iterate over form dof maps
    for i in range(len(dof_maps)):

        # Extract sub dof maps
        sub_dof_maps = _extract_sub_dof_maps(dof_maps[i], (i,))

        # Generate code for each dof map
        for (label, sub_dof_map) in sub_dof_maps:
            code += [(label, generate_dof_map(sub_dof_map, format))]
                
    debug("done")
    return code

def _extract_sub_elements(element, parent):
    """Recursively extract sub elements as a list of tuples where
    each tuple consists of a tuple labeling the sub element and
    the sub element itself."""
    
    if element.num_sub_elements() == 1:
        return [(parent, element)]
    sub_elements = []
    for i in range(element.num_sub_elements()):
        sub_elements += _extract_sub_elements(element.sub_element(i), parent + (i,))
    return sub_elements + [(parent, element)]

def _extract_sub_dof_maps(dof_map, parent):
    """Recursively extract sub dof maps as a list of tuples where
    each tuple consists of a tuple labeling the sub dof map and
    the sub dof map itself."""
    
    if dof_map.num_sub_dof_maps() == 1:
        return [(parent, dof_map)]
    sub_dof_maps = []
    for i in range(dof_map.num_sub_dof_maps()):
        sub_dof_maps += _extract_sub_dof_maps(dof_map.sub_dof_map(i), parent + (i,))
    return sub_dof_maps + [(parent, dof_map)]
