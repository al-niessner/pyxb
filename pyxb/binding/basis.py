# -*- coding: utf-8 -*-
# Copyright 2009-2013, Peter A. Bigot
#
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

"""This module contains support classes from which schema-specific bindings
inherit, and that describe the content models of those schema."""

import logging
import collections.abc
import xml.dom
import pyxb
from pyxb.utils import domutils, utility, sal as six
import pyxb.namespace
from pyxb.namespace.builtin import XMLSchema_instance as XSI
import decimal

try:
    from collections import Iterable
except ImportError:
    from collections.abc import Iterable

_log = logging.getLogger(__name__)

class _TypeBinding_mixin (utility.Locatable_mixin):
    # Private member holding the validation configuration that applies to the
    # class or instance.  Can't really make it private with __ prefix because
    # that would screw up parent classes.  You end users---stay away from
    # this.
    _validationConfig_ = pyxb.GlobalValidationConfig

    @classmethod
    def _SetValidationConfig (cls, validation_config):
        """Set the validation configuration for this class."""
        cls._validationConfig_ = validation_config

    @classmethod
    def _GetValidationConfig (cls):
        """The L{pyxb.ValidationConfig} instance that applies to this class.

        By default this will reference L{pyxb.GlobalValidationConfig}."""
        return cls._validationConfig_

    def _setValidationConfig (self, validation_config):
        """Set the validation configuration for this instance."""
        self._validationConfig_ = validation_config

    def __getValidationConfig (self):
        """The L{pyxb.ValidationConfig} instance that applies to this instance.

        By default this will reference the class value from
        L{_GetValidationConfig}, which defaults to
        L{pyxb.GlobalValidationConfig}."""
        return self._validationConfig_

    # This is how you should be accessing this value.
    _validationConfig = property(__getValidationConfig)

    @classmethod
    def _PerformValidation (cls):
        """Determine whether the content model should be validated for this class.

        In the absence of context, this returns C{True} iff both binding and
        document validation are in force.

        @deprecated: use L{_GetValidationConfig} and check specific requirements."""
        # Bypass the property since this is a class method
        vo = cls._validationConfig_
        return vo.forBinding and vo.forDocument

    def _performValidation (self):
        """Determine whether the content model should be validated for this
        instance.

        In the absence of context, this returns C{True} iff both binding and
        document validation are in force.

        @deprecated: use L{_validationConfig} and check specific requirements."""
        vo = self._validationConfig
        return vo.forBinding and vo.forDocument

    _ExpandedName = None
    """The expanded name of the component."""

    _XSDLocation = None
    """Where the definition can be found in the originating schema."""

    _ReservedSymbols = set([ 'validateBinding', 'toDOM', 'toxml', 'Factory', 'property' ])

    if pyxb._CorruptionDetectionEnabled:
        def __setattr__ (self, name, value):
            if name in self._ReservedSymbols:
                raise pyxb.ReservedNameError(self, name)
            return super(_TypeBinding_mixin, self).__setattr__(name, value)

    _PyXBFactoryKeywords = ( '_dom_node', '_fallback_namespace', '_from_xml',
                             '_apply_whitespace_facet', '_validate_constraints',
                             '_require_value', '_nil', '_element', '_apply_attributes',
                             '_convert_string_values', '_location' )
    """Keywords that are interpreted by __new__ or __init__ in one or more
    classes in the PyXB type hierarchy.  All these keywords must be removed
    before invoking base Python __init__ or __new__."""

    # While simple type definitions cannot be abstract, they can appear in
    # many places where complex types can, so we want it to be legal to test
    # for abstractness without checking whether the object is a complex type.
    _Abstract = False

    def _namespaceContext (self):
        """Return a L{namespace context <pyxb.binding.NamespaceContext>}
        associated with the binding instance.

        This will return C{None} unless something has provided a context to
        the instance.  Context is provided when instances are generated by the
        DOM and SAX-based translators."""
        return self.__namespaceContext
    def _setNamespaceContext (self, namespace_context):
        """Associate a L{namespace context <pyxb.binding.NamespaceContext>}
        with the binding instance."""
        self.__namespaceContext = namespace_context
        return self
    __namespaceContext = None

    def _setElement (self, elt):
        """Associate an element binding with the instance.

        Since the value of a binding instance reflects only its content, an
        associated element is necessary to generate an XML document or DOM
        tree.

        @param elt: the L{pyxb.binding.basis.element} instance associated with
        the value.  This may be C{None} when disassociating a value from a
        specific element."""
        import pyxb.binding.content
        assert (elt is None) or isinstance(elt, element)
        self.__element = elt
        return self
    def _element (self):
        """Return a L{pyxb.binding.basis.element} associated with the binding
        instance.

        This will return C{None} unless an element has been associated.
        Constructing a binding instance using the element instance will add
        this association.
        """
        return self.__element
    __element = None

    __xsiNil = None
    def _isNil (self):
        """Indicate whether this instance is U{nil
        <http://www.w3.org/TR/xmlschema-1/#xsi_nil>}.

        The value is set by the DOM and SAX parsers when building an instance
        from a DOM element with U{xsi:nil
        <http://www.w3.org/TR/xmlschema-1/#xsi_nil>} set to C{true}.

        @return: C{None} if the element used to create the instance is not
        U{nillable<http://www.w3.org/TR/xmlschema-1/#nillable>}.
        If it is nillable, returns C{True} or C{False} depending on
        whether the instance itself is U{nil<http://www.w3.org/TR/xmlschema-1/#xsi_nil>}.
        """
        return self.__xsiNil
    def _setIsNil (self, nil=True):
        """Set the xsi:nil property of the instance.

        @param nil: C{True} if the value of xsi:nil should be C{true},
        C{False} if the value of xsi:nil should be C{false}.

        @raise pyxb.NoNillableSupportError: the instance is not associated
        with an element that is L{nillable
        <pyxb.binding.basis.element.nillable>}.
        """
        if self.__xsiNil is None:
            raise pyxb.NoNillableSupportError(self)
        self.__xsiNil = not not nil
        if self.__xsiNil:
            # The element must be empty, so also remove all element content.
            # Attribute values are left unchanged.
            self._resetContent(reset_elements=True)

    def _resetContent (self, reset_elements=False):
        """Reset the content of an element value.

        This is not a public method.

        For simple types, this does nothing. For complex types, this clears the
        L{content<complexTypeDefinition.content>} array, removing all
        non-element content from the instance.  It optionally also removes all
        element content.

        @param reset_elements: If C{False} (default) only the content array is
        cleared, which has the effect of removing any preference for element
        order when generating a document.  If C{True}, the element content
        stored within the binding is also cleared, leaving it with no content
        at all.

        @note: This is not the same thing as L{complexTypeDefinition.reset},
        which unconditionally resets attributes and element and non-element
        content.
        """
        pass

    __constructedWithValue = False
    def __checkNilCtor (self, args):
        self.__constructedWithValue = (0 < len(args))
        if self.__xsiNil:
            if self.__constructedWithValue:
                raise pyxb.ContentInNilInstanceError(self, args[0])
        else:
            # Types that descend from string will, when constructed from an
            # element with empty content, appear to have no constructor value,
            # while in fact an empty string should have been passed.
            if issubclass(type(self), six.string_types):
                self.__constructedWithValue = True
    def _constructedWithValue (self):
        return self.__constructedWithValue

    # Flag used to control whether we print a warning when creating a complex
    # type instance that does not have an associated element.  Not sure yet
    # whether that'll be common practice or common error.
    __WarnedUnassociatedElement = False

    def __init__ (self, *args, **kw):
        # Strip keyword not used above this level.
        element = kw.pop('_element', None)
        is_nil = kw.pop('_nil', False)
        super(_TypeBinding_mixin, self).__init__(*args, **kw)
        if (element is None) or element.nillable():
            self.__xsiNil = is_nil
        if element is not None:
            self._setElement(element)
        self.__checkNilCtor(args)

    @classmethod
    def _PreFactory_vx (cls, args, kw):
        """Method invoked upon entry to the Factory method.

        This method is entitled to modify the keywords array.  It can also
        return a state value which is passed to _postFactory_vx."""
        return None

    def _postFactory_vx (cls, state):
        """Method invoked prior to leaving the Factory method.

        This is an instance method, and is given the state that was returned
        by _PreFactory_vx."""
        return None

    @classmethod
    def Factory (cls, *args, **kw):
        """Provide a common mechanism to create new instances of this type.

        The class constructor won't do, because you can't create
        instances of union types.

        This method may be overridden in subclasses (like STD_union).  Pre-
        and post-creation actions can be customized on a per-class instance by
        overriding the L{_PreFactory_vx} and L{_postFactory_vx} methods.

        @keyword _dom_node: If provided, the value must be a DOM node, the
        content of which will be used to set the value of the instance.

        @keyword _location: An optional instance of
        L{pyxb.utils.utility.Location} showing the origin the binding.  If
        C{None}, a value from C{_dom_node} is used if available.

        @keyword _from_xml: If C{True}, the input must be either a DOM node or
        a unicode string comprising a lexical representation of a value.  This
        is a further control on C{_apply_whitespace_facet} and arises from
        cases where the lexical and value representations cannot be
        distinguished by type.  The default value is C{True} iff C{_dom_node}
        is not C{None}.

        @keyword _apply_whitespace_facet: If C{True} and this is a
        simpleTypeDefinition with a whiteSpace facet, the first argument will
        be normalized in accordance with that facet prior to invoking the
        parent constructor.  The value is always C{True} if text content is
        extracted from a C{_dom_node}, and otherwise defaults to the defaulted
        value of C{_from_xml}.

        @keyword _validate_constraints: If C{True}, any constructed value is
        checked against constraints applied to the union as well as the member
        type.

        @keyword _require_value: If C{False} (default), it is permitted to
        create a value without an initial value.  If C{True} and no initial
        value was provided, causes L{pyxb.SimpleContentAbsentError} to be raised.
        Only applies to simpleTypeDefinition instances; this is used when
        creating values from DOM nodes.
        """
        # Invoke _PreFactory_vx for the superseding class, which is where
        # customizations will be found.
        dom_node = kw.get('_dom_node')
        location = kw.get('_location')
        if (location is None) and isinstance(dom_node, utility.Locatable_mixin):
            location = dom_node._location()
        kw.setdefault('_from_xml', dom_node is not None)
        used_cls = cls._SupersedingClass()
        state = used_cls._PreFactory_vx(args, kw)
        rv = cls._DynamicCreate(*args, **kw)
        rv._postFactory_vx(state)
        if (rv._location is None) and (location is not None):
            rv._setLocation(location)
        return rv

    def _substitutesFor (self, element):
        if (element is None) or (self._element() is None):
            return False
        return self._element().substitutesFor(element)

    @classmethod
    def _IsUrType (cls):
        """Return C{True} iff this is the ur-type.

        The only ur-type is {http://www.w3.org/2001/XMLSchema}anyType.  The
        implementation of this method is overridden for
        L{pyxb.binding.datatypes.anyType}."""
        return False

    @classmethod
    def _RequireXSIType (cls, value_type):
        if cls._IsUrType():
            # Require xsi:type if value refines xs:anyType
            return value_type != cls
        if cls._Abstract:
            # You can't instantiate an abstract class, so if the element
            # declaration expects one we're gonna need to be told what type
            # this really is.
            return value_type != cls._SupersedingClass()
        # For unions delegate to whether the selected member type requires
        # the attribute.  Most times they won't.
        if issubclass(cls, STD_union):
            for mt in cls._MemberTypes:
                if issubclass(value_type, mt):
                    return mt._RequireXSIType(value_type)
            raise pyxb.LogicError('Union %s instance type %s not sublass of member type?' % (cls, value_type))
        # Otherwise we need the qualifier if the value type extends or
        # restricts the type schema expects.
        return value_type != cls._SupersedingClass()

    @classmethod
    def _CompatibleValue (cls, value, **kw):
        """Return a variant of the value that is compatible with this type.

        Compatibility is defined relative to the type definition associated
        with the element.  The value C{None} is always compatible.  If
        C{value} has a Python type (e.g., C{int}) that is a superclass of the
        required L{_TypeBinding_mixin} class (e.g., C{xs:byte}), C{value} is
        used as a constructor parameter to return a new instance of the
        required type.  Note that constraining facets are applied here if
        necessary (e.g., although a Python C{int} with value C{500} is
        type-compatible with C{xs:byte}, it is outside the value space, and
        compatibility will fail).

        @keyword _convert_string_values: If C{True} (default) and the incoming value is
        a string, an attempt will be made to form a compatible value by using
        the string as a constructor argument to the this class.  This flag is
        set to C{False} when testing automaton transitions.

        @raise pyxb.SimpleTypeValueError: if the value is not both
        type-consistent and value-consistent with the element's type.
        """
        convert_string_values = kw.get('_convert_string_values', True)
        # None is always None
        if value is None:
            return None
        # Already an instance?
        if isinstance(value, cls):
            # @todo: Consider whether we should change the associated _element
            # of this value.  (**Consider** it, don't just do it.)
            return value
        value_type = type(value)
        # All string-based PyXB binding types use unicode, not str
        if six.PY2 and str == value_type:
            value_type = six.text_type

        # See if we got passed a Python value which needs to be "downcasted"
        # to the _TypeBinding_mixin version.
        if issubclass(cls, value_type):
            return cls(value)

        # See if we have a numeric type that needs to be cast across the
        # numeric hierarchy.  int to long is the *only* conversion we accept.
        if isinstance(value, int) and issubclass(cls, six.long_type):
            return cls(value)

        # Same, but for boolean, which Python won't let us subclass
        if isinstance(value, bool) and issubclass(cls, pyxb.binding.datatypes.boolean):
            return cls(value)

        # See if we have convert_string_values on, and have a string type that
        # somebody understands.
        if convert_string_values and value_type == six.text_type:
            return cls(value)

        # Maybe this is a union?
        if issubclass(cls, STD_union):
            for mt in cls._MemberTypes:
                try:
                    return mt._CompatibleValue(value, **kw)
                except:
                    pass

        # Any type is compatible with the corresponding ur-type
        if (pyxb.binding.datatypes.anySimpleType == cls) and issubclass(value_type, simpleTypeDefinition):
            return value
        if pyxb.binding.datatypes.anyType == cls:
            if not isinstance(value, _TypeBinding_mixin):
                _log.info('Created %s instance from value of type %s', cls._ExpandedName, type(value))
                value = cls(value)
            return value

        # Is this the wrapper class that indicates we should create a binding
        # from arguments?
        if isinstance(value, pyxb.BIND):
            return value.createInstance(cls.Factory, **kw)

        # Does the class have simple content which we can convert?
        if cls._IsSimpleTypeContent():
            # NB: byte(34.2) will create a value, but it may not be one we
            # want to accept, so only do this if the output is equal to the
            # input.
            rv = cls.Factory(value)
            if isinstance(rv, simpleTypeDefinition) and (rv == value):
                return rv
            # Python decimal instances do not compare equal to float values;
            # test whether the string representation is equal instead.
            if isinstance(rv, decimal.Decimal) and (str(rv) == str(value)):
                return rv
            if isinstance(rv, complexTypeDefinition) and (rv.value() == value):
                return rv

        # There may be other things that can be converted to the desired type,
        # but we can't tell that from the type hierarchy.  Too many of those
        # things result in an undesirable loss of information: for example,
        # when an all model supports both numeric and string transitions, the
        # candidate is a number, and the string transition is tested first.
        raise pyxb.SimpleTypeValueError(cls, value)

    @classmethod
    def _IsSimpleTypeContent (cls):
        """Return True iff the content of this binding object is a simple type.

        This is true only for descendents of simpleTypeDefinition and instances
        of complexTypeDefinition that have simple type content."""
        raise pyxb.LogicError('Failed to override _TypeBinding_mixin._IsSimpleTypeContent')

    # If the type supports wildcard attributes, this describes their
    # constraints.  (If it doesn't, this should remain None.)  Supporting
    # classes should override this value.
    _AttributeWildcard = None

    _AttributeMap = { }
    """Map from expanded names to AttributeUse instances.  Non-empty only in
    L{complexTypeDefinition} subclasses."""

    @classmethod
    def __AttributesFromDOM (cls, node):
        attribute_settings = { }
        for ai in range(0, node.attributes.length):
            attr = node.attributes.item(ai)
            # NB: Specifically do not consider attr's NamespaceContext, since
            # attributes do not accept a default namespace.
            attr_en = pyxb.namespace.ExpandedName(attr)

            # Ignore xmlns and xsi attributes; we've already handled those
            if attr_en.namespace() in ( pyxb.namespace.XMLNamespaces, XSI ):
                continue

            attribute_settings[attr_en] = attr.value
        return attribute_settings

    def _setAttributesFromKeywordsAndDOM (self, kw, dom_node):
        """Invoke self._setAttribute based on node attributes and keywords.

        Though attributes can only legally appear in complexTypeDefinition
        instances, delayed conditional validation requires caching them in
        simpleTypeDefinition.

        @param kw: keywords passed to the constructor.  This map is mutated by
        the call: keywords corresponding to recognized attributes are removed.

        @param dom_node: an xml.dom Node instance, possibly C{None}
        """

        # Extract keywords that match field names
        attribute_settings = { }
        if dom_node is not None:
            attribute_settings.update(self.__AttributesFromDOM(dom_node))
        for fu in six.itervalues(self._AttributeMap):
            iv = kw.pop(fu.id(), None)
            if iv is not None:
                attribute_settings[fu.name()] = iv
        for (attr_en, value_lex) in six.iteritems(attribute_settings):
            self._setAttribute(attr_en, value_lex)

    def toDOM (self, bds=None, parent=None, element_name=None):
        """Convert this instance to a DOM node.

        The name of the top-level element is either the name of the L{element}
        instance associated with this instance, or the XML name of the type of
        this instance.

        @param bds: Support for customizing the generated document
        @type bds: L{pyxb.utils.domutils.BindingDOMSupport}
        @param parent: If C{None}, a standalone document is created;
        otherwise, the created element is a child of the given element.
        @type parent: C{xml.dom.Element} or C{None}
        @rtype: C{xml.dom.Document}
        """

        if bds is None:
            bds = domutils.BindingDOMSupport()
        need_xsi_type = bds.requireXSIType()
        if isinstance(element_name, six.string_types):
            element_name = pyxb.namespace.ExpandedName(bds.defaultNamespace(), element_name)
        if (element_name is None) and (self._element() is not None):
            element_binding = self._element()
            element_name = element_binding.name()
            need_xsi_type = need_xsi_type or element_binding.typeDefinition()._RequireXSIType(type(self))
        if element_name is None:
            raise pyxb.UnboundElementError(self)
        element = bds.createChildElement(element_name, parent)
        if need_xsi_type:
            bds.addAttribute(element, XSI.type, self._ExpandedName)
        self._toDOM_csc(bds, element)
        bds.finalize()
        return bds.document()

    def toxml (self, encoding=None, bds=None, root_only=False, element_name=None):
        """Shorthand to get the object as an XML document.

        If you want to set the default namespace, pass in a pre-configured
        C{bds}.

        @param encoding: The encoding to be used.  See
        @C{xml.dom.Node.toxml()} for a description of why you should always
        pass @C{'utf-8'} here.  Because this method follows the contract of
        the corresponding C{xml.dom.Node} method, it does not automatically
        get the default PyXB output encoding.

        @param bds: Optional L{pyxb.utils.domutils.BindingDOMSupport} instance
        to use for creation. If not provided (default), a new generic one is
        created.

        @param root_only: Set to C{True} to automatically deference the
        C{documentElement} of the resulting DOM node.  This eliminates the XML
        declaration that would otherwise be generated.

        @param element_name: This value is passed through to L{toDOM}, and is
        useful when the value has no bound element but you want to convert it
        to XML anyway.
        """
        dom = self.toDOM(bds, element_name=element_name)
        if root_only:
            dom = dom.documentElement
        return dom.toxml(encoding)

    def _toDOM_csc (self, dom_support, parent):
        assert parent is not None
        if self.__xsiNil:
            dom_support.addAttribute(parent, XSI.nil, 'true')
        return getattr(super(_TypeBinding_mixin, self), '_toDOM_csc', lambda *_args,**_kw: dom_support)(dom_support, parent)

    def _validateBinding_vx (self):
        """Override in subclasses for type-specific validation of instance
        content.

        @return: C{True} if the instance validates
        @raise pyxb.BatchContentValidationError: complex content does not match model
        @raise pyxb.SimpleTypeValueError: simple content fails to satisfy constraints
        """
        raise NotImplementedError('%s._validateBinding_vx' % (type(self).__name__,))

    def validateBinding (self):
        """Check whether the binding content matches its content model.

        @return: C{True} if validation succeeds.
        @raise pyxb.BatchContentValidationError: complex content does not match model
        @raise pyxb.SimpleTypeValueError: attribute or simple content fails to satisfy constraints
        """
        if self._performValidation():
            self._validateBinding_vx()
        return True

    def _finalizeContentModel (self):
        """Inform content model that all additions have been provided.

        This is used to resolve any pending non-determinism when the content
        of an element is provided through a DOM assignment or through
        positional arguments in a constructor."""
        return self

    def _postDOMValidate (self):
        self.validateBinding()
        return self

    @classmethod
    def _Name (cls):
        """Return the best descriptive name for the type of the instance.

        This is intended to be a human-readable value used in diagnostics, and
        is the expanded name if the type has one, or the Python type name if
        it does not."""
        if cls._ExpandedName is not None:
            return six.text_type(cls._ExpandedName)
        return six.text_type(cls)

    def _diagnosticName (self):
        """The best name available for this instance in diagnostics.

        If the instance is associated with an element, it is the element name;
        otherwise it is the best name for the type of the instance per L{_Name}."""
        if self.__element is None:
            return self._Name()
        return six.text_type(self.__element.name())

