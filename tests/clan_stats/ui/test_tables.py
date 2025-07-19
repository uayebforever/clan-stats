from typing_extensions import NamedTuple

from clan_stats.ui.tables import TableBuilder


def test_table_builder():
    class DataObject(NamedTuple):
        name: str
        number: int

    tb = TableBuilder()

    @tb.add_column(name="Name")
    def name_column(r: DataObject) -> str:
        return r.name

    @tb.add_column(name="Name and Number")
    def other(r: DataObject) -> str:
        return f"{r.name}  {r.number}"

    source = [
        DataObject("Bob", 2345),
        DataObject("Paul", 2383)
    ]

    result = tb.build(source)

    assert result == "\n".join([
        "Name    Name and Number",
        "Bob     Bob  2345",
        "Paul    Paul  2383"
    ])

    index_result = tb.build_indexed(source)

    assert index_result == "\n".join([
        "    Name    Name and Number",
        " 1  Bob     Bob  2345",
        " 2  Paul    Paul  2383"
    ])
