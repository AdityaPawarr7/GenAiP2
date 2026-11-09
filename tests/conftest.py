"""Shared pytest setup.

Registers the `ac` marker for tests whose name does not carry their acceptance criterion
(e.g. @pytest.mark.ac("AC3.1")). The marker value is written into the junit XML as a test
property, so scripts/run_validation.py can map the test to its AC. Tests named
test_ACx_y_... are mapped by name and need no marker.
"""


def pytest_configure(config):
    config.addinivalue_line("markers", 'ac(id): the acceptance criterion a test checks, e.g. ac("AC3.1")')


def pytest_collection_modifyitems(items):
    for item in items:
        for m in item.iter_markers(name="ac"):
            if m.args:
                item.user_properties.append(("ac", m.args[0]))