class _DynamicCreate_mixin (pyxb.cscRoot):
    """Helper to allow overriding the implementation class.

    Generally we'll want to augment the generated bindings by subclassing
    them, and adding functionality to the subclass.  This mix-in provides a
    way to communicate the existence of the superseding subclass back to the
    binding infrastructure, so that when it creates an instance it uses the
    subclass rather than the unaugmented binding class.

    When a raw generated binding is subclassed, L{_SetSupersedingClass} should be
    invoked on the raw class passing in the superseding subclass.  E.g.::

      class mywsdl (raw.wsdl):
        pass
      raw.wsdl._SetSupersedingClass(mywsdl)

    """

    @classmethod
    def __SupersedingClassAttribute (cls):
        return '_%s__SupersedingClass' % (cls.__name__,)

    @classmethod
    def __AlternativeConstructorAttribute (cls):
        return '_%s__AlternativeConstructor' % (cls.__name__,)

    @classmethod
    def _SupersedingClass (cls):
        """Return the class stored in the class reference attribute."""
        return getattr(cls, cls.__SupersedingClassAttribute(), cls)

    @classmethod
    def _AlternativeConstructor (cls):
        """Return the class stored in the class reference attribute."""
        rv = getattr(cls, cls.__AlternativeConstructorAttribute(), None)
        if isinstance(rv, tuple):
            rv = rv[0]
        return rv

    @classmethod
    def _SetSupersedingClass (cls, superseding):
        """Set the class reference attribute.

        @param superseding: A Python class that is a subclass of this class.
        """
        assert (superseding is None) or issubclass(superseding, cls)
        if superseding is None:
            cls.__dict__.pop(cls.__SupersedingClassAttribute(), None)
        else:
            setattr(cls, cls.__SupersedingClassAttribute(), superseding)
        return superseding

    @classmethod
    def _SetAlternativeConstructor (cls, alternative_constructor):
        attr = cls.__AlternativeConstructorAttribute()
        if alternative_constructor is None:
            cls.__dict__.pop(attr, None)
        else:
            # Need to use a tuple as the value: if you use an invokable, this
            # ends up converting it from a function to an unbound method,
            # which is not what we want.
            setattr(cls, attr, (alternative_constructor,))
        assert cls._AlternativeConstructor() == alternative_constructor
        return alternative_constructor

    @classmethod
    def _DynamicCreate (cls, *args, **kw):
        """Invoke the constructor for this class or the one that supersedes it."""
        ctor = cls._AlternativeConstructor()
        if ctor is None:
            ctor = cls._SupersedingClass()
        try:
            return ctor(*args, **kw)
        except TypeError:
            raise pyxb.SimpleTypeValueError(ctor, args)

class _RepresentAsXsdLiteral_mixin (pyxb.cscRoot):
    """Marker class for data types using XSD literal string as pythonLiteral.

    This is necessary for any simple data type where Python repr() produces a
    constructor call involving a class that may not be available by that name;
    e.g. duration, decimal, and any of the date/time types."""
    pass

