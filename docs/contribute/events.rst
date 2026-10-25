Events
======

.. tags:: events


To provide a flexible way to hook into the existing and future components, HARP uses an event-driven architecture.


.. _eda:
Event Driven Architecture
:::::::::::::::::::::::::

An :ref:`Event Driven Architecture (EDA) <eda>` emits or receives events occurring in different parts of a system.
Events can be network-based, like in microservice architectures with an event bus (e.g., CQRS or event-sourcing
systems), or internal to a process, like in HARP, allowing components to communicate and extend each other without tight
coupling. This makes the software easier to maintain, as listeners do not need to know about the emitters and vice
versa. An example of in-process event dispatching familiar to web developers is DOM events in the browser: you can
listen to a click event on a button without knowing how the button is implemented.

HARP uses :mod:`Whistle <whistle>`, a simple Python event dispatcher, to allow both built-in and custom applications to
easily expose or hook into system events. For instance, events occur each time a transaction or an HTTP request or
response passes through the proxy, and you can listen to these events to implement custom behaviors.


.. _events:
Defining and exposing Events
::::::::::::::::::::::::::::

An event is usually just a symbolic name (a string) that represents something happening in the system. If your
event is also associated with some context that the listeners might be interested in, you can associate it with a
custom :class:`whistle.Event` class that will serve as an envelope for this context.

.. code-block:: python

    import asyncio
    from whistle import Event, AsyncEventDispatcher

    class MyEvent(Event):
        def __init__(self, context):
            super().__init__()
            self.context = context

    async def main(dispatcher):
        event = await dispatcher.adispatch('my.event', MyEvent({'foo': 'bar'}))

        # the context can be accessed and changed by the listeners
        print(event.context)

    if __name__ == '__main__':
        dispatcher = AsyncEventDispatcher()
        asyncio.run(main(dispatcher))

This isolated example uses a local event dispatcher, meaning the listeners collection is confined to each instance,
limiting its utility. In a real-world application, you would use the event dispatcher registered in the
:ref:`system-wide dependency-injection container <dic>` to enable components to listen to events from other components.

.. code-block:: python

    class MyEventEmittingService:
        def __init__(self, dispatcher: IAsyncEventDispatcher):
            self.dispatcher = dispatcher

        async def handle(self):
            event = await self.dispatcher.adispatch('my.event', MyEvent({'foo': 'bar'}))

Now, if this class is registered with the dependency-injection container, it will receive the container-wide instance
of the event dispatcher, and it will be able to listen to events from other components.

If you expose events to the world, it's a good idea to define them in a ``events`` module or package within your
application, exposing both the custom event classes and the symbolic names as constants:

.. code-block:: python

    from whistle import Event

    class MyEvent(Event):
        def __init__(self, context):
            super().__init__()
            self.context = context

    MY_EVENT = 'my.event'


Listening to Events
:::::::::::::::::::

To react to an event you simply register a listener with the dispatcher. The listener is an asynchronous callable that
will be called with the event instance when the event is dispatched.

.. code-block:: python

    async def my_listener(event: MyEvent):
        print(event.context)

    async def main():
        dispatcher = AsyncEventDispatcher()
        dispatcher.add_listener(MY_EVENT, my_listener)

        await dispatcher.adispatch(MY_EVENT, MyEvent({'foo': 'bar'}))

    if __name__ == '__main__':
        asyncio.run(main())

Once again, this is an isolated class. A real-world application would register the listener with the system-wide
event dispatcher, so it can listen to events from any component registered with the same dispatcher:

.. code-block:: python

    class MyEventListener:
        def __init__(self, dispatcher: IAsyncEventDispatcher):
            self.dispatcher = dispatcher
            self.dispatcher.add_listener(MY_EVENT, self.handle)

        async def handle(self, event: MyEvent):
            print(event.context)


.. _events-unit-of-work:
Recording an auditable event
::::::::::::::::::::::::::::

An action on the control plane and the record of it share one database commit, without the acting application knowing
what records it. Declare the event with the ``auditable`` mark (the event id is part of the mark), then hand it to a
unit of work:

.. code-block:: python

    from harp.unit_of_work import IUnitOfWorkFactory, auditable

    @auditable("accounts.role_changed")
    class RoleChanged(Event):
        ...

    class AccountsService:
        def __init__(self, unit_of_work: IUnitOfWorkFactory):
            self.unit_of_work = unit_of_work

        async def change_role(self, ...):
            async with self.unit_of_work() as uow:
                ...  # the change
                await uow.record(RoleChanged(...))

``record`` runs in two phases:

1. Inside the transaction, the event is dispatched on the **transactional dispatcher**
   (:class:`harp.unit_of_work.TransactionalEventDispatcher`, available in the container), a second dispatcher distinct
   from the main one. Only listeners attached to it run there, and their writes join the commit: if one fails, the
   unit of work rolls back and the action fails. Storage's ``current_session()`` gives such a listener the session of
   the running unit of work.
2. After the commit, the same event is dispatched on the main dispatcher, for every other listener. A failure there is
   logged and undoes nothing.

An auditable event derives from :class:`harp.unit_of_work.audit.AuditableEvent` and carries an ``actor``, a ``target``,
an ``outcome`` and a ``details`` dict, which the :doc:`audit application </apps/audit/index>` records. A transactional
listener attached to ``harp.unit_of_work.ANY_EVENT`` receives every recorded event, and ``uow.after_commit(callback)``
runs a callback once the commit is done.

Only the ``details_fields`` an auditable event declares are recorded, and only as scalars or lists of scalars. The event
author declares which fields are safe: values are not inspected, so a declared field must never carry a credential (ids,
names, prefixes and scopes only).

``record`` refuses an event that is not ``auditable``. Mark an event ``loggable`` instead when it deserves a structured
log line but no audit row; it is dispatched on the main dispatcher as usual. An unmarked event is neither.

An action outside the database goes through ``uow.act``: record the event, act, and the commit comes last. A failing
action leaves nothing. A commit failing after the action calls the compensation given to ``act``, or logs a critical
error when there is none.

.. code-block:: python

    async with self.unit_of_work() as uow:
        await uow.record(RemoteDisabled(...))
        await uow.act(remote.disable, compensation=remote.enable)


See Also
::::::::

:doc:`All pages tagged with «events» </_tags/events>` (includes this page and all event reference pages).
