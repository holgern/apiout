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
* final segment (``id``) returns the value when present

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

List Item Serialization
-----------------------

Lists extracted through ``path`` or method lookups can apply serializers
to each item with ``item_fields`` or ``item_serializer``. This is useful
when each element requires its own field mapping:

.. code-block:: toml

   [serializers.people]
   [serializers.people.fields]
   contacts = { path = "items", item_fields = { name = "name", age = "age" } }

   # or reuse an existing serializer definition
   enriched = { path = "items", item_serializer = { fields = { name = "name" } } }

Each element is mapped individually, producing a list of structured
objects in the final output.

JSON Parsing
------------

The ``parse_json`` parameter provides explicit control over JSON parsing
for fields containing JSON strings. This is useful when you need to
parse JSON data but want to control when and how it's parsed:

.. code-block:: toml

   [serializers.api_serializer]
   [serializers.api_serializer.fields]
   raw_text = "text"
   parsed_data = { path = "text", parse_json = true }
   first_item = { path = "text.items", parse_json = true, limit = 1 }

* ``raw_text`` returns the original JSON string
* ``parsed_data`` returns the parsed JSON object
* ``first_item`` parses JSON and extracts the first item from the array

The ``parse_json`` parameter is applied to the first segment of the path,
allowing subsequent path navigation through the parsed JSON structure.

Hidden Fields
-------------

The ``hidden`` parameter allows fields to be processed but excluded from
the final output. This is useful for intermediate data that should be
available to other field mappings but not included in the result:

.. code-block:: toml

   [serializers.context7_serializer]
   [serializers.context7_serializer.fields]
   ok = "ok"
   status_code = "status_code"
   text = { path = "text", parse_json = true, hidden = true }
   url = "url"
   results = { path = "text.snippets", limit = 1 }

In this example:

* ``text`` is parsed as JSON but hidden from output
* ``results`` can access the parsed ``text`` data to extract snippets
* The final output contains ``ok``, ``status_code``, ``url``, and ``results``

Hidden fields are processed in the first pass to build the complete context,
then excluded from the final result in the second pass.

Key Serialization
-----------------

Dictionary and mapping keys that are not native JSON types (for example,
``pandas.Timestamp``) are automatically converted to ISO strings when
possible, falling back to ``str(key)``. This guarantees compatibility with
``--json`` CLI output while preserving readable keys.
