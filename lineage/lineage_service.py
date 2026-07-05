"""Service functions for table-level data lineage."""

from __future__ import annotations

from typing import Any

from lineage.lineage_loader import load_lineage_config


def _parse_table_column(endpoint: str) -> tuple[str | None, str | None]:
    """Parse a `table.column` endpoint from lineage relationship text."""

    endpoint = str(endpoint).strip()

    if "." not in endpoint:
        return endpoint or None, None

    table_name, column_name = endpoint.split(".", 1)
    return table_name.strip() or None, column_name.strip() or None


def _parse_relationship(relationship: str | None) -> tuple[dict[str, str | None], dict[str, str | None]]:
    """Parse `source.table_column -> target.table_column` relationship text."""

    if not relationship or "->" not in str(relationship):
        return (
            {"table": None, "column": None},
            {"table": None, "column": None},
        )

    left, right = str(relationship).split("->", 1)
    left_table, left_column = _parse_table_column(left)
    right_table, right_column = _parse_table_column(right)

    return (
        {"table": left_table, "column": left_column},
        {"table": right_table, "column": right_column},
    )


def _fallback_column(table_config: dict[str, Any], endpoint: dict[str, str | None]) -> str | None:
    """Prefer parsed relationship column, then table primary key."""

    return endpoint.get("column") or table_config.get("primary_key")


def _build_edge(
    current_table: str,
    current_config: dict[str, Any],
    relationship_config: dict[str, Any],
    direction: str,
) -> dict[str, Any]:
    """Build a normalized lineage edge from an upstream/downstream entry."""

    related_table = relationship_config.get("table")
    relationship = relationship_config.get("relationship")
    left, right = _parse_relationship(relationship)

    if direction == "upstream":
        source_endpoint = left if left.get("table") == related_table else right
        target_endpoint = left if left.get("table") == current_table else right
        source_table = source_endpoint.get("table") or related_table
        target_table = target_endpoint.get("table") or current_table
    else:
        source_endpoint = left if left.get("table") == current_table else right
        target_endpoint = left if left.get("table") == related_table else right
        source_table = source_endpoint.get("table") or current_table
        target_table = target_endpoint.get("table") or related_table

    return {
        "source_table": source_table,
        "source_column": _fallback_column(current_config, source_endpoint),
        "target_table": target_table,
        "target_column": target_endpoint.get("column"),
        "relationship_type": relationship_config.get("relationship_type", "lineage"),
        "description": relationship_config.get("description", ""),
        "relationship": relationship,
        "declared_on_table": current_table,
        "direction": direction,
    }


def _edge_key(edge: dict[str, Any]) -> tuple[Any, ...]:
    """Return a stable key for de-duplicating lineage edges."""

    return (
        edge.get("source_table"),
        edge.get("source_column"),
        edge.get("target_table"),
        edge.get("target_column"),
        edge.get("relationship_type"),
    )


def get_all_lineage_edges(
    lineage_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all configured lineage relationships as normalized edges."""

    lineage_config = lineage_config or load_lineage_config()
    edges_by_key: dict[tuple[Any, ...], dict[str, Any]] = {}

    for table_name, table_config in lineage_config.items():
        if not isinstance(table_config, dict):
            continue

        for relationship_config in table_config.get("downstream", []) or []:
            if not isinstance(relationship_config, dict):
                continue
            edge = _build_edge(
                table_name,
                table_config,
                relationship_config,
                direction="downstream",
            )
            edges_by_key[_edge_key(edge)] = edge

        for relationship_config in table_config.get("upstream", []) or []:
            if not isinstance(relationship_config, dict):
                continue
            edge = _build_edge(
                table_name,
                table_config,
                relationship_config,
                direction="upstream",
            )
            edges_by_key[_edge_key(edge)] = edge

    return sorted(
        edges_by_key.values(),
        key=lambda edge: (
            str(edge.get("source_table")),
            str(edge.get("target_table")),
            str(edge.get("source_column")),
        ),
    )


def get_table_lineage(
    table_name: str,
    lineage_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return lineage metadata and related edges for one table."""

    lineage_config = lineage_config or load_lineage_config()
    table_config = lineage_config.get(table_name, {})
    edges = get_all_lineage_edges(lineage_config)

    upstream_edges = [
        edge for edge in edges
        if edge.get("target_table") == table_name
    ]
    downstream_edges = [
        edge for edge in edges
        if edge.get("source_table") == table_name
    ]

    return {
        "table_name": table_name,
        "description": table_config.get("description", ""),
        "primary_key": table_config.get("primary_key"),
        "upstream": upstream_edges,
        "downstream": downstream_edges,
    }
