Event Dispatcher
================

To provide a flexible way to hook into the existing and future components, HARP uses an event-driven architecture.

.. eda:

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

Defining and exposing Events
::::::::::::::::::::::::::::

An event is usually just a symbolic name (as a :func:`str`) that represents something happening in the system. If your
an event is also associated with some context that the listeners might be interested in, you can associate it with a
custom :class:`whistle.Event` class that will serve as an envelope for this context.

.. code-block:: python

    import asyncio
    from whistle import Event, AsyncEventDispatcher

    class MyEvent(Event):
        def __init__(self, context):
            super().__init__()
            self.context = context

    async def main(dispatcher: IAsyncEventDispatcher):
        event = dispatcher.adispatch('my.event', MyEvent({'foo': 'bar'}))

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

    if __name__ == '__main__':
        dispatcher = AsyncEventDispatcher()
        dispatcher.add_listener(MY_EVENT, my_listener)

        event = dispatcher.adispatch(MY_EVENT, MyEvent({'foo': 'bar'}))

        asyncio.run(event)

Once again, this is an isolated class. A real-world application would register the listener with the system-wide
event dispatcher, so it can listen to events from any component registered with the same dispatcher:

.. code-block:: python

    class MyEventListener:
        def __init__(self, dispatcher: IAsyncEventDispatcher):
            self.dispatcher = dispatcher
            self.dispatcher.add_listener(MY_EVENT, self.handle)

        async def handle(self, event: MyEvent):
            print(event.context)


Event List
::::::::::

In HARP Proxy (CE), there are a few applications that expose events, here is a list of the most important ones:

- :doc:`Events dispatched by HARP Core <../core/events>`
- :doc:`Events dispatched by the Dashboard Application <../apps/dashboard/events>`
