from lineage.lineage_service import get_all_lineage_edges, get_table_lineage


def test_get_all_lineage_edges_normalizes_upstream_and_downstream():
    lineage_config = {
        "customers": {
            "description": "Customer master table",
            "primary_key": "customer_id",
            "downstream": [
                {
                    "table": "orders",
                    "relationship": "customers.customer_id -> orders.customer_id",
                    "relationship_type": "foreign_key",
                }
            ],
        },
        "orders": {
            "description": "Order table",
            "primary_key": "order_id",
            "upstream": [
                {
                    "table": "customers",
                    "relationship": "orders.customer_id -> customers.customer_id",
                    "relationship_type": "foreign_key",
                }
            ],
        },
    }

    edges = get_all_lineage_edges(lineage_config)

    assert len(edges) == 1
    assert edges[0]["source_table"] == "customers"
    assert edges[0]["source_column"] == "customer_id"
    assert edges[0]["target_table"] == "orders"
    assert edges[0]["target_column"] == "customer_id"


def test_get_table_lineage_returns_upstream_and_downstream_edges():
    lineage_config = {
        "customers": {
            "description": "Customer master table",
            "primary_key": "customer_id",
            "downstream": [
                {
                    "table": "orders",
                    "relationship": "customers.customer_id -> orders.customer_id",
                    "relationship_type": "foreign_key",
                }
            ],
        },
        "orders": {
            "description": "Order table",
            "primary_key": "order_id",
        },
    }

    table_lineage = get_table_lineage("orders", lineage_config)

    assert table_lineage["table_name"] == "orders"
    assert len(table_lineage["upstream"]) == 1
    assert table_lineage["upstream"][0]["source_table"] == "customers"
    assert table_lineage["downstream"] == []