class _NoNullaryNonNillableNew_mixin (pyxb.cscRoot):
    """Marker class indicating that a simple data type cannot construct
    a value from XML through an empty string.

    This class should appear immediately L{simpleTypeDefinition} (or whatever
    inherits from L{simpleTypeDefinition} in cases where it applies."""
    pass

class simpleTypeDefinition (_TypeBinding_mixin, utility._DeconflictSymbols_mixin, _DynamicCreate_mixin):
    """L{simpleTypeDefinition} is a base class that is part of the
    hierarchy of any class that represents the Python datatype for a
    L{SimpleTypeDefinition<pyxb.xmlschema.structures.SimpleTypeDefinition>}.

    @note: This class, or a descendent of it, must be the first class
    in the method resolution order when a subclass has multiple
    parents.  Otherwise, constructor keyword arguments may not be
    removed before passing them on to Python classes that do not
    accept them.
    """

    # A map from leaf classes in the facets module to instance of
    # those classes that constrain or otherwise affect the datatype.
    # Note that each descendent of simpleTypeDefinition has its own map.
    __FacetMap = {}

    _ReservedSymbols = _TypeBinding_mixin._ReservedSymbols.union(set([ 'XsdLiteral', 'xsdLiteral',
                            'XsdSuperType', 'XsdPythonType', 'XsdConstraintsOK',
                            'xsdConstraintsOK', 'XsdValueLength', 'xsdValueLength',
                            'PythonLiteral', 'pythonLiteral',
                            'SimpleTypeDefinition' ]))
    """Symbols that remain the responsibility of this class.  Any
    public symbols in generated binding subclasses are deconflicted
    by providing an alternative name in the subclass.  (There
    currently are no public symbols in generated SimpleTypeDefinion
    bindings."""


    # Determine the name of the class-private facet map.  For the base class
    # this should produce the same attribute name as Python's privatization
    # scheme.
    __FacetMapAttributeNameMap = { }
    @classmethod
    def __FacetMapAttributeName (cls):
        """ """
        '''
        if cls == simpleTypeDefinition:
            return '_%s__FacetMap' % (cls.__name__.strip('_'),)

        # It is not uncommon for a class in one namespace to extend a class of
        # the same name in a different namespace, so encode the namespace URI
        # in the attribute name (if it is part of a namespace).
        ns_uri = ''
        try:
            ns_uri = cls._ExpandedName.namespaceURI()
        except Exception:
            pass
        nm = '_' + utility.MakeIdentifier('%s_%s_FacetMap' % (ns_uri, cls.__name__.strip('_')))
        '''
        nm = cls.__FacetMapAttributeNameMap.get(cls)
        if nm is None:
            nm = cls.__name__
            if nm.endswith('_'):
                nm += '1'
            if cls == simpleTypeDefinition:
                nm = '_%s__FacetMap' % (nm,)
            else:
                # It is not uncommon for a class in one namespace to extend a class of
                # the same name in a different namespace, so encode the namespace URI
                # in the attribute name (if it is part of a namespace).
                ns_uri = ''
                try:
                    ns_uri = cls._ExpandedName.namespaceURI()
                except Exception:
                    pass
                nm = '_' + utility.MakeIdentifier('%s_%s_FacetMap' % (ns_uri, nm))
            cls.__FacetMapAttributeNameMap[cls] = nm
        return nm

    @classmethod
    def _FacetMap (cls):
        """Return a reference to the facet map for this datatype.

        The facet map is a map from leaf facet classes to instances of those
        classes that constrain or otherwise apply to the lexical or value
        space of the datatype.  Classes may inherit their facet map from their
        superclass, or may create a new class instance if the class adds a new
        constraint type.

        @raise AttributeError: if the facet map has not been defined"""
        return getattr(cls, cls.__FacetMapAttributeName())

    @classmethod
    def _InitializeFacetMap (cls, *args):
        """Initialize the facet map for this datatype.

        This must be called exactly once, after all facets belonging to the
        datatype have been created.

        @raise pyxb.LogicError: if called multiple times (on the same class)
        @raise pyxb.LogicError: if called when a parent class facet map has not been initialized
        :return: the facet map"""
        fm = None
        try:
            fm = cls._FacetMap()
        except AttributeError:
            pass
        if fm is not None:
            raise pyxb.LogicError('%s facet map initialized multiple times: %s' % (cls.__name__, cls.__FacetMapAttributeName()))

        # Search up the type hierarchy to find the nearest ancestor that has a
        # facet map.  This gets a bit tricky: if we hit the ceiling early
        # because the PSTD hierarchy re-based itself on a new Python type, we
        # have to jump to the XsdSuperType.
        source_class = cls
        while fm is None:
            # Assume we're staying in this hierarchy.  Include source_class in
            # the candidates, since we might have jumped to it.
            for super_class in source_class.mro():
                assert super_class is not None
                if (super_class == simpleTypeDefinition): # and (source_class.XsdSuperType() is not None):
                    break
                if issubclass(super_class, simpleTypeDefinition):
                    try:
                        fm = super_class._FacetMap()
                        break
                    except AttributeError:
                        pass
            if fm is None:
                try:
                    source_class = source_class.XsdSuperType()
                except AttributeError:
                    source_class = None
                if source_class is None:
                    fm = { }
        if fm is None:
            raise pyxb.LogicError('%s is not a child of simpleTypeDefinition' % (cls.__name__,))
        fm = fm.copy()
        for facet in args:
            fm[type(facet)] = facet
        setattr(cls, cls.__FacetMapAttributeName(), fm)
        return fm

    @classmethod
    def _ConvertArguments_vx (cls, args, kw):
        return args

    @classmethod
    def _ConvertArguments (cls, args, kw):
        """Pre-process the arguments.

        This is used before invoking the parent constructor.  One application
        is to apply the whitespace facet processing; if such a request is in
        the keywords, it is removed so it does not propagate to the
        superclass.  Another application is to convert the arguments from a
        string to a list.  Binding-specific applications are performed in the
        overloaded L{_ConvertArguments_vx} method."""
        dom_node = kw.pop('_dom_node', None)
        from_xml = kw.get('_from_xml', dom_node is not None)
        if dom_node is not None:
            text_content = domutils.ExtractTextContent(dom_node)
            if text_content is not None:
                args = (domutils.ExtractTextContent(dom_node),) + args
                kw['_apply_whitespace_facet'] = True
        apply_whitespace_facet = kw.pop('_apply_whitespace_facet', from_xml)
        if (0 < len(args)) and isinstance(args[0], six.string_types) and apply_whitespace_facet:
            cf_whitespace = getattr(cls, '_CF_whiteSpace', None)
            if cf_whitespace is not None:
                norm_str = six.text_type(cf_whitespace.normalizeString(args[0]))
                args = (norm_str,) + args[1:]
        kw['_from_xml'] = from_xml
        return cls._ConvertArguments_vx(args, kw)

    # Must override new, because new gets invoked before init, and usually
    # doesn't accept keywords.  In case it does (e.g., datetime.datetime),
    # only remove the ones that would normally be interpreted by this class.
    # Do the same argument conversion as is done in init.  Trap errors and
    # convert them to BadTypeValue errors.
    #
    # Note: We explicitly do not validate constraints here.  That's
    # done in the normal constructor; here, we might be in the process
    # of building a value that eventually will be legal, but isn't
    # yet.
    def __new__ (cls, *args, **kw):
        # PyXBFactoryKeywords
        kw.pop('_validate_constraints', None)
        kw.pop('_require_value', None)
        kw.pop('_element', None)
        kw.pop('_fallback_namespace', None)
        kw.pop('_apply_attributes', None)
        is_nil = kw.pop('_nil', None)
        # ConvertArguments will remove _dom_node, _element, and
        # _apply_whitespace_facet, and it will set _from_xml.
        args = cls._ConvertArguments(args, kw)
        from_xml = kw.pop('_from_xml', False)
        if ((0 == len(args))
            and from_xml
            and not is_nil
            and issubclass(cls, _NoNullaryNonNillableNew_mixin)):
            raise pyxb.SimpleTypeValueError(cls, args);
        kw.pop('_location', None)
        assert issubclass(cls, _TypeBinding_mixin)
        try:
            parent = super(simpleTypeDefinition, cls)
            if parent.__new__ is object.__new__:
                return parent.__new__(cls)
            return parent.__new__(cls, *args, **kw)
        except ValueError:
            raise pyxb.SimpleTypeValueError(cls, args)
        except OverflowError:
            raise pyxb.SimpleTypeValueError(cls, args)

    # Validate the constraints after invoking the parent constructor,
    # unless told not to.
    def __init__ (self, *args, **kw):
        """Initialize a newly created STD instance.

        Usually there is one positional argument, which is a value that can be
        converted to the underlying Python type.

        @keyword _validate_constraints: If True (default if validation is
        enabled), the newly constructed value is checked against its
        constraining facets.
        @type _validate_constraints: C{bool}

        @keyword _apply_attributes: If C{True} (default), any attributes
        present in the keywords or DOM node are applied.  Normally presence of
        such an attribute should produce an error; when creating simple
        content for a complex type we need the DOM node, but do not want to
        apply the attributes, so we bypass the application.
        """
        # PyXBFactoryKeywords
        validate_constraints = kw.pop('_validate_constraints', self._validationConfig.forBinding)
        require_value = kw.pop('_require_value', False)
        # Save DOM node so we can pull attributes off it
        dom_node = kw.get('_dom_node')
        location = kw.get('_location')
        if (location is None) and isinstance(dom_node, utility.Locatable_mixin):
            location = dom_node._location()
        apply_attributes = kw.pop('_apply_attributes', True)
        # _ConvertArguments handles _dom_node and _apply_whitespace_facet
        # TypeBinding_mixin handles _nil and _element
        args = self._ConvertArguments(args, kw)
        try:
            super(simpleTypeDefinition, self).__init__(*args, **kw)
        except OverflowError:
            raise pyxb.SimpleTypeValueError(type(self), args)
        if apply_attributes and (dom_node is not None):
            self._setAttributesFromKeywordsAndDOM(kw, dom_node)
        if require_value and (not self._constructedWithValue()):
            if location is None:
                location = self._location()
            raise pyxb.SimpleContentAbsentError(self, location)
        if validate_constraints and not kw.pop('_nil', False):
            self.xsdConstraintsOK(location)

    # The class attribute name used to store the reference to the STD
    # component instance must be unique to the class, not to this base class.
    # Otherwise we mistakenly believe we've already associated a STD instance
    # with a class (e.g., xsd:normalizedString) when in fact it's associated
    # with the superclass (e.g., xsd:string)
    @classmethod
    def __STDAttrName (cls):
        return '_%s__SimpleTypeDefinition' % (cls.__name__,)

    @classmethod
    def _SimpleTypeDefinition (cls, std):
        """Set the L{pyxb.xmlschema.structures.SimpleTypeDefinition} instance
        associated with this binding."""
        attr_name = cls.__STDAttrName()
        if hasattr(cls, attr_name):
            old_value = getattr(cls, attr_name)
            if old_value != std:
                raise pyxb.LogicError('%s: Attempt to override existing STD %s with %s' % (cls, old_value.name(), std.name()))
        setattr(cls, attr_name, std)

    @classmethod
    def SimpleTypeDefinition (cls):
        """Return the SimpleTypeDefinition instance for the given
        class.

        This should only be invoked when generating bindings.  An STD must
        have been associated with the class using L{_SimpleTypeDefinition}."""
        attr_name = cls.__STDAttrName()
        assert hasattr(cls, attr_name)
        return getattr(cls, attr_name)

    @classmethod
    def XsdLiteral (cls, value):
        """Convert from a python value to a string usable in an XML
        document.

        This should be implemented in the subclass."""
        raise pyxb.LogicError('%s does not implement XsdLiteral' % (cls,))

    def xsdLiteral (self):
        """Return text suitable for representing the value of this
        instance in an XML document.

        The base class implementation delegates to the object class's
        XsdLiteral method."""
        if self._isNil():
            return ''
        return self.XsdLiteral(self)

    @classmethod
    def XsdSuperType (cls):
        """Find the nearest parent class in the PST hierarchy.

        The value for anySimpleType is None; for all others, it's a
        primitive or derived PST descendent (including anySimpleType)."""
        for sc in cls.mro():
            if sc == cls:
                continue
            if simpleTypeDefinition == sc:
                # If we hit the PST base, this is a primitive type or
                # otherwise directly descends from a Python type; return
                # the recorded XSD supertype.
                return cls._XsdBaseType
            if issubclass(sc, simpleTypeDefinition):
                return sc
        raise pyxb.LogicError('No supertype found for %s' % (cls,))

    @classmethod
    def _XsdConstraintsPreCheck_vb (cls, value):
        """Pre-extended class method to verify other things before
        checking constraints.

        This is used for list types, to verify that the values in the
        list are acceptable, and for token descendents, to check the
        lexical/value space conformance of the input.
        """
        super_fn = getattr(super(simpleTypeDefinition, cls), '_XsdConstraintsPreCheck_vb', lambda *a,**kw: value)
        return super_fn(value)

    # Cache of pre-computed sequences of class facets in the order required
    # for constraint validation
    __ClassFacetSequence = { }

    @classmethod
    def XsdConstraintsOK (cls, value, location=None):
        """Validate the given value against the constraints on this class.

        @raise pyxb.SimpleTypeValueError: if any constraint is violated.
        """

        value = cls._XsdConstraintsPreCheck_vb(value)

        facet_values = cls.__ClassFacetSequence.get(cls)
        if facet_values is None:
            # Constraints for simple type definitions are inherited.  Check them
            # from least derived to most derived.
            classes = [ _x for _x in cls.mro() if issubclass(_x, simpleTypeDefinition) ]
            classes.reverse()
            cache_result = True
            facet_values = []
            for clazz in classes:
                # When setting up the datatypes, if we attempt to validate
                # something before the facets have been initialized (e.g., a
                # nonNegativeInteger used as a length facet for the parent
                # integer datatype), just ignore that for now.  Don't cache
                # the value, though, since a subsequent check after
                # initialization should succceed.
                try:
                    clazz_facets = list(six.itervalues(clazz._FacetMap()))
                except AttributeError:
                    cache_result = False
                    clazz_facets = []
                for v in clazz_facets:
                    if not (v in facet_values):
                        facet_values.append(v)
            if cache_result:
                cls.__ClassFacetSequence[cls] = facet_values
        for f in facet_values:
            if not f.validateConstraint(value):
                raise pyxb.SimpleFacetValueError(cls, value, f, location)
        return value

    def xsdConstraintsOK (self, location=None):
        """Validate the value of this instance against its constraints."""
        return self.XsdConstraintsOK(self, location)

    def _validateBinding_vx (self):
        if not self._isNil():
            self._checkValidValue()
        return True

    @classmethod
    def XsdValueLength (cls, value):
        """Return the length of the given value.

        The length is calculated by a subclass implementation of
        _XsdValueLength_vx in accordance with
        http://www.w3.org/TR/xmlschema-2/#rf-length.

        The return value is a non-negative integer, or C{None} if length
        constraints should be considered trivially satisfied (as with
        QName and NOTATION).

        @raise pyxb.LogicError: the provided value is not an instance of cls.
        @raise pyxb.LogicError: an attempt is made to calculate a length for
        an instance of a type that does not support length calculations.
        """
        assert isinstance(value, cls)
        if not hasattr(cls, '_XsdValueLength_vx'):
            raise pyxb.LogicError('Class %s does not support length validation' % (cls.__name__,))
        return cls._XsdValueLength_vx(value)

    def xsdValueLength (self):
        """Return the length of this instance within its value space.

        See XsdValueLength."""
        return self.XsdValueLength(self)

    @classmethod
    def PythonLiteral (cls, value):
        """Return a string which can be embedded into Python source to
        represent the given value as an instance of this class."""
        class_name = cls.__name__
        if issubclass(cls, _RepresentAsXsdLiteral_mixin):
            value = value.xsdLiteral()
        return '%s(%s)' % (class_name, pyxb.utils.utility.repr2to3(value))

    def pythonLiteral (self):
        """Return a string which can be embedded into Python source to
        represent the value of this instance."""
        return self.PythonLiteral(self)

    def _toDOM_csc (self, dom_support, parent):
        assert parent is not None
        dom_support.appendTextChild(self, parent)
        return getattr(super(simpleTypeDefinition, self), '_toDOM_csc', lambda *_args,**_kw: dom_support)(dom_support, parent)

    @classmethod
    def _IsSimpleTypeContent (cls):
        """STDs have simple type content."""
        return True

    @classmethod
    def _IsValidValue (self, value):
        try:
            self._CheckValidValue(value)
            return True
        except pyxb.PyXBException:
            pass
        return False

    @classmethod
    def _CheckValidValue (cls, value):

        """NB: Invoking this on a value that is a list will, if necessary,
        replace the members of the list with new values that are of the
        correct item type.  This is permitted because only with lists is it
        possible to bypass the normal content validation (by invoking
        append/extend on the list instance)."""
        if value is None:
            raise pyxb.SimpleTypeValueError(cls, value)
        value_class = cls
        if issubclass(cls, STD_list):
            if not isinstance(value, Iterable):
                raise pyxb.SimpleTypeValueError(cls, value)
            for v in value:
                if not cls._ItemType._IsValidValue(v):
                    raise pyxb.SimpleListValueError(cls, v)
        else:
            if issubclass(cls, STD_union):
                value_class = None
                for mt in cls._MemberTypes:
                    if mt._IsValidValue(value):
                        value_class = mt
                        break
                if value_class is None:
                    raise pyxb.SimpleUnionValueError(cls, value)
            #if not (isinstance(value, value_class) or issubclass(value_class, type(value))):
            if not isinstance(value, value_class):
                raise pyxb.SimpleTypeValueError(cls, value)
        value_class.XsdConstraintsOK(value)

    def _checkValidValue (self):
        self._CheckValidValue(self)

    def _isValidValue (self):
        self._IsValidValue(self)

    def _setAttribute (self, attr_en, value_lex):
        # Simple types have no attributes, but the parsing infrastructure
        # might invoke this to delegate responsibility for notifying the user
        # of the failure.
        raise pyxb.AttributeOnSimpleTypeError(self, attr_en, value_lex)

    @classmethod
    def _description (cls, name_only=False, user_documentation=True):
        name = cls._Name()
        if name_only:
            return name
        desc = [ name, ' restriction of ', cls.XsdSuperType()._description(name_only=True) ]
        if user_documentation and (cls._Documentation is not None):
            desc.extend(["\n", cls._Documentation])
        return ''.join(desc)

