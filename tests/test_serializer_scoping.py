from apiout.fetcher import resolve_serializer


def test_resolve_serializer_inline_dict():
    """Test that inline dict has highest priority"""
    api_config = {"serializer": {"fields": {"inline": "value"}}}
    global_serializers = {"generic": {"fields": {"global": "value"}}}

    result = resolve_serializer(api_config, global_serializers)

    assert result == {"fields": {"inline": "value"}}


def test_resolve_serializer_explicit_dotted_reference():
    """Test that explicit dotted references (client.serializer) work"""
    api_config = {"serializer": "btc_price.price_data"}
    global_serializers = {
        "btc_price.price_data": {"fields": {"usd": "usd_price"}},
        "price_data": {"fields": {"wrong": "field"}},
    }

    result = resolve_serializer(api_config, global_serializers)

    assert result == {"fields": {"usd": "usd_price"}}


def test_resolve_serializer_client_scoped_lookup():
    """Test that client_ref scopes the serializer lookup"""
    api_config = {"serializer": "price_data", "client": "btc_price"}
    global_serializers = {
        "btc_price.price_data": {"fields": {"usd": "usd_price"}},
        "price_data": {"fields": {"generic": "field"}},
    }

    result = resolve_serializer(api_config, global_serializers, client_ref="btc_price")

    assert result == {"fields": {"usd": "usd_price"}}


def test_resolve_serializer_global_fallback():
    """Test that global lookup works when client-scoped not found"""
    api_config = {"serializer": "price_data", "client": "btc_price"}
    global_serializers = {
        "price_data": {"fields": {"generic": "field"}},
    }

    result = resolve_serializer(api_config, global_serializers, client_ref="btc_price")

    assert result == {"fields": {"generic": "field"}}


def test_resolve_serializer_empty_when_not_found():
    """Test that empty dict is returned when serializer not found"""
    api_config = {"serializer": "nonexistent", "client": "some_client"}
    global_serializers = {}

    result = resolve_serializer(
        api_config, global_serializers, client_ref="some_client"
    )

    assert result == {}


def test_resolve_serializer_priority_order():
    """Test that resolution order is correct: inline > dotted > scoped > global"""
    # Test that inline beats all
    api_config = {"serializer": {"fields": {"inline": "wins"}}, "client": "test"}
    global_serializers = {
        "test.my_ser": {"fields": {"scoped": "loses"}},
        "my_ser": {"fields": {"global": "loses"}},
    }

    result = resolve_serializer(api_config, global_serializers, client_ref="test")
    assert result == {"fields": {"inline": "wins"}}

    # Test that dotted beats scoped
    api_config = {"serializer": "other.my_ser", "client": "test"}
    global_serializers = {
        "other.my_ser": {"fields": {"dotted": "wins"}},
        "test.my_ser": {"fields": {"scoped": "loses"}},
        "my_ser": {"fields": {"global": "loses"}},
    }

    result = resolve_serializer(api_config, global_serializers, client_ref="test")
    assert result == {"fields": {"dotted": "wins"}}

    # Test that scoped beats global
    api_config = {"serializer": "my_ser", "client": "test"}
    global_serializers = {
        "test.my_ser": {"fields": {"scoped": "wins"}},
        "my_ser": {"fields": {"global": "loses"}},
    }

    result = resolve_serializer(api_config, global_serializers, client_ref="test")
    assert result == {"fields": {"scoped": "wins"}}


def test_resolve_serializer_no_client_ref():
    """Test that it works without client_ref (backward compatibility)"""
    api_config = {"serializer": "generic"}
    global_serializers = {
        "generic": {"fields": {"value": "data"}},
    }

    result = resolve_serializer(api_config, global_serializers)

    assert result == {"fields": {"value": "data"}}


def test_resolve_serializer_no_serializer_in_config():
    """Test that empty dict is returned when no serializer in config"""
    api_config = {}
    global_serializers = {"generic": {"fields": {"value": "data"}}}

    result = resolve_serializer(api_config, global_serializers, client_ref="test")

    assert result == {}
