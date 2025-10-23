Serializer Enhancements
=======================

The serializer now understands dot-delimited paths that step through
attributes, mappings, lists, and JSON encoded strings. This enables
referencing deeply nested data in configuration files without custom
post-processing.

Dot-Path Resolution
-------------------

Paths such as ``text.results.0.id`` are resolved segment by segment:

* ``text`` is looked up via attribute or mapping access
* if the current value is a JSON string, it is decoded automatically
* list segments accept numeric indices (``0``)
* the final segment (``id``) returns the value when present

If at any point a segment is missing, the resolver returns ``None``.

Array Limiting
--------------

When using the dictionary form of field definitions, ``limit`` restricts
the number of items returned from list results:

.. code-block:: toml

   [serializers.search_serializer]
   [serializers.search_serializer.fields]
   id = "text.results.0.id"
   results = { path = "text.results", limit = 1 }

With the Context7 search API this yields the first result alongside its
identifier, allowing responses to be trimmed directly within the
serializer configuration.
