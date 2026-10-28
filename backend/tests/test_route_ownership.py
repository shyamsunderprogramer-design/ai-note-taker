"""A path/method must have one runtime owner and one matching OpenAPI contract."""
def test_no_duplicate_registered_routes():
    from core.main import app
    owners = {}
    duplicates = []
    for route in app.routes:
        for method in getattr(route, 'methods', ()) or ():
            key = (method, route.path)
            name = route.endpoint.__module__ + '.' + route.endpoint.__name__
            if key in owners:
                duplicates.append((key, owners[key], name))
            owners[key] = name
    assert not duplicates, duplicates