class STD_union (simpleTypeDefinition):
    """Base class for union datatypes.

    This class descends only from simpleTypeDefinition.  A pyxb.LogicError is
    raised if an attempt is made to construct an instance of a subclass of
    STD_union.  Values consistent with the member types are constructed using
    the Factory class method.  Values are validated using the _ValidatedMember
    class method.

    Subclasses must provide a class variable _MemberTypes which is a
    tuple of legal members of the union."""

    _MemberTypes = None
    """A list of classes which are permitted as values of the union."""

    # Ick: If we don't declare this here, this class's map doesn't get
    # initialized.  Alternative is to not descend from simpleTypeDefinition.
    # @todo Ensure that pattern and enumeration are valid constraints
    __FacetMap = {}

    @classmethod
    def Factory (cls, *args, **kw):
        """Given a value, attempt to create an instance of some member of this
        union.  The first instance which can be legally created is returned.

        @keyword _validate_constraints: If C{True} (default if validation is
        enabled), any constructed value is checked against constraints applied
        to the union as well as the member type.

        @raise pyxb.SimpleTypeValueError: no member type will permit creation of
        an instance from the parameters in C{args} and C{kw}.
        """

        used_cls = cls._SupersedingClass()
        state = used_cls._PreFactory_vx(args, kw)

        rv = None
        # NB: get, not pop: preserve it for the member type invocations
        validate_constraints = kw.get('_validate_constraints', cls._GetValidationConfig().forBinding)
        assert isinstance(validate_constraints, bool)
        if 0 < len(args):
            arg = args[0]
            try:
                rv = cls._ValidatedMember(arg)
            except pyxb.SimpleTypeValueError:
                pass
        if rv is None:
            kw['_validate_constraints'] = True
            for mt in cls._MemberTypes:
                try:
                    rv = mt.Factory(*args, **kw)
                    break
                except pyxb.SimpleTypeValueError:
                    pass
                except (ValueError, OverflowError):
                    pass
                except:
                    pass
        location = None
        if kw is not None:
            location = kw.get('_location')
        if rv is not None:
            if validate_constraints:
                cls.XsdConstraintsOK(rv, location)
            rv._postFactory_vx(state)
            return rv
        # The constructor may take any number of arguments, so pass the whole thing.
        # Should we also provide the keywords?
        raise pyxb.SimpleUnionValueError(cls, args, location)

    @classmethod
    def _ValidatedMember (cls, value):
        """Validate the given value as a potential union member.

        @raise pyxb.SimpleTypeValueError: the value is not an instance of a
        member type."""
        if not isinstance(value, cls._MemberTypes):
            for mt in cls._MemberTypes:
                try:
                    # Force validation so we get the correct type, otherwise
                    # first member will be accepted.
                    value = mt.Factory(value, _validate_constraints=True)
                    return value
                except (TypeError, pyxb.SimpleTypeValueError):
                    pass
            raise pyxb.SimpleUnionValueError(cls, value)
        return value

    def __new__ (self, *args, **kw):
        raise pyxb.LogicError('%s: cannot construct instances of union' % (self.__class__.__name__,))

    def __init__ (self, *args, **kw):
        raise pyxb.LogicError('%s: cannot construct instances of union' % (self.__class__.__name__,))

    @classmethod
    def _description (cls, name_only=False, user_documentation=True):
        name = cls._Name()
        if name_only:
            return name
        desc = [ name, ', union of ']
        desc.append(', '.join([ _td._description(name_only=True) for _td in cls._MemberTypes ]))
        return ''.join(desc)

    @classmethod
    def XsdLiteral (cls, value):
        """Convert from a binding value to a string usable in an XML document."""
        return cls._ValidatedMember(value).xsdLiteral()


class STD_list (simpleTypeDefinition, six.list_type):
    """Base class for collection datatypes.

    This class descends from the Python list type, and incorporates
    simpleTypeDefinition.  Subclasses must define a class variable _ItemType
    which is a reference to the class of which members must be instances."""

    _ItemType = None
    """A reference to the binding class for items within this list."""

    # Ick: If we don't declare this here, this class's map doesn't get
    # initialized.  Alternative is to not descend from simpleTypeDefinition.
    __FacetMap = {}

    @classmethod
    def _ValidatedItem (cls, value, kw=None):
        """Verify that the given value is permitted as an item of this list.

        This may convert the value to the proper type, if it is
        compatible but not an instance of the item type.  Returns the
        value that should be used as the item, or raises an exception
        if the value cannot be converted.

        @param kw: optional dictionary of standard constructor keywords used
        when exceptions must be built.  In particular, C{_location} may be
        useful.
        """
        if isinstance(value, cls._ItemType):
            pass
        elif issubclass(cls._ItemType, STD_union):
            value = cls._ItemType._ValidatedMember(value)
        else:
            try:
                value = cls._ItemType(value)
            except (pyxb.SimpleTypeValueError, TypeError):
                location = None
                if kw is not None:
                    location = kw.get('_location')
                raise pyxb.SimpleListValueError(cls, value, location)
        return value

    @classmethod
    def _ConvertArguments_vx (cls, args, kw):
        # If the first argument is a string, split it on spaces and use the
        # resulting list of tokens.
        if 0 < len(args):
            arg1 = args[0]
            if isinstance(arg1, six.string_types):
                args = (arg1.split(),) + args[1:]
                arg1 = args[0]
            if isinstance(arg1,Iterable):
                new_arg1 = [ cls._ValidatedItem(_v, kw) for _v in arg1 ]
                args = (new_arg1,) + args[1:]
        super_fn = getattr(super(STD_list, cls), '_ConvertArguments_vx', lambda *a,**kw: args)
        return super_fn(args, kw)

    @classmethod
    def _XsdValueLength_vx (cls, value):
        return len(value)

    @classmethod
    def XsdLiteral (cls, value):
        """Convert from a binding value to a string usable in an XML document."""
        return ' '.join([ cls._ItemType.XsdLiteral(_v) for _v in value ])

    @classmethod
    def _description (cls, name_only=False, user_documentation=True):
        name = cls._Name()
        if name_only:
            return name
        desc = [ name, ', list of ', cls._ItemType._description(name_only=True) ]
        return ''.join(desc)

    # Convert a single value to the required type, if not already an instance
    @classmethod
    def __ConvertOne (cls, v):
        return cls._ValidatedItem(v)

    # Convert a sequence of values to the required type, if not already instances
    def __convertMany (self, values):
        return [ self._ValidatedItem(_v) for _v in values ]

    def __setitem__ (self, key, value):
        if isinstance(key, slice):
            super(STD_list, self).__setitem__(key, self.__convertMany(value))
        else:
            super(STD_list, self).__setitem__(key, self._ValidatedItem(value))

    if six.PY2:
        def __setslice__ (self, start, end, values):
            super(STD_list, self).__setslice__(start, end, self.__convertMany(values))

    def __contains__ (self, item):
        return super(STD_list, self).__contains__(self._ValidatedItem(item))

    # Standard mutable sequence methods, per Python Library Reference "Mutable Sequence Types"

    def append (self, x):
        super(STD_list, self).append(self._ValidatedItem(x))

    def extend (self, x, _from_xml=False):
        super(STD_list, self).extend(self.__convertMany(x))

    def count (self, x):
        return super(STD_list, self).count(self._ValidatedItem(x))

    def index (self, x, *args):
        return super(STD_list, self).index(self._ValidatedItem(x), *args)

    def insert (self, i, x):
        super(STD_list, self).insert(i, self._ValidatedItem(x))

    def remove (self, x):
        super(STD_list, self).remove(self._ValidatedItem(x))

