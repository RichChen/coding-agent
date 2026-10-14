from todo import add_item, completed_items


def test_add_item_defaults_to_not_done():
    items = add_item([], "write tests")
    assert items == [{"text": "write tests", "done": False}]


def test_completed_items_filters_done_items():
    items = [
        {"text": "a", "done": True},
        {"text": "b", "done": False},
        {"text": "c", "done": True},
    ]
    assert completed_items(items) == ["a", "c"]
