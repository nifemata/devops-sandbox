from app.main import add, app


def test_add():
    assert add(2, 3) == 5


def test_index_reports_course():
    # Lab 01, Part B6: this field does not exist yet. Make the test pass the right way.
    body = app.test_client().get("/").get_json()
    assert body["course"] == "DevOps Lab"
