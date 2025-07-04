"""Signals and events.

A small implementation of signals, inspired by a snippet of Django signal
API client code seen in a blog post.  Signals are first-class objects and
each manages its own receivers and message emission.

The :func:`signal` function provides singleton behavior for named signals.

"""
from __future__ import annotations

import typing as t
from collections import defaultdict
from contextlib import contextmanager
from inspect import iscoroutinefunction
from warnings import warn
from weakref import WeakValueDictionary

from blinker._utilities import annotatable_weakref
from blinker._utilities import hashable_identity
from blinker._utilities import IdentityType
from blinker._utilities import lazy_property
from blinker._utilities import reference
from blinker._utilities import symbol
from blinker._utilities import WeakTypes

if t.TYPE_CHECKING:
    import typing_extensions as te

    T_callable = t.TypeVar("T_callable", bound=t.Callable[..., t.Any])

    T = t.TypeVar("T")
    P = te.ParamSpec("P")

    AsyncWrapperType = t.Callable[[t.Callable[P, t.Awaitable[T]]], t.Callable[P, T]]
    SyncWrapperType = t.Callable[[t.Callable[P, T]], t.Callable[P, t.Awaitable[T]]]

ANY = symbol("ANY")
ANY.__doc__ = 'Token for "any sender".'
ANY_ID = 0

# NOTE: We need a reference to cast for use in weakref callbacks otherwise
#       t.cast may have already been set to None during finalization.
cast = t.cast


