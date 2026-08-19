from run_v10 import dashboard_is_external


def test_dashboard_external_flag_is_strictly_opt_in():
    assert dashboard_is_external("true") is True
    assert dashboard_is_external("ON") is True
    assert dashboard_is_external("false") is False
    assert dashboard_is_external("") is False
    assert dashboard_is_external("unexpected") is False