class element (utility._DeconflictSymbols_mixin, _DynamicCreate_mixin):
    """Class that represents a schema element within a binding.

    This gets a little confusing.  Within a schema, the
    L{pyxb.xmlschema.structures.ElementDeclaration} type represents an
    U{element
    declaration<http://www.w3.org/TR/xmlschema-1/#cElement_Declarations>}.
    Those declarations may be global (have a name that is visible in the
    namespace), or local (have a name that is visible only within a complex
    type definition).  Further, local (but not global) declarations may have a
    reference to a global declaration (which might be in a different
    namespace).

    Within a PyXB binding, the element declarations from the original complex
    type definition that have the same
    U{QName<http://www.w3.org/TR/1999/REC-xml-names-19990114/#dt-qname>}
    (after deconflicting the
    U{LocalPart<http://www.w3.org/TR/1999/REC-xml-names-19990114/#NT-LocalPart>})
    are associated with an attribute in the class for the complex type.  Each
    of these attributes is defined via a
    L{pyxb.binding.content.ElementDeclaration} which provides the mechanism by
    which the binding holds values associated with that element.

    Furthermore, in the FAC-based content model each schema element
    declaration is associated with an
    L{ElementUse<pyxb.binding.content.ElementUse>} instance to locate the
    point in the schema where content came from.  Instances that refer to the
    same schema element declaration share the same underlying
    L{pyxb.binding.content.ElementDeclaration}.

    This element isn't any of those elements.  This element is the type used
    for an attribute which associates the name of a element with data required
    to represent it, all within a particular scope (a module for global scope,
    the binding class for a complex type definition for local scope).  From
    the perspective of a PyXB user they look almost like a class, in that you
    can call them to create instances of the underlying complex type.

    Global and local elements are represented by instances of this class.
    """

    def name (self):
        """The expanded name of the element within its scope."""
        return self.__name
    __name = None

    def typeDefinition (self):
        """The L{_TypeBinding_mixin} subclass for values of this element."""
        return self.__typeDefinition._SupersedingClass()
    __typeDefinition = None

    def xsdLocation (self):
        """The L{pyxb.utils.utility.Location} where the element appears in the schema."""
        return self.__xsdLocation
    __xsdLocation = None

    def scope (self):
        """The scope of the element.  This is either C{None}, representing a
        top-level element, or an instance of C{complexTypeDefinition} for
        local elements."""
        return self.__scope
    __scope = None

    def nillable (self):
        """Indicate whether values matching this element can have U{nil
        <http://www.w3.org/TR/xmlschema-1/#xsi_nil>} set."""
        return self.__nillable
    __nillable = False

    def abstract (self):
        """Indicate whether this element is abstract (must use substitution
        group members for matches)."""
        return self.__abstract
    __abstract = False

    def documentation (self):
        """Contents of any documentation annotation in the definition."""
        return self.__documentation
    __documentation = None

    def defaultValue (self):
        """The default value of the element.

        C{None} if the element has no default value.

        @note: A non-C{None} value is always an instance of a simple type,
        even if the element has complex content."""
        return self.__defaultValue
    __defaultValue = None

    def fixed (self):
        """C{True} if the element content cannot be changed"""
        return self.__fixed
    __fixed = False

    def substitutionGroup (self):
        """The L{element} instance to whose substitution group this element
        belongs.  C{None} if this element is not part of a substitution
        group."""
        return self.__substitutionGroup
    def _setSubstitutionGroup (self, substitution_group):
        self.__substitutionGroup = substitution_group
        if substitution_group is not None:
            self.substitutesFor = self._real_substitutesFor
        return self
    __substitutionGroup = None

    def findSubstituendDecl (self, ctd_class):
        ed = ctd_class._ElementMap.get(self.name())
        if ed is not None:
            return ed
        if self.substitutionGroup() is None:
            return None
        return self.substitutionGroup().findSubstituendDecl(ctd_class)

    def _real_substitutesFor (self, other):
        """Determine whether an instance of this element can substitute for the other element.

        See U{Substitution Group OK<http://www.w3.org/TR/xmlschema-1/#cos-equiv-derived-ok-rec>}.

        @todo: Do something about blocking constraints.  This ignores them, as
        does everything leading to this point.
        """
        if self.substitutionGroup() is None:
            return False
        if other is None:
            return False
        assert isinstance(other, element)
        # On the first call, other is likely to be the local element.  We need
        # the global one.
        if other.scope() is not None:
            other = other.name().elementBinding()
            if other is None:
                return False
            assert other.scope() is None
        # Do both these refer to the same (top-level) element?
        if self.name().elementBinding() == other:
            return True
        return (self.substitutionGroup() == other) or self.substitutionGroup().substitutesFor(other)

    def substitutesFor (self, other):
        """Stub replaced by _real_substitutesFor when element supports substitution groups."""
        return False

    def memberElement (self, name):
        """Return a reference to the element instance used for the given name
        within this element.

        The type for this element must be a complex type definition."""
        return self.typeDefinition()._UseForTag(name).elementBinding()

    def __init__ (self, name, type_definition, scope=None, nillable=False, abstract=False, unicode_default=None, fixed=False, substitution_group=None, documentation=None, location=None):
        """Create a new element binding.
        """
        assert isinstance(name, pyxb.namespace.ExpandedName)
        self.__name = name
        self.__typeDefinition = type_definition
        self.__scope = scope
        self.__nillable = nillable
        self.__abstract = abstract
        if unicode_default is not None:
            # Override default None.  If this is a complex type with simple
            # content, use the underlying simple type value.
            self.__defaultValue = self.__typeDefinition.Factory(unicode_default, _from_xml=True)
            if isinstance(self.__defaultValue, complexTypeDefinition):
                self.__defaultValue = self.__defaultValue.value()
        self.__fixed = fixed
        self.__substitutionGroup = substitution_group
        self.__documentation = documentation
        self.__xsdLocation = location
        super(element, self).__init__()

    def __call__ (self, *args, **kw):
        """Invoke the Factory method on the type associated with this element.

        @keyword _dom_node: This keyword is removed.  If present, it must be C{None}.

        @note: Other keywords are passed to L{_TypeBinding_mixin.Factory}.

        @raise pyxb.AbstractElementError: This element is abstract and no DOM
        node was provided.
        """
        dom_node = kw.pop('_dom_node', None)
        assert dom_node is None, 'Cannot pass DOM node directly to element constructor; use createFromDOM'
        if '_element' in kw:
            raise pyxb.LogicError('Cannot set _element in element-based instance creation')
        kw['_element'] = self
        # Can't create instances of abstract elements.
        if self.abstract():
            location = kw.get('_location')
            if (location is None) and isinstance(dom_node, utility.Locatable_mixin):
                location = dom_node._location()
            raise pyxb.AbstractElementError(self, location, args)
        if self.__defaultValue is not None:
            if 0 == len(args):
                # No initial value; use the default
                args = [ self.__defaultValue ]
            elif self.__fixed:
                # Validate that the value is consistent with the fixed value
                if 1 < len(args):
                    raise ValueError(*args)
                args = [ self.compatibleValue(args[0], **kw) ]
        rv = self.typeDefinition().Factory(*args, **kw)
        rv._setElement(self)
        return rv

    def compatibleValue (self, value, **kw):
        """Return a variant of the value that is compatible with this element.

        This mostly defers to L{_TypeBinding_mixin._CompatibleValue}.

        @raise pyxb.SimpleTypeValueError: if the value is not both
        type-consistent and value-consistent with the element's type.
        """
        # None is always None, unless there's a default.
        if value is None:
            return self.__defaultValue
        is_plural = kw.pop('is_plural', False)
        if is_plural:
            if not isinstance(value, Iterable):
                raise pyxb.SimplePluralValueError(self.typeDefinition(), value)
            return [ self.compatibleValue(_v) for _v in value ]
        compValue = self.typeDefinition()._CompatibleValue(value, **kw);
        if self.__fixed and (compValue != self.__defaultValue):
            raise pyxb.ElementChangeError(self, value)
        if isinstance(value, _TypeBinding_mixin) and (value._element() is not None) and value._element().substitutesFor(self):
            return value
        if self.abstract():
            location = None
            if isinstance(value, utility.Locatable_mixin):
                location = value._location()
            raise pyxb.AbstractElementError(self, location, value)
        return compValue

    @classmethod
    def CreateDOMBinding (cls, node, element_binding, **kw):
        """Create a binding from a DOM node.

        @param node: The DOM node

        @param element_binding: An instance of L{element} that would normally
        be used to determine the type of the binding.  The actual type of
        object returned is determined by the type definition associated with
        the C{element_binding} and the value of any U{xsi:type
        <http://www.w3.org/TR/xmlschema-1/#xsi_type>} attribute found in
        C{node}, modulated by
        L{XSI._InterpretTypeAttribute<pyxb.namespace.builtin._XMLSchema_instance._InterpretTypeAttribute>}.

        @keyword _fallback_namespace: The namespace to use as the namespace for
        the node, if the node name is unqualified.  This should be an absent
        namespace.

        @return: A binding for the DOM node.

        @raises pyxb.UnrecognizedDOMRootNodeError: if no underlying element or
        type for the node can be identified.
        """

        if xml.dom.Node.ELEMENT_NODE != node.nodeType:
            raise ValueError('node is not an element')

        fallback_namespace = kw.get('_fallback_namespace')

        # Record the element to be associated with the created binding
        # instance.
        if '_element' in kw:
            raise pyxb.LogicError('Cannot set _element in element-based instance creation')

        type_class = None
        if element_binding is not None:
            # Can't create instances of abstract elements.  @todo: Is there any
            # way this could be legal given an xsi:type attribute?  I'm pretty
            # sure "no"...
            if element_binding.abstract():
                location = kw.get('location')
                if (location is None) and isinstance(node, utility.Locatable_mixin):
                    location = node._location()
                raise pyxb.AbstractElementError(element_binding, location, node)
            kw['_element'] = element_binding
            type_class = element_binding.typeDefinition()

        # Get the namespace context for the value being created.  If none is
        # associated, one will be created.  Do not make assumptions about the
        # namespace context; if the user cared, she should have assigned a
        # context before calling this.
        ns_ctx = pyxb.namespace.NamespaceContext.GetNodeContext(node)
        (did_replace, type_class) = XSI._InterpretTypeAttribute(XSI.type.getAttribute(node), ns_ctx, fallback_namespace, type_class)

        if type_class is None:
            raise pyxb.UnrecognizedDOMRootNodeError(node)

        # Pass xsi:nil on to the constructor regardless of whether the element
        # is nillable.  Another sop to SOAP-encoding WSDL fans who don't
        # bother to provide valid schema for their message content.
        is_nil = XSI.nil.getAttribute(node)
        if is_nil is not None:
            kw['_nil'] = pyxb.binding.datatypes.boolean(is_nil)

        try:
            pyxb.namespace.NamespaceContext.PushContext(ns_ctx)
            rv = type_class.Factory(_dom_node=node, **kw)
        finally:
            pyxb.namespace.NamespaceContext.PopContext()
        assert rv._element() == element_binding
        rv._setNamespaceContext(pyxb.namespace.NamespaceContext.GetNodeContext(node))
        return rv._postDOMValidate()

    # element
    @classmethod
    def AnyCreateFromDOM (cls, node, fallback_namespace):
        """Create an instance of an element from a DOM node.

        This method does minimal processing of C{node} and delegates to
        L{CreateDOMBinding}.

        @param node: An C{xml.dom.Node} representing a root element.  If the
        node is a document, that document's root node will be substituted.
        The name of the node is extracted as the name of the element to be
        created, and the node and the name are passed to L{CreateDOMBinding}.

        @param fallback_namespace: The value to pass as C{_fallback_namespace}
        to L{CreateDOMBinding}

        @return: As with L{CreateDOMBinding}"""
        if xml.dom.Node.DOCUMENT_NODE == node.nodeType:
            node = node.documentElement
        expanded_name = pyxb.namespace.ExpandedName(node, fallback_namespace=fallback_namespace)
        return cls.CreateDOMBinding(node, expanded_name.elementBinding(), _fallback_namespace=fallback_namespace)

    def elementForName (self, name):
        """Return the element that should be used if this element binding is
        permitted and an element with the given name is encountered.

        Normally, the incoming name matches the name of this binding, and
        C{self} is returned.  If the incoming name is different, it is
        expected to be the name of a global element which is within this
        element's substitution group.  In that case, the binding corresponding
        to the named element is return.

        @return: An instance of L{element}, or C{None} if no element with the
        given name can be found.
        """

        # Name match means OK.
        if self.name() == name:
            return self
        # No name match means only hope is a substitution group, for which the
        # element must be top-level.
        top_elt = self.name().elementBinding()
        if top_elt is None:
            return None
        # Members of the substitution group must also be top-level.  NB: If
        # named_elt == top_elt, then the adoptName call below improperly
        # associated the global namespace with a local element of the same
        # name; cf. test-namespace-uu:testBad.
        elt_en = top_elt.name().adoptName(name)
        assert 'elementBinding' in elt_en.namespace()._categoryMap(), 'No element bindings in %s' % (elt_en.namespace(),)
        named_elt = elt_en.elementBinding()
        if (named_elt is None) or (named_elt == top_elt):
            return None
        if named_elt.substitutesFor(top_elt):
            return named_elt
        return None

    def createFromDOM (self, node, fallback_namespace=None, **kw):
        """Create an instance of this element using a DOM node as the source
        of its content.

        This method does minimal processing of C{node} and delegates to
        L{_createFromDOM}.

        @param node: An C{xml.dom.Node} representing a root element.  If the
        node is a document, that document's root node will be substituted.
        The name of the node is extracted as the name of the element to be
        created, and the node and the name are passed to L{_createFromDOM}

        @keyword fallback_namespace: Used as default for
        C{_fallback_namespace} in call to L{_createFromDOM}

        @note: Keyword parameters are passed to L{CreateDOMBinding}.

        @return: As with L{_createFromDOM}
        """
        if xml.dom.Node.DOCUMENT_NODE == node.nodeType:
            node = node.documentElement
        if fallback_namespace is not None:
            kw.setdefault('_fallback_namespace', fallback_namespace)
        expanded_name = pyxb.namespace.ExpandedName(node, fallback_namespace=fallback_namespace)
        return self._createFromDOM(node, expanded_name, **kw)

    def _createFromDOM (self, node, expanded_name, **kw):
        """Create an instance from a DOM node given the name of an element.

        This method does minimal processing of C{node} and C{expanded_name}
        and delegates to L{CreateDOMBinding}.

        @param node: An C{xml.dom.Node} representing a root element.  If the
        node is a document, that document's root node will be substituted.
        The value is passed to L{CreateDOMBinding}.

        @param expanded_name: The expanded name of the element to be used for
        content.  This is passed to L{elementForName} to obtain the binding
        that is passed to L{CreateDOMBinding}, superseding any identification
        that might be inferred from C{node}.  If no name is available, use
        L{createFromDOM}.

        @note: Keyword parameters are passed to L{CreateDOMBinding}.

        @return: As with L{CreateDOMBinding}.
        """
        if xml.dom.Node.DOCUMENT_NODE == node.nodeType:
            node = node.documentElement
        return element.CreateDOMBinding(node, self.elementForName(expanded_name), **kw)

    def __str__ (self):
        return 'Element %s' % (self.name(),)

    def _description (self, name_only=False, user_documentation=True):
        name = six.text_type(self.name())
        if name_only:
            return name
        desc = [ name, ' (', self.typeDefinition()._description(name_only=True), ')' ]
        if self.scope() is not None:
            desc.extend([', local to ', self.scope()._description(name_only=True) ])
        if self.nillable():
            desc.append(', nillable')
        if self.substitutionGroup() is not None:
            desc.extend([', substitutes for ', self.substitutionGroup()._description(name_only=True) ])
        if user_documentation and (self.documentation() is not None):
            desc.extend(["\n", self.documentation() ])
        return six.u('').join(desc)