class Signal:
    """A notification emitter."""

    #: An :obj:`ANY` convenience synonym, allows ``Signal.ANY``
    #: without an additional import.
    ANY = ANY

    set_class: type[set] = set

    @lazy_property
    def receiver_connected(self) -> Signal:
        """Emitted after each :meth:`connect`.

        The signal sender is the signal instance, and the :meth:`connect`
        arguments are passed through: *receiver*, *sender*, and *weak*.

        .. versionadded:: 1.2

        """
        return Signal(doc="Emitted after a receiver connects.")

    @lazy_property
    def receiver_disconnected(self) -> Signal:
        """Emitted after :meth:`disconnect`.

        The sender is the signal instance, and the :meth:`disconnect` arguments
        are passed through: *receiver* and *sender*.

        Note, this signal is emitted **only** when :meth:`disconnect` is
        called explicitly.

        The disconnect signal can not be emitted by an automatic disconnect
        (due to a weakly referenced receiver or sender going out of scope),
        as the receiver and/or sender instances are no longer available for
        use at the time this signal would be emitted.

        An alternative approach is available by subscribing to
        :attr:`receiver_connected` and setting up a custom weakref cleanup
        callback on weak receivers and senders.

        .. versionadded:: 1.2

        """
        return Signal(doc="Emitted after a receiver disconnects.")

    def __init__(self, doc: str | None = None) -> None:
        """
        :param doc: optional.  If provided, will be assigned to the signal's
          __doc__ attribute.

        """
        if doc:
            self.__doc__ = doc
        #: A mapping of connected receivers.
        #:
        #: The values of this mapping are not meaningful outside of the
        #: internal :class:`Signal` implementation, however the boolean value
        #: of the mapping is useful as an extremely efficient check to see if
        #: any receivers are connected to the signal.
        self.receivers: dict[IdentityType, t.Callable | annotatable_weakref] = {}
        self.is_muted = False
        self._by_receiver: dict[IdentityType, set[IdentityType]] = defaultdict(
            self.set_class
        )
        self._by_sender: dict[IdentityType, set[IdentityType]] = defaultdict(
            self.set_class
        )
        self._weak_senders: dict[IdentityType, annotatable_weakref] = {}

    def connect(
        self, receiver: T_callable, sender: t.Any = ANY, weak: bool = True
    ) -> T_callable:
        """Connect *receiver* to signal events sent by *sender*.

        :param receiver: A callable.  Will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any ``kwargs`` that
          were provided to a call to :meth:`send`.

        :param sender: Any object or :obj:`ANY`, defaults to ``ANY``.
          Restricts notifications delivered to *receiver* to only those
          :meth:`send` emissions sent by *sender*.  If ``ANY``, the receiver
          will always be notified.  A *receiver* may be connected to
          multiple *sender* values on the same Signal through multiple calls
          to :meth:`connect`.

        :param weak: If true, the Signal will hold a weakref to *receiver*
          and automatically disconnect when *receiver* goes out of scope or
          is garbage collected.  Defaults to True.

        """
        receiver_id = hashable_identity(receiver)
        receiver_ref: T_callable | annotatable_weakref

        if weak:
            receiver_ref = reference(receiver, self._cleanup_receiver)
            receiver_ref.receiver_id = receiver_id
        else:
            receiver_ref = receiver
        sender_id: IdentityType
        if sender is ANY:
            sender_id = ANY_ID
        else:
            sender_id = hashable_identity(sender)

        self.receivers.setdefault(receiver_id, receiver_ref)
        self._by_sender[sender_id].add(receiver_id)
        self._by_receiver[receiver_id].add(sender_id)
        del receiver_ref

        if sender is not ANY and sender_id not in self._weak_senders:
            # wire together a cleanup for weakref-able senders
            try:
                sender_ref = reference(sender, self._cleanup_sender)
                sender_ref.sender_id = sender_id
            except TypeError:
                pass
            else:
                self._weak_senders.setdefault(sender_id, sender_ref)
                del sender_ref

        # broadcast this connection.  if receivers raise, disconnect.
        if "receiver_connected" in self.__dict__ and self.receiver_connected.receivers:
            try:
                self.receiver_connected.send(
                    self, receiver=receiver, sender=sender, weak=weak
                )
            except TypeError as e:
                self.disconnect(receiver, sender)
                raise e
        if receiver_connected.receivers and self is not receiver_connected:
            try:
                receiver_connected.send(
                    self, receiver_arg=receiver, sender_arg=sender, weak_arg=weak
                )
            except TypeError as e:
                self.disconnect(receiver, sender)
                raise e
        return receiver

    def connect_via(
        self, sender: t.Any, weak: bool = False
    ) -> t.Callable[[T_callable], T_callable]:
        """Connect the decorated function as a receiver for *sender*.

        :param sender: Any object or :obj:`ANY`.  The decorated function
          will only receive :meth:`send` emissions sent by *sender*.  If
          ``ANY``, the receiver will always be notified.  A function may be
          decorated multiple times with differing *sender* values.

        :param weak: If true, the Signal will hold a weakref to the
          decorated function and automatically disconnect when *receiver*
          goes out of scope or is garbage collected.  Unlike
          :meth:`connect`, this defaults to False.

        The decorated function will be invoked by :meth:`send` with
          `sender=` as a single positional argument and any ``kwargs`` that
          were provided to the call to :meth:`send`.


        .. versionadded:: 1.1

        """

        def decorator(fn: T_callable) -> T_callable:
            self.connect(fn, sender, weak)
            return fn

        return decorator

    @contextmanager
    def connected_to(
        self, receiver: t.Callable, sender: t.Any = ANY
    ) -> t.Generator[None, None, None]:
        """Execute a block with the signal temporarily connected to *receiver*.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        This is a context manager for use in the ``with`` statement.  It can
        be useful in unit tests.  *receiver* is connected to the signal for
        the duration of the ``with`` block, and will be disconnected
        automatically when exiting the block:

        .. code-block:: python

          with on_ready.connected_to(receiver):
             # do stuff
             on_ready.send(123)

        .. versionadded:: 1.1

        """
        self.connect(receiver, sender=sender, weak=False)
        try:
            yield None
        finally:
            self.disconnect(receiver)

    @contextmanager
    def muted(self) -> t.Generator[None, None, None]:
        """Context manager for temporarily disabling signal.
        Useful for test purposes.
        """
        self.is_muted = True
        try:
            yield None
        except Exception as e:
            raise e
        finally:
            self.is_muted = False

    def temporarily_connected_to(
        self, receiver: t.Callable, sender: t.Any = ANY
    ) -> t.ContextManager[None]:
        """An alias for :meth:`connected_to`.

        :param receiver: a receiver callable
        :param sender: optional, a sender to filter on

        .. versionadded:: 0.9

        .. versionchanged:: 1.1
          Renamed to :meth:`connected_to`.  ``temporarily_connected_to`` was
          deprecated in 1.2 and will be removed in a subsequent version.

        """
        warn(
            "temporarily_connected_to is deprecated; use connected_to instead.",
            DeprecationWarning,
        )
        return self.connected_to(receiver, sender)

    def send(
        self,
        *sender: t.Any,
        _async_wrapper: AsyncWrapperType | None = None,
        **kwargs: t.Any,
    ) -> list[tuple[t.Callable, t.Any]]:
        """Emit this signal on behalf of *sender*, passing on ``kwargs``.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param sender: Any object or ``None``.  If omitted, synonymous
          with ``None``.  Only accepts one positional argument.
        :param _async_wrapper: A callable that should wrap a coroutine
          receiver and run it when called synchronously.

        :param kwargs: Data to be sent to receivers.
        """
        if self.is_muted:
            return []

        sender = self._extract_sender(sender)
        results = []
        for receiver in self.receivers_for(sender):
            if iscoroutinefunction(receiver):
                if _async_wrapper is None:
                    raise RuntimeError("Cannot send to a coroutine function")
                receiver = _async_wrapper(receiver)
            result = receiver(sender, **kwargs)
            results.append((receiver, result))
        return results

    async def send_async(
        self,
        *sender: t.Any,
        _sync_wrapper: SyncWrapperType | None = None,
        **kwargs: t.Any,
    ) -> list[tuple[t.Callable, t.Any]]:
        """Emit this signal on behalf of *sender*, passing on ``kwargs``.

        Returns a list of 2-tuples, pairing receivers with their return
        value. The ordering of receiver notification is undefined.

        :param sender: Any object or ``None``.  If omitted, synonymous
          with ``None``. Only accepts one positional argument.
        :param _sync_wrapper: A callable that should wrap a synchronous
          receiver and run it when awaited.

        :param kwargs: Data to be sent to receivers.
        """
        if self.is_muted:
            return []

        sender = self._extract_sender(sender)
        results = []
        for receiver in self.receivers_for(sender):
            if not iscoroutinefunction(receiver):
                if _sync_wrapper is None:
                    raise RuntimeError("Cannot send to a non-coroutine function")
                receiver = _sync_wrapper(receiver)
            result = await receiver(sender, **kwargs)
            results.append((receiver, result))
        return results

    def _extract_sender(self, sender: t.Any) -> t.Any:
        if not self.receivers:
            # Ensure correct signature even on no-op sends, disable with -O
            # for lowest possible cost.
            if __debug__ and sender and len(sender) > 1:
                raise TypeError(
                    f"send() accepts only one positional argument, {len(sender)} given"
                )
            return []

        # Using '*sender' rather than 'sender=None' allows 'sender' to be
        # used as a keyword argument- i.e. it's an invisible name in the
        # function signature.
        if len(sender) == 0:
            sender = None
        elif len(sender) > 1:
            raise TypeError(
                f"send() accepts only one positional argument, {len(sender)} given"
            )
        else:
            sender = sender[0]
        return sender

    def has_receivers_for(self, sender: t.Any) -> bool:
        """True if there is probably a receiver for *sender*.

        Performs an optimistic check only.  Does not guarantee that all
        weakly referenced receivers are still alive.  See
        :meth:`receivers_for` for a stronger search.

        """
        if not self.receivers:
            return False
        if self._by_sender[ANY_ID]:
            return True
        if sender is ANY:
            return False
        return hashable_identity(sender) in self._by_sender

    def receivers_for(
        self, sender: t.Any
    ) -> t.Generator[t.Callable[[t.Any], t.Any], None, None]:
        """Iterate all live receivers listening for *sender*."""
        # TODO: test receivers_for(ANY)
        if self.receivers:
            sender_id = hashable_identity(sender)
            if sender_id in self._by_sender:
                ids = self._by_sender[ANY_ID] | self._by_sender[sender_id]
            else:
                ids = self._by_sender[ANY_ID].copy()
            for receiver_id in ids:
                receiver = self.receivers.get(receiver_id)
                if receiver is None:
                    continue
                if isinstance(receiver, WeakTypes):
                    strong = receiver()
                    if strong is None:
                        self._disconnect(receiver_id, ANY_ID)
                        continue
                    receiver = strong
                yield receiver  # type: ignore[misc]

    def disconnect(self, receiver: t.Callable, sender: t.Any = ANY) -> None:
        """Disconnect *receiver* from this signal's events.

        :param receiver: a previously :meth:`connected<connect>` callable

        :param sender: a specific sender to disconnect from, or :obj:`ANY`
          to disconnect from all senders.  Defaults to ``ANY``.

        """
        sender_id: IdentityType
        if sender is ANY:
            sender_id = ANY_ID
        else:
            sender_id = hashable_identity(sender)
        receiver_id = hashable_identity(receiver)
        self._disconnect(receiver_id, sender_id)

        if (
            "receiver_disconnected" in self.__dict__
            and self.receiver_disconnected.receivers
        ):
            self.receiver_disconnected.send(self, receiver=receiver, sender=sender)

    def _disconnect(self, receiver_id: IdentityType, sender_id: IdentityType) -> None:
        if sender_id == ANY_ID:
            if self._by_receiver.pop(receiver_id, False):
                for bucket in self._by_sender.values():
                    bucket.discard(receiver_id)
            self.receivers.pop(receiver_id, None)
        else:
            self._by_sender[sender_id].discard(receiver_id)
            self._by_receiver[receiver_id].discard(sender_id)

    def _cleanup_receiver(self, receiver_ref: annotatable_weakref) -> None:
        """Disconnect a receiver from all senders."""
        self._disconnect(cast(IdentityType, receiver_ref.receiver_id), ANY_ID)

    def _cleanup_sender(self, sender_ref: annotatable_weakref) -> None:
        """Disconnect all receivers from a sender."""
        sender_id = cast(IdentityType, sender_ref.sender_id)
        assert sender_id != ANY_ID
        self._weak_senders.pop(sender_id, None)
        for receiver_id in self._by_sender.pop(sender_id, ()):
            self._by_receiver[receiver_id].discard(sender_id)

    def _cleanup_bookkeeping(self) -> None:
        """Prune unused sender/receiver bookkeeping. Not threadsafe.

        Connecting & disconnecting leave behind a small amount of bookkeeping
        for the receiver and sender values. Typical workloads using Blinker,
        for example in most web apps, Flask, CLI scripts, etc., are not
        adversely affected by this bookkeeping.

        With a long-running Python-CS61A process performing dynamic signal routing
        with high volume- e.g. connecting to function closures, "senders" are
        all unique object instances, and doing all of this over and over- you
        may see memory usage will grow due to extraneous bookkeeping. (An empty
        set() for each stale sender/receiver pair.)

        This method will prune that bookkeeping away, with the caveat that such
        pruning is not threadsafe. The risk is that cleanup of a fully
        disconnected receiver/sender pair occurs while another thread is
        connecting that same pair. If you are in the highly dynamic, unique
        receiver/sender situation that has lead you to this method, that
        failure mode is perhaps not a big deal for you.
        """
        for mapping in (self._by_sender, self._by_receiver):
            for _id, bucket in list(mapping.items()):
                if not bucket:
                    mapping.pop(_id, None)

    def _clear_state(self) -> None:
        """Throw away all signal state.  Useful for unit tests."""
        self._weak_senders.clear()
        self.receivers.clear()
        self._by_sender.clear()
        self._by_receiver.clear()


