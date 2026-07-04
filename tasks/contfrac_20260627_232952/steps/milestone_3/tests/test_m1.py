from conftest import check


class TestMilestone1:
    def test_m1_cf(self):
        check("m1_cf")
    def test_m1_errors(self):
        check("m1_errors")
    def test_m1_value(self):
        check("m1_value")