class enumeration_mixin (pyxb.cscRoot):
    """Marker in case we need to know that a PST has an enumeration constraint facet."""

    _ReservedSymbols = set([ 'itervalues', 'values', 'iteritems', 'items' ])

    @classmethod
    def itervalues (cls):
        """Return a generator for the values that the enumeration can take."""
        return six.itervalues(cls._CF_enumeration)

    @classmethod
    def values (cls):
        """Return a list of values that the enumeration can take."""
        return list(cls.itervalues()) # nosix

    @classmethod
    def iteritems (cls):
        """Generate the associated L{pyxb.binding.facet._EnumerationElement} instances."""
        return six.iteritems(cls._CF_enumeration)

    @classmethod
    def items (cls):
        """Return the associated L{pyxb.binding.facet._EnumerationElement} instances."""
        return list(cls.iteritems()) # nosix

    @classmethod
    def _elementForValue (cls, value):
        """Return the L{_EnumerationElement} instance that has the given value.

        @raise KeyError: the value is not valid for the enumeration."""
        return cls._CF_enumeration.elementForValue(value)

    @classmethod
    def _valueForUnicode (cls, ustr):
        """Return the enumeration value corresponding to the given unicode string.

        If ustr is not a valid option for this enumeration, return None."""
        return cls._CF_enumeration.valueForUnicode(ustr)

class _Content (object):
    """Base for any wrapper added to L{complexTypeDefinition.orderedContent}."""

    def __getValue (self):
        """The value of the content.

        This is a unicode string for L{NonElementContent}, and (ideally) an
        instance of L{_TypeBinding_mixin} for L{ElementContent}."""
        return self.__value
    __value = None
    value = property(__getValue)

    @classmethod
    def ContentIterator (cls, input):
        """Return an iterator that filters and maps a sequence of L{_Content}
        instances.

        The returned iterator will filter out sequence members that are not
        instances of the class from which the iterator was created.  Further,
        only the L{value} field of the sequence member is returned.

        Thus the catenated text of the non-element content of an instance can
        be obtained with::

           text = six.u('').join(NonElementContent.ContentIterator(instance.orderedContent()))

        See also L{pyxb.NonElementContent}
        """
        class _Iterator (six.Iterator):
            def __init__ (self, input):
                self.__input = iter(input)
            def __iter__ (self):
                return self
            def __next__ (self):
                while True:
                    content = next(self.__input)
                    if isinstance(content, cls):
                        return content.value
        return _Iterator(input)

    def __init__ (self, value):
        self.__value = value

class ElementContent (_Content):
    """Marking wrapper for element content.

    The value should be translated into XML and made a child of its parent."""

    def __getElementDeclaration (self):
        """The L{pyxb.binding.content.ElementDeclaration} associated with the element content.
        This may be C{None} if the value is a wildcard."""
        return self.__elementDeclaration
    __elementDeclaration = None

    elementDeclaration = property(__getElementDeclaration)

    def __init__ (self, value, element_declaration=None, instance=None, tag=None):
        """Create a wrapper associating a value with its element declaration.

        Normally the element declaration is determined by consulting the
        content model when creating a binding instance.  When manipulating the
        preferred content list, this may be inconvenient to obtain; in that case
        provide the C{instance} in which the content appears immediately,
        along with the C{tag} that is used for the Python attribute that holds
        the element.

        @param value: the value of the element.  Should be an instance of
        L{_TypeBinding_mixin}, but for simple types might be a Python native
        type.

        @keyword element_declaration: The
        L{pyxb.binding.content.ElementDeclaration} associated with the element
        value.  Should be C{None} if the element matches wildcard content.

        @keyword instance: Alternative path to providing C{element_declaration}
        @keyword tag: Alternative path to providing C{element_declaration}
        """

        import pyxb.binding.content
        super(ElementContent, self).__init__(value)
        if instance is not None:
            if not isinstance(instance, complexTypeDefinition):
                raise pyxb.UsageError('Unable to determine element declaration')
            element_declaration = instance._UseForTag(tag)
        assert (element_declaration is None) or isinstance(element_declaration, pyxb.binding.content.ElementDeclaration)
        self.__elementDeclaration = element_declaration

class NonElementContent (_Content):
    """Marking wrapper for non-element content.

    The value will be unicode text, and should be appended as character
    data."""
    def __init__ (self, value):
        super(NonElementContent, self).__init__(six.text_type(value))