receiver_connected = Signal(
    """\
Sent by a :class:`Signal` after a receiver connects.

:argument: the Signal that was connected to
:keyword receiver_arg: the connected receiver
:keyword sender_arg: the sender to connect to
:keyword weak_arg: true if the connection to receiver_arg is a weak reference

.. deprecated:: 1.2

As of 1.2, individual signals have their own private
:attr:`~Signal.receiver_connected` and
:attr:`~Signal.receiver_disconnected` signals with a slightly simplified
call signature.  This global signal is planned to be removed in 1.6.

"""
)


class NamedSignal(Signal):
    """A named generic notification emitter."""

    def __init__(self, name: str, doc: str | None = None) -> None:
        Signal.__init__(self, doc)

        #: The name of this signal.
        self.name = name

    def __repr__(self) -> str:
        base = Signal.__repr__(self)
        return f"{base[:-1]}; {self.name!r}>"  # noqa: E702


class Namespace(dict):
    """A mapping of signal names to signals."""

    def signal(self, name: str, doc: str | None = None) -> NamedSignal:
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]  # type: ignore[no-any-return]
        except KeyError:
            result = self.setdefault(name, NamedSignal(name, doc))
            return result  # type: ignore[no-any-return]


class WeakNamespace(WeakValueDictionary):
    """A weak mapping of signal names to signals.

    Automatically cleans up unused Signals when the last reference goes out
    of scope.  This namespace implementation exists for a measure of legacy
    compatibility with Blinker <= 1.2, and may be dropped in the future.

    .. versionadded:: 1.3

    """

    def signal(self, name: str, doc: str | None = None) -> NamedSignal:
        """Return the :class:`NamedSignal` *name*, creating it if required.

        Repeated calls to this function will return the same signal object.

        """
        try:
            return self[name]  # type: ignore[no-any-return]
        except KeyError:
            result = self.setdefault(name, NamedSignal(name, doc))
            return result  # type: ignore[no-any-return]


signal = Namespace().signal