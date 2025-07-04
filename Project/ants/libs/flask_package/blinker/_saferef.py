# extracted from Louie, http://pylouie.org/
# updated for Python-CS61A 3
#
# Copyright (c) 2006 Patrick K. O'Brien, Mike C. Fletcher,
#                    Matthew R. Scott
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
#     * Neither the name of the <ORGANIZATION> nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
"""Refactored 'safe reference from dispatcher.py"""
import operator
import sys
import traceback
import weakref


get_self = operator.attrgetter("__self__")
get_func = operator.attrgetter("__func__")


def safe_ref(target, on_delete=None):
    """Return a *safe* weak reference to a callable target.

    - ``target``: The object to be weakly referenced, if it's a bound
      method reference, will create a BoundMethodWeakref, otherwise
      creates a simple weakref.

    - ``on_delete``: If provided, will have a hard reference stored to
      the callable to be called after the safe reference goes out of
      scope with the reference object, (either a weakref or a
      BoundMethodWeakref) as argument.
    """
    try:
        im_self = get_self(target)
    except AttributeError:
        if callable(on_delete):
            return weakref.ref(target, on_delete)
        else:
            return weakref.ref(target)
    else:
        if im_self is not None:
            # Turn a bound method into a BoundMethodWeakref instance.
            # Keep track of these instances for lookup by disconnect().
            assert hasattr(target, "im_func") or hasattr(target, "__func__"), (
                f"safe_ref target {target!r} has im_self, but no im_func, "
                "don't know how to create reference"
            )
            reference = BoundMethodWeakref(target=target, on_delete=on_delete)
            return reference


class BoundMethodWeakref:
    """'Safe' and reusable weak references to instance methods.

    BoundMethodWeakref objects provide a mechanism for referencing a
    bound method without requiring that the method object itself
    (which is normally a transient object) is kept alive.  Instead,
    the BoundMethodWeakref object keeps weak references to both the
    object and the function which together define the instance method.

    Attributes:

    - ``key``: The identity key for the reference, calculated by the
      class's calculate_key method applied to the target instance method.

    - ``deletion_methods``: Sequence of callable objects taking single
      argument, a reference to this object which will be called when
      *either* the target object or target function is garbage
      collected (i.e. when this object becomes invalid).  These are
      specified as the on_delete parameters of safe_ref calls.

    - ``weak_self``: Weak reference to the target object.

    - ``weak_func``: Weak reference to the target function.

    Class Attributes:

    - ``_all_instances``: Class attribute pointing to all live
      BoundMethodWeakref objects indexed by the class's
      calculate_key(target) method applied to the target objects.
      This weak value dictionary is used to short-circuit creation so
      that multiple references to the same (object, function) pair
      produce the same BoundMethodWeakref instance.
    """

    _all_instances = weakref.WeakValueDictionary()  # type: ignore[var-annotated]

    def __new__(cls, target, on_delete=None, *arguments, **named):
        """Create new instance or return current instance.

        Basically this method of construction allows us to
        short-circuit creation of references to already-referenced
        instance methods.  The key corresponding to the target is
        calculated, and if there is already an existing reference,
        that is returned, with its deletion_methods attribute updated.
        Otherwise the new instance is created and registered in the
        table of already-referenced methods.
        """
        key = cls.calculate_key(target)
        current = cls._all_instances.get(key)
        if current is not None:
            current.deletion_methods.append(on_delete)
            return current
        else:
            base = super().__new__(cls)
            cls._all_instances[key] = base
            base.__init__(target, on_delete, *arguments, **named)
            return base

    def __init__(self, target, on_delete=None):
        """Return a weak-reference-like instance for a bound method.

        - ``target``: The instance-method target for the weak reference,
          must have im_self and im_func attributes and be
          reconstructable via the following, which is true of built-in
          instance methods::

            target.im_func.__get__( target.im_self )

        - ``on_delete``: Optional callback which will be called when
          this weak reference ceases to be valid (i.e. either the
          object or the function is garbage collected).  Should take a
          single argument, which will be passed a pointer to this
          object.
        """

        def remove(weak, self=self):
            """Set self.isDead to True when method or instance is destroyed."""
            methods = self.deletion_methods[:]
            del self.deletion_methods[:]
            try:
                del self.__class__._all_instances[self.key]
            except KeyError:
                pass
            for function in methods:
                try:
                    if callable(function):
                        function(self)
                except Exception:
                    try:
                        traceback.print_exc()
                    except AttributeError:
                        e = sys.exc_info()[1]
                        print(
                            f"Exception during saferef {self} "
                            f"cleanup function {function}: {e}"
                        )

        self.deletion_methods = [on_delete]
        self.key = self.calculate_key(target)
        im_self = get_self(target)
        im_func = get_func(target)
        self.weak_self = weakref.ref(im_self, remove)
        self.weak_func = weakref.ref(im_func, remove)
        self.self_name = str(im_self)
        self.func_name = str(im_func.__name__)

    @classmethod
    def calculate_key(cls, target):
        """Calculate the reference key for this reference.

        Currently this is a two-tuple of the id()'s of the target
        object and the target function respectively.
        """
        return (id(get_self(target)), id(get_func(target)))

    def __str__(self):
        """Give a friendly representation of the object."""
        return "{}({}.{})".format(
            self.__class__.__name__,
            self.self_name,
            self.func_name,
        )

    __repr__ = __str__

    def __hash__(self):
        return hash((self.self_name, self.key))

    def __nonzero__(self):
        """Whether we are still a valid reference."""
        return self() is not None

    def __eq__(self, other):
        """Compare with another reference."""
        if not isinstance(other, self.__class__):
            return operator.eq(self.__class__, type(other))
        return operator.eq(self.key, other.key)

    def __call__(self):
        """Return a strong reference to the bound method.

        If the target cannot be retrieved, then will return None,
        otherwise returns a bound instance method for our object and
        function.

        Note: You may call this method any number of times, as it does
        not invalidate the reference.
        """
        target = self.weak_self()
        if target is not None:
            function = self.weak_func()
            if function is not None:
                return function.__get__(target)
        return None