class complexTypeDefinition (_TypeBinding_mixin, utility._DeconflictSymbols_mixin, _DynamicCreate_mixin):
    """Base for any Python class that serves as the binding for an
    XMLSchema complexType.

    Subclasses should define a class-level _AttributeMap variable which maps
    from the unicode tag of an attribute to the AttributeUse instance that
    defines it.  Similarly, subclasses should define an _ElementMap variable.
    """

    _CT_EMPTY = 'EMPTY'                 #<<< No content
    _CT_SIMPLE = 'SIMPLE'               #<<< Simple (character) content
    _CT_MIXED = 'MIXED'                 #<<< Children may be elements or other (e.g., character) content
    _CT_ELEMENT_ONLY = 'ELEMENT_ONLY'   #<<< Expect only element content.

    _ContentTypeTag = None

    _TypeDefinition = None
    """Subclass of simpleTypeDefinition that corresponds to the type content.
    Only valid if _ContentTypeTag is _CT_SIMPLE"""

    # A value that indicates whether the content model for this type supports
    # wildcard elements.  Supporting classes should override this value.
    _HasWildcardElement = False

    # Map from expanded names to ElementDeclaration instances
    _ElementMap = { }
    """Map from expanded names to ElementDeclaration instances."""

    # Per-instance map from tags to attribute values for wildcard attributes.
    # Value is C{None} if the type does not support wildcard attributes.
    __wildcardAttributeMap = None

    def wildcardAttributeMap (self):
        """Obtain access to wildcard attributes.

        The return value is C{None} if this type does not support wildcard
        attributes.  If wildcard attributes are allowed, the return value is a
        map from QNames to the unicode string value of the corresponding
        attribute.

        @todo: The map keys should be namespace extended names rather than
        QNames, as the in-scope namespace may not be readily available to the
        user.
        """
        return self.__wildcardAttributeMap

    # Per-instance list of DOM nodes interpreted as wildcard elements.
    # Value is None if the type does not support wildcard elements.
    __wildcardElements = None

    def wildcardElements (self):
        """Obtain access to wildcard elements.

        The return value is C{None} if the content model for this type does not
        support wildcard elements.  If wildcard elements are allowed, the
        return value is a list of values corresponding to conformant
        unrecognized elements, in the order in which they were encountered.
        If the containing binding was created from an XML document and enough
        information was present to determine the binding of the member
        element, the value is a binding instance.  Otherwise, the value is the
        original DOM Element node.
        """
        return self.__wildcardElements

    def __init__ (self, *args, **kw):
        """Create a new instance of this binding.

        Arguments are used as transition values along the content model.
        Keywords are passed to the constructor of any simple content, or used
        to initialize attribute and element values whose L{id
        <content.ElementDeclaration.id>} (not L{name <content.ElementDeclaration.name>})
        matches the keyword.

        @keyword _dom_node: The node to use as the source of binding content.
        @type _dom_node: C{xml.dom.Element}

        @keyword _location: An optional instance of
        L{pyxb.utils.utility.Location} showing the origin the binding.  If
        C{None}, a value from C{_dom_node} is used if available.

        @keyword _from_xml: See L{_TypeBinding_mixin.Factory}

        @keyword _finalize_content_model: If C{True} the constructor invokes
        L{_TypeBinding_mixin._finalizeContentModel} prior to return.  The
        value defaults to C{False} when content is assigned through keyword
        parameters (bypassing the content model) or neither a C{_dom_node} nor
        positional element parameters have been provided, and to C{True} in
        all other cases.
        """

        fallback_namespace = kw.pop('_fallback_namespace', None)
        is_nil = False
        dom_node = kw.pop('_dom_node', None)
        location = kw.pop('_location', None)
        from_xml = kw.pop('_from_xml', dom_node is not None)
        do_finalize_content_model = kw.pop('_finalize_content_model', None)
        if dom_node is not None:
            if (location is None) and isinstance(dom_node, pyxb.utils.utility.Locatable_mixin):
                location = dom_node._location()
            if xml.dom.Node.DOCUMENT_NODE == dom_node.nodeType:
                dom_node = dom_node.documentElement
            #kw['_validate_constraints'] = False
            is_nil = XSI.nil.getAttribute(dom_node)
            if is_nil is not None:
                is_nil = kw['_nil'] = pyxb.binding.datatypes.boolean(is_nil)
        if location is not None:
            self._setLocation(location)
        if self._AttributeWildcard is not None:
            self.__wildcardAttributeMap = { }
        if self._HasWildcardElement:
            self.__wildcardElements = []
        if self._Abstract:
            raise pyxb.AbstractInstantiationError(type(self), location, dom_node)
        super(complexTypeDefinition, self).__init__(**kw)
        self.reset()
        self._setAttributesFromKeywordsAndDOM(kw, dom_node)
        did_set_kw_elt = False
        for fu in six.itervalues(self._ElementMap):
            iv = kw.pop(fu.id(), None)
            if iv is not None:
                did_set_kw_elt = True
                fu.set(self, iv)
        if do_finalize_content_model is None:
            do_finalize_content_model = not did_set_kw_elt
        if kw and kw.pop('_strict_keywords', True):
            [ kw.pop(_fkw, None) for _fkw in self._PyXBFactoryKeywords ]
            if kw:
                raise pyxb.UnprocessedKeywordContentError(self, kw)
        if 0 < len(args):
            if did_set_kw_elt:
                raise pyxb.UsageError('Cannot mix keyword and positional args for element initialization')
            self.extend(args, _from_xml=from_xml, _location=location)
        elif self._CT_SIMPLE == self._ContentTypeTag:
            value = self._TypeDefinition.Factory(_require_value=not self._isNil(), _dom_node=dom_node, _location=location, _nil=self._isNil(), _apply_attributes=False, *args)
            if value._constructedWithValue():
                self.append(value)
        elif dom_node is not None:
            self.extend(dom_node.childNodes[:], fallback_namespace)
        else:
            do_finalize_content_model = False
        if do_finalize_content_model:
            self._finalizeContentModel()

    # Specify the symbols to be reserved for all CTDs.
    _ReservedSymbols = _TypeBinding_mixin._ReservedSymbols.union(set([ 'wildcardElements', 'wildcardAttributeMap',
                             'xsdConstraintsOK', 'content', 'orderedContent', 'append', 'extend', 'value', 'reset' ]))

    # None, or a reference to a pyxb.utils.fac.Automaton instance that defines
    # the content model for the type.
    _Automaton = None

    @classmethod
    def _AddElement (cls, element):
        """Method used by generated code to associate the element binding with a use in this type.

        This is necessary because all complex type classes appear in the
        module prior to any of the element instances (which reference type
        classes), so the association must be formed after the element
        instances are available."""
        return cls._UseForTag(element.name())._setElementBinding(element)

    @classmethod
    def _UseForTag (cls, tag, raise_if_fail=True):
        """Return the ElementDeclaration object corresponding to the element name.

        @param tag: The L{ExpandedName} of an element in the class."""
        try:
            rv = cls._ElementMap[tag]
        except KeyError:
            if raise_if_fail:
                raise
            rv = None
        return rv

    def __childrenForDOM (self):
        """Generate a list of children in the order in which they should be
        added to the parent when creating a DOM representation of this
        object.

        @note: This is only used when L{pyxb.RequireValidWhenGenerating} has
        disabled validation.  Consequently, it may not generate valid XML.
        """
        order = []
        for ed in six.itervalues(self._ElementMap):
            value = ed.value(self)
            if value is None:
                continue
            if isinstance(value, list) and ed.isPlural():
                order.extend([ ElementContent(_v, ed) for _v in value ])
                continue
            order.append(ElementContent(value, ed))
        return order

    def _validatedChildren (self):
        """Provide the child elements and non-element content in an order
        consistent with the content model.

        Returns a sequence of tuples representing a valid path through the
        content model where each transition corresponds to one of the member
        element instances within this instance.  The tuple is a pair
        comprising the L{content.ElementDeclaration} instance and the value for the
        transition.

        If the content of the instance does not validate against the content
        model, an exception is raised.

        @return: C{None} or a list as described above.
        """
        if self._ContentTypeTag in (self._CT_EMPTY, self._CT_SIMPLE):
            return []
        self._resetAutomaton()
        return self.__automatonConfiguration.sequencedChildren()

    def _symbolSet (self):
        """Return a map from L{content.ElementDeclaration} instances to a list of
        values associated with that use.

        This is used as the set of symbols available for transitions when
        validating content against a model.  Note that the original
        L{content.ElementUse} that may have validated the assignment of the
        symbol to the content is no longer available, which may result in a
        different order being generated by the content model.  Preservation of
        the original order mitigates this risk.

        The value C{None} is used to provide the wildcard members, if any.

        If an element use has no associated values, it must not appear in the
        returned map.

        @raise pyxb.SimpleTypeValueError: when unable to convert element
        content to the binding declaration type.
        """
        rv = { }
        for eu in six.itervalues(self._ElementMap):
            value = eu.value(self)
            if value is None:
                continue
            converter = eu.elementBinding().compatibleValue
            if eu.isPlural():
                if 0 < len(value):
                    rv[eu] = [ converter(_v) for _v in value ]
            else:
                rv[eu] = [ converter(value)]
        wce = self.__wildcardElements
        if (wce is not None) and (0 < len(wce)):
            rv[None] = wce[:]
        return rv

    def _validateAttributes (self):
        for au in six.itervalues(self._AttributeMap):
            au.validate(self)

    def _validateBinding_vx (self):
        if self._isNil():
            if (self._IsSimpleTypeContent() and (self.__content is not None)) or self.__content:
                raise pyxb.ContentInNilInstanceError(self, self.__content)
            return True
        if self._IsSimpleTypeContent() and (self.__content is None):
            raise pyxb.SimpleContentAbsentError(self, self._location())
        order = self._validatedChildren()
        for content in order:
            if isinstance (content, NonElementContent):
                continue
            if isinstance(content.value, _TypeBinding_mixin):
                content.value.validateBinding()
            elif content.elementDeclaration is not None:
                _log.warning('Cannot validate value %s in field %s', content.value, content.elementDeclaration.id())
        self._validateAttributes()
        return True

    def _setAttribute (self, attr_en, value_lex):
        au = self._AttributeMap.get(attr_en)
        if au is None:
            if self._AttributeWildcard is None:
                raise pyxb.UnrecognizedAttributeError(type(self), attr_en, self)
            self.__wildcardAttributeMap[attr_en] = value_lex
        else:
            au.set(self, value_lex, from_xml=True)
        return au

    def xsdConstraintsOK (self, location=None):
        """Validate the content against the simple type.

        @return: C{True} if the content validates against its type.
        @raise pyxb.NotSimpleContentError: this type does not have simple content.
        @raise pyxb.SimpleContentAbsentError: the content of this type has not been set
        """
        # @todo: type check
        if self._CT_SIMPLE != self._ContentTypeTag:
            raise pyxb.NotSimpleContentError(self)
        if self._isNil():
            return True
        if self.__content is None:
            if location is None:
                location = self._location()
            raise pyxb.SimpleContentAbsentError(self, location)
        return self.value().xsdConstraintsOK(location)

    # __content is used in two ways: when complex content is used, it is as
    # documented in L{orderedContent}.  When simple content is used, it is as
    # documented in L{value}.
    __content = None

    def orderedContent (self):
        """Return the element and non-element content of the instance in order.

        This must be a complex type with complex content.  The return value is
        a list of the element and non-element content in a preferred order.

        The returned list contains L{element<ElementContent>} and
        L{non-element<NonElementContent>} content in the order which it was
        added to the instance.  This may have been through parsing a document,
        constructing an instance using positional arguments, invoking the
        L{append} or L{extend} methods, or assigning directly to an instance
        attribute associated with an element binding.

        @note: Be aware that assigning directly to an element attribute does not
        remove any previous value for the element from the content list.

        @note: Be aware that element values directly appended to an instance
        attribute with list type (viz., that corresponds to an element that
        allows more than one occurrence) will not appear in the ordered
        content list.

        The order in the list may influence the generation of documents
        depending on L{pyxb.ValidationConfig} values that apply to an
        instance.  Non-element content is emitted immediately prior to the
        following element in this list.  Any trailing non-element content is
        emitted after the last element in the content.  The list should
        include all element content.  Element content in this list that is not
        present within an element member of the binding instance may result in
        an error, or may be ignored.

        @note: The returned value is mutable, allowing the caller to change
        the order to be used.

        @raise pyxb.NotComplexContentError: this is not a complex type with mixed or element-only content
        """
        if self._ContentTypeTag in (self._CT_EMPTY, self._CT_SIMPLE):
            raise pyxb.NotComplexContentError(self)
        return self.__content

    @classmethod
    def __WarnOnContent (cls):
        if cls.__NeedWarnOnContent:
            import traceback
            cls.__NeedWarnOnContent = False
            _log.warning('Deprecated complexTypeDefinition method "content" invoked\nPlease use "orderedContent"\n%s', ''.join(traceback.format_stack()[:-2]))
            pass
    __NeedWarnOnContent = True

    def content (self):
        """Legacy interface for ordered content.

        This version does not accurately distinguish non-element content from
        element content that happens to have unicode type.

        @deprecated: use L{orderedContent}."""
        self.__WarnOnContent()
        if self._ContentTypeTag in (self._CT_EMPTY, self._CT_SIMPLE):
            raise pyxb.NotComplexContentError(self)
        return [ _v.value for _v in self.__content ]

    def value (self):
        """Return the value of the element.

        This must be a complex type with simple content.  The returned value
        is expected to be an instance of some L{simpleTypeDefinition} class.

        @raise pyxb.NotSimpleContentError: this is not a complex type with simple content
        """
        if self._CT_SIMPLE != self._ContentTypeTag:
            raise pyxb.NotSimpleContentError(self)
        return self.__content

    def _setValue (self, value):
        """Change the simple content value without affecting attributes."""
        if self._CT_SIMPLE != self._ContentTypeTag:
            raise pyxb.NotSimpleContentError(self)
        location = self._location()
        if self._isNil():
            if value is not None:
                raise pyxb.ContentInNilInstanceError(self, value, location)
        else:
            if not isinstance(value, self._TypeDefinition):
                value = self._TypeDefinition.Factory(value)
            self.__setContent(value)
            if self._validationConfig.forBinding:
                self.xsdConstraintsOK(location)
        return self

    def _resetContent (self, reset_elements=False):
        if reset_elements:
            for eu in six.itervalues(self._ElementMap):
                eu.reset(self)
        nv = None
        if self._ContentTypeTag in (self._CT_MIXED, self._CT_ELEMENT_ONLY):
            nv = []
        return self.__setContent(nv)

    __automatonConfiguration = None
    def _resetAutomaton (self):
        if self._Automaton is not None:
            if self.__automatonConfiguration is None:
                import pyxb.binding.content
                self.__automatonConfiguration = pyxb.binding.content.AutomatonConfiguration(self)
            self.__automatonConfiguration.reset()
        return self.__automatonConfiguration

    def _automatonConfiguration (self):
        """For whitebox testing use only"""
        return self.__automatonConfiguration

    def reset (self):
        """Reset the instance.

        This resets all element and attribute fields, and discards any
        recorded content.  It resets the content model automaton to its
        initial state.

        @see: Manipulate the return value of L{orderedContent} if your intent is
        to influence the generation of documents from the binding instance
        without changing its (element) content.
        """

        self._resetContent(reset_elements=True)
        for au in six.itervalues(self._AttributeMap):
            au.reset(self)
        self._resetAutomaton()
        return self

    @classmethod
    def _ElementBindingDeclForName (cls, element_name):
        """Determine what the given name means as an element in this type.

        Normally, C{element_name} identifies an element definition within this
        type.  If so, the returned C{element_decl} identifies that definition,
        and the C{element_binding} is extracted from that use.

        It may also be that the C{element_name} does not appear as an element
        definition, but that it identifies a global element.  In that case,
        the returned C{element_binding} identifies the global element.  If,
        further, that element is a member of a substitution group which does
        have an element definition in this class, then the returned
        C{element_decl} identifies that definition.

        If a non-C{None} C{element_decl} is returned, there will be an
        associated C{element_binding}.  However, it is possible to return a
        non-C{None} C{element_binding}, but C{None} as the C{element_decl}.  In
        that case, the C{element_binding} can be used to create a binding
        instance, but the content model will have to treat it as a wildcard.

        @param element_name: The name of the element in this type, either an
        expanded name or a local name if the element has an absent namespace.

        @return: C{( element_binding, element_decl )}
        """
        element_decl = cls._ElementMap.get(element_name)
        element_binding = None
        if element_decl is None:
            try:
                element_binding = element_name.elementBinding()
            except pyxb.NamespaceError:
                pass
            if element_binding is not None:
                element_decl = element_binding.findSubstituendDecl(cls)
        else:
            element_binding = element_decl.elementBinding()
        return (element_binding, element_decl)

    def append (self, value, **kw):
        """Add the value to the instance.

        The value should be a DOM node or other value that is or can be
        converted to a binding instance, or a string if the instance allows
        mixed content.  The value must be permitted by the content model.

        @raise pyxb.ContentValidationError: the value is not permitted at the current
        state of the content model.
        """

        # @todo: Allow caller to provide default element use; it's available
        # in saxer.
        element_decl = kw.get('_element_decl', None)
        maybe_element = kw.get('_maybe_element', True)
        location = kw.get('_location', None)
        if self._isNil():
            raise pyxb.ContentInNilInstanceError(self, value, location)
        fallback_namespace = kw.get('_fallback_namespace', None)
        require_validation = kw.get('_require_validation', self._validationConfig.forBinding)
        from_xml = kw.get('_from_xml', False)
        element_binding = None
        if element_decl is not None:
            from pyxb.binding import content
            assert isinstance(element_decl, content.ElementDeclaration)
            element_binding = element_decl.elementBinding()
            assert element_binding is not None
        # Convert the value if it's XML and we recognize it.
        if isinstance(value, xml.dom.Node):
            from_xml = True
            assert maybe_element
            assert element_binding is None
            node = value
            require_validation = pyxb.GlobalValidationConfig.forBinding
            if xml.dom.Node.COMMENT_NODE == node.nodeType:
                # @todo: Note that we're allowing comments inside the bodies
                # of simple content elements, which isn't really Hoyle.
                return self
            if node.nodeType in (xml.dom.Node.TEXT_NODE, xml.dom.Node.CDATA_SECTION_NODE):
                value = node.data
                maybe_element = False
            else:
                # Do type conversion here
                assert xml.dom.Node.ELEMENT_NODE == node.nodeType
                expanded_name = pyxb.namespace.ExpandedName(node, fallback_namespace=fallback_namespace)
                (element_binding, element_decl) = self._ElementBindingDeclForName(expanded_name)
                if element_binding is not None:
                    # If we have an element binding, we need to use it because
                    # it knows how to resolve substitution groups.
                    value = element_binding._createFromDOM(node, expanded_name, _fallback_namespace=fallback_namespace)
                else:
                    # If we don't have an element binding, we might still be
                    # able to convert this if it has an xsi:type attribute
                    # that names a valid type.
                    xsi_type = XSI.type.getAttribute(node)
                    try_create = False
                    if xsi_type is not None:
                        ns_ctx = pyxb.namespace.NamespaceContext.GetNodeContext(node)
                        (try_create, type_class) = XSI._InterpretTypeAttribute(xsi_type, ns_ctx, fallback_namespace, None)
                    if try_create:
                        value = element.CreateDOMBinding(node, None, _fallback_namespace=fallback_namespace)
                    else:
                        _log.warning('Unable to convert DOM node %s at %s to binding', expanded_name, getattr(node, 'location', '[UNAVAILABLE]'))
        if (not maybe_element) and isinstance(value, six.string_types) and (self._ContentTypeTag in (self._CT_EMPTY, self._CT_ELEMENT_ONLY)):
            if (0 == len(value.strip())) and not self._isNil():
                return self
        if maybe_element and (self.__automatonConfiguration is not None):
            # Allows element content.
            if not require_validation:
                if element_decl is not None:
                    element_decl.setOrAppend(self, value)
                    return self
                if self.__wildcardElements is not None:
                    self._appendWildcardElement(value)
                    return self
                raise pyxb.StructuralBadDocumentError(container=self, content=value)
            # Attempt to place the value based on the content model
            num_cand = self.__automatonConfiguration.step(value, element_decl)
            if 1 <= num_cand:
                # Resolution was successful (possibly non-deterministic)
                return self
        # We couldn't place this thing.  If it's element content, it has
        # to be placed.  Is it element content?
        #
        # If it's bound to an element, it's element content.
        #
        # Complex type instance?  Element content.
        #
        # Uninterpretable DOM nodes or binding wrappers?  Element content.
        #
        # Simple type definition?  Well, if the thing we're trying to fill
        # accepts mixed content or has simple content, technically we
        # could convert the value to text and use it.  So that's not
        # element content.
        if ((element_binding is not None)
            or isinstance(value, (xml.dom.Node, complexTypeDefinition, pyxb.BIND))
            or (isinstance(value, simpleTypeDefinition) and not (self._IsSimpleTypeContent() or self._IsMixed()))):
            # Element content.  If it has an automaton we can provide more
            # information.  If it doesn't, it must consume text and we should
            # use a different exception.
            if self.__automatonConfiguration:
                raise pyxb.UnrecognizedContentError(self, self.__automatonConfiguration, value, location)
            raise pyxb.NonElementValidationError(value, location)

        # We have something that doesn't seem to be an element.  Are we
        # expecting simple content?
        if self._IsSimpleTypeContent():
            if self.__content is not None:
                raise pyxb.ExtraSimpleContentError(self, value)
            if not self._isNil():
                if not isinstance(value, self._TypeDefinition):
                    value = self._TypeDefinition.Factory(value, _from_xml=from_xml)
                self.__setContent(value)
                if require_validation:
                    # NB: This only validates the value, not any associated
                    # attributes, which is correct to be parallel to complex
                    # content validation.
                    self.xsdConstraintsOK(location)
            return self

        # Do we allow non-element content?
        if not self._IsMixed():
            raise pyxb.MixedContentError(self, value, location)

        # It's character information.
        self._addContent(NonElementContent(value))
        return self

    def _appendWildcardElement (self, value):
        if (isinstance(value, xml.dom.Node)
            or (isinstance(value, _TypeBinding_mixin) and (value._element is not None))):
            # Something that we can interpret as an element
            self._addContent(ElementContent(value, None))
            self.__wildcardElements.append(value)
        elif self._IsMixed():
            # Not an element, but allowed as mixed content
            self._addContent(NonElementContent(value))
        else:
            # Not an element and no mixed content allowed: error
            raise pyxb.MixedContentError(self, value)

    def extend (self, value_list, _fallback_namespace=None, _from_xml=False, _location=None):
        """Invoke L{append} for each value in the list, in turn."""
        kw = { '_fallback_namespace': _fallback_namespace,
               '_from_xml': _from_xml,
               '_location': _location }
        [ self.append(_v, **kw) for _v in value_list ]
        return self

    def __setContent (self, value):
        self.__content = value
        return self.__content

    def _addContent (self, wrapped_value):
        # This assert is inadequate in the case of plural/non-plural elements with an STD_list base type.
        # Trust that validation elsewhere was done correctly.
        #assert self._IsMixed() or (not self._performValidation()) or isinstance(child, _TypeBinding_mixin) or isinstance(child, six.string_types), 'Unrecognized child %s type %s' % (child, type(child))
        assert not (self._ContentTypeTag in (self._CT_EMPTY, self._CT_SIMPLE))
        assert isinstance(wrapped_value, _Content)
        self.__content.append(wrapped_value)
        if isinstance(wrapped_value, ElementContent):
            value = wrapped_value.value
            ed = wrapped_value.elementDeclaration
            if isinstance(value, _TypeBinding_mixin) and (ed is not None) and (value._element() is None):
                assert isinstance(ed.elementBinding(), element)
                value._setElement(ed.elementBinding())

    @classmethod
    def _IsMixed (cls):
        return (cls._CT_MIXED == cls._ContentTypeTag)

    def _finalizeContentModel (self):
        # Override parent implementation.
        if self.__automatonConfiguration:
            self.__automatonConfiguration.resolveNondeterminism()

    def _postDOMValidate (self):
        # It's probably finalized already, but just in case...
        self._finalizeContentModel()
        if self._validationConfig.forBinding:
            # @todo isNil should verify that no content is present.
            if (not self._isNil()) and (self.__automatonConfiguration is not None):
                if not self.__automatonConfiguration.isAccepting():
                    if self._IsSimpleTypeContent():
                        raise pyxb.SimpleContentAbsentError(self, self._location())
                    self.__automatonConfiguration.diagnoseIncompleteContent()
            self._validateAttributes()
        return self

    def _setDOMFromAttributes (self, dom_support, element):
        """Add any appropriate attributes from this instance into the DOM element."""
        for au in six.itervalues(self._AttributeMap):
            if pyxb.GlobalValidationConfig.forDocument:
                au.validate(self)
            au.addDOMAttribute(dom_support, self, element)
        if self.__wildcardAttributeMap:
            for (an, av) in six.iteritems(self.__wildcardAttributeMap):
                dom_support.addAttribute(element, an, av)
        return element

    def _toDOM_csc (self, dom_support, parent):
        """Create a DOM element with the given tag holding the content of this instance."""
        element = parent
        self._setDOMFromAttributes(dom_support, element)
        if self._isNil():
            pass
        elif self._CT_EMPTY == self._ContentTypeTag:
            pass
        elif self._CT_SIMPLE == self._ContentTypeTag:
            if self.__content is None:
                raise pyxb.SimpleContentAbsentError(self, self._location())
            dom_support.appendTextChild(self.value(), element)
        else:
            if pyxb.GlobalValidationConfig.forDocument:
                order = self._validatedChildren()
            else:
                order = self.__childrenForDOM()
            for content in order:
                assert id(content.value) != id(self)
                if isinstance(content, NonElementContent):
                    dom_support.appendTextChild(content.value, element)
                    continue
                if content.elementDeclaration is None:
                    if isinstance(content.value, xml.dom.Node):
                        dom_support.appendChild(content.value, element)
                    else:
                        content.value.toDOM(dom_support, parent)
                else:
                    content.elementDeclaration.toDOM(dom_support, parent, content.value)
            mixed_content = self.orderedContent()
            for mc in mixed_content:
                pass
        return getattr(super(complexTypeDefinition, self), '_toDOM_csc', lambda *_args,**_kw: dom_support)(dom_support, parent)

    @classmethod
    def _IsSimpleTypeContent (cls):
        """CTDs with simple content are simple; other CTDs are not."""
        return cls._CT_SIMPLE == cls._ContentTypeTag

    @classmethod
    def _description (cls, name_only=False, user_documentation=True):
        name = cls._Name()
        if name_only:
            return name
        desc = [ name ]
        if cls._CT_EMPTY == cls._ContentTypeTag:
            desc.append(', empty content')
        elif cls._CT_SIMPLE == cls._ContentTypeTag:
            desc.extend([', simple content type ', cls._TypeDefinition._description(name_only=True)])
        else:
            if cls._CT_MIXED == cls._ContentTypeTag:
                desc.append(', mixed content')
            else:
                assert cls._CT_ELEMENT_ONLY == cls._ContentTypeTag
                desc.append(', element-only content')
        if (0 < len(cls._AttributeMap)) or (cls._AttributeWildcard is not None):
            desc.append("\nAttributes:\n  ")
            desc.append("\n  ".join([ _au._description(user_documentation=False) for _au in six.itervalues(cls._AttributeMap) ]))
            if cls._AttributeWildcard is not None:
                desc.append("\n  Wildcard attribute(s)")
        if (0 < len(cls._ElementMap)) or cls._HasWildcardElement:
            desc.append("\nElements:\n  ")
            desc.append("\n  ".join([ _eu._description(user_documentation=False) for _eu in six.itervalues(cls._ElementMap) ]))
            if cls._HasWildcardElement:
                desc.append("\n  Wildcard element(s)")
        return ''.join(desc)

## Local Variables:
## fill-column:78
## End:
