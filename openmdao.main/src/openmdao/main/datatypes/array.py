"""
Trait for numpy array variables, with optional units.
"""

#public symbols
__all__ = ["Array"]

import logging

# pylint: disable-msg=E0611,F0401
from openmdao.units import PhysicalQuantity

from openmdao.main.attrwrapper import AttrWrapper, UnitsAttrWrapper
from openmdao.main.index import get_indexed_value
from openmdao.main.interfaces import implements, IVariable
from openmdao.main.variable import gui_excludes

try:
    from numpy import array, ndarray
except ImportError as err:
    logging.warn("In %s: %r", __file__, err)
    from openmdao.main.numpy_fallback import array, ndarray
    from openmdao.main.variable import Variable
    
    class TraitArray(Variable):
        '''Simple fallback array class for when numpy is not available'''
        
        def __init__(self, **metadata):
            self._shape = metadata.get('shape')
            self._dtype = metadata.get('dtype')
            super(TraitArray, self).__init__(**metadata)
        
        def validate(self, obj, name, value):
            ''' Simple validation'''
            try:
                it = iter(value)
            except:
                msg = "attempted to assign non-iterable value to an array"
                raise ValueError(msg)
            
            # FIXME: improve type checking
            if self._dtype:
                return array(value, dtype=self._dtype)
            else:
                return array(value)
else:
    from enthought.traits.api import Array as TraitArray


class Array(TraitArray):
    """A variable wrapper for a numpy array with optional units.
    The unit applies to the entire array."""
    
    implements(IVariable)

    def __init__(self, default_value=None, dtype = None, shape = None,
                 iotype=None, desc=None, units=None, **metadata):
        
        # Determine default_value if unspecified
        if default_value is None:
            if shape is None or len(shape) == 1:
                default_value = array([])
            elif len(shape) == 2:
                default_value = array([[]])
            elif len(shape) == 3:
                default_value = array([[[]]])
                    
        elif isinstance(default_value, ndarray):
            pass
        elif isinstance(default_value, list):
            default_value = array(default_value)
        else:
            raise TypeError("Default value should be an array-like object, "
                             "not a %s." % type(default_value))
        
        # Put iotype in the metadata dictionary
        if iotype is not None:
            metadata['iotype'] = iotype
            
        # Put desc in the metadata dictionary
        if desc is not None:
            metadata['desc'] = desc
            
        # Put units in the metadata dictionary
        if units is not None:
            metadata['units'] = units
            
            # Since there are units, test them by creating a physical quantity
            try:
                pq = PhysicalQuantity(0., metadata['units'])
            except:
                raise ValueError("Units of '%s' are invalid" %
                                 metadata['units'])
            
        # Put shape in the metadata dictionary
        if shape is not None:
            metadata['shape'] = shape
            
            # Make sure default matches the shape.
            if len(shape) != len(default_value.shape):
                raise ValueError("Shape of the default value does not match "
                                 "the shape attribute.")
            for i, sh in enumerate(shape):
                if sh is not None and sh != default_value.shape[i]:
                    raise ValueError("Shape of the default value does not "
                                     "match the shape attribute.")
            
        super(Array, self).__init__(dtype=dtype, value=default_value,
                                    **metadata)


    def validate(self, obj, name, value):
        """ Validates that a specified value is valid for this trait.
        Units are converted as needed.
        """
        
        # pylint: disable-msg=E1101
        # If both source and target have units, we need to process differently
        if isinstance(value, AttrWrapper):
            if self.units:
                valunits = value.metadata.get('units')
                if valunits and isinstance(valunits, basestring) and \
                   self.units != valunits:
                    return self._validate_with_metadata(obj, name, 
                                                        value.value, 
                                                        valunits)
            
            value = value.value
            
        try:
            return super(Array, self).validate(obj, name, value)
        except Exception:
            self.error(obj, name, value)

    def error(self, obj, name, value):
        """Returns an informative and descriptive error string."""
        
        wtype = "value"
        wvalue = value
        info = "an array-like object"
        
        # pylint: disable-msg=E1101
        if self.shape and hasattr(value, 'shape') and value.shape:
            if self.shape != value.shape:
                info += " of shape %s" % str(self.shape)
                wtype = "shape"
                wvalue = str(value.shape)

        vtype = type( value )
        msg = "Variable '%s' must be %s, but a %s of %s (%s) was specified." % \
                               (name, info, wtype, wvalue, vtype)
        try:
            obj.raise_exception(msg, ValueError)
        except AttributeError:
            raise ValueError(msg)

    def get_val_wrapper(self, value, index=None):
        """Return a UnitsAttrWrapper object.  Its value attribute
        will be filled in by the caller.
        """
        # pylint: disable-msg=E1101
        if index is not None:
            value = get_indexed_value(value, None, index)
        if self.units:
            return UnitsAttrWrapper(value, units=self.units)
        else:
            return value

    def _validate_with_metadata(self, obj, name, value, src_units):
        """Perform validation and unit conversion using metadata from
        the source trait.
        """
        
        # pylint: disable-msg=E1101
        dst_units = self.units

        try:
            pq = PhysicalQuantity(1.0, src_units)
        except NameError:
            raise NameError("while setting value of %s: undefined unit '%s'" %
                            (src_units, name))
        
        try:
            pq.convert_to_unit(dst_units)
        except NameError:
            raise NameError("undefined unit '%s' for variable '%s'" %
                            (dst_units, name))
        except TypeError:
            msg = "%s: units '%s' are incompatible " % (name, src_units) + \
                   "with assigning units of '%s'" % (dst_units)
            raise TypeError(msg)
        
        try:
            value *= pq.value
            return super(Array, self).validate(obj, name, value)
        except Exception:
            self.error(obj, name, value)

    def get_attribute(self, name, value, trait, meta):
        """Return the attribute dictionary for this variable. This dict is
        used by the GUI to populate the edit UI. 
        
        name: str
          Name of variable
          
        value: object
          The value of the variable
          
        value: object
          Value of variable
          
        meta: dict
          Dictionary of metadata for this variable
        """
        
        attr = {}
        
        attr['name'] = name
        attr['type'] = "ndarray"
        attr['value'] = str(value)
        
        for field in meta:
            if field not in gui_excludes:
                attr[field] = meta[field]
        
        return attr, None

            
# register a flattener for Cases
from openmdao.main.case import flatteners

def _flatten_array(name, arr):
    ret = []
    
    def _recurse_flatten(ret, name, idx, arr):
        for i, entry in enumerate(arr):
            new_idx = idx+[i]
            if isinstance(entry, (ndarray, list)):
                _recurse_flatten(ret, name, new_idx, entry)
            else:
                idxstr = ''.join(["[%d]" % j for j in new_idx])
                ret.append(("%s%s" % (name, idxstr), entry))
    
    _recurse_flatten(ret, name, [], arr)
    return ret
        
flatteners[ndarray] = _flatten_array
flatteners[array] = _flatten_array
