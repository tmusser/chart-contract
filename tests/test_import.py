from chart_contract import Chart, audit_spec


def test_imports_public_api() -> None:
    assert Chart is not None
    assert audit_spec is not None
