def test_app_module_exports_factory():
    from solo_harness.main import create_app
    app = create_app()
    assert app.title == "SOLO Harness"
