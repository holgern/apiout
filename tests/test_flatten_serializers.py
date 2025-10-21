from apiout.cli import _flatten_serializers


def test_flatten_serializers_global_only():
    """Test that global serializers (with 'fields') remain at top level"""
    serializers = {
        "generic": {"fields": {"value": "data"}},
        "another": {"fields": {"key": "val"}},
    }

    result = _flatten_serializers(serializers)

    assert result == {
        "generic": {"fields": {"value": "data"}},
        "another": {"fields": {"key": "val"}},
    }


def test_flatten_serializers_nested_only():
    """Test that nested serializers get flattened with dotted keys"""
    serializers = {
        "btc_price": {
            "price_data": {"fields": {"usd": "usd_price"}},
            "other": {"fields": {"value": "data"}},
        },
    }

    result = _flatten_serializers(serializers)

    assert result == {
        "btc_price.price_data": {"fields": {"usd": "usd_price"}},
        "btc_price.other": {"fields": {"value": "data"}},
    }


def test_flatten_serializers_mixed():
    """Test that global and nested serializers work together"""
    serializers = {
        "generic": {"fields": {"value": "data"}},
        "btc_price": {
            "price_data": {"fields": {"usd": "usd_price"}},
            "volume": {"fields": {"vol": "volume"}},
        },
        "mempool": {
            "block_data": {"fields": {"hash": "block_hash"}},
        },
        "another_global": {"fields": {"key": "val"}},
    }

    result = _flatten_serializers(serializers)

    assert result == {
        "generic": {"fields": {"value": "data"}},
        "btc_price.price_data": {"fields": {"usd": "usd_price"}},
        "btc_price.volume": {"fields": {"vol": "volume"}},
        "mempool.block_data": {"fields": {"hash": "block_hash"}},
        "another_global": {"fields": {"key": "val"}},
    }


def test_flatten_serializers_empty():
    """Test that empty dict returns empty dict"""
    serializers = {}

    result = _flatten_serializers(serializers)

    assert result == {}


def test_flatten_serializers_unexpected_format():
    """Test that unexpected formats are kept as-is"""
    serializers = {
        "normal": {"fields": {"value": "data"}},
        "string_value": "unexpected",
        "number_value": 42,
    }

    result = _flatten_serializers(serializers)

    assert result == {
        "normal": {"fields": {"value": "data"}},
        "string_value": "unexpected",
        "number_value": 42,
    }
