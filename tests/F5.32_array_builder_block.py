#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies Array Builder block behavior in direct and runtime execution.
# File Name: F5.32_array_builder_block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-07-07
# -----------------------------------------------------------------------------

"""F5.32 - Array Builder block.

The test validates that Array Builder turns several incoming runtime values into
one JSON array and stays compatible with centralized and zeromq_active runs.
"""

# Test cases:
# - FB1/FB2/FB3 - Direct execution collects input events and converts auto-typed values into a JSON array.
# - FB4 - Strict number mode rejects non-numeric values with a structured failure.
# - FB5 - Modal, inspector, and node card are rendered by block-owned HTML.
# - FB1/FB2/FB3 - Runtime execution receives two connected sources and emits the same JSON array in centralized and zeromq_active modes.

from pathlib import Path
from types import SimpleNamespace
import json
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
TESTS_DIR = ROOT_DIR / "tests"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from ui_smoke_common import (  # noqa: E402
    create_run_api,
    data_edge,
    display_node,
    expect,
    graph_payload,
    isolated_server,
    text_node,
    wait_for_run_terminal,
)

from blocs.array_builder.block import ArrayBuilderBlock  # noqa: E402
from bloxsmith_app.block_runtime import BlockInputEvent, BlockRuntimeContext  # noqa: E402
from bloxsmith_app.block_ui import render_block_inspector_panel, render_block_modal, render_block_node_card  # noqa: E402
from bloxsmith_app.port_requirements import REQUIRED_FOR_EXECUTION  # noqa: E402


def array_builder_node(*, mode: str = "auto") -> dict:
    """Return a graph node payload for Array Builder runtime checks."""

    return {
        "id": "array-builder-1",
        "kind": "array_builder",
        "title": "Array Builder",
        "position": {"x": 420, "y": 160},
        "inputs": [
            {
                "id": 1,
                "name": "items",
                "title": "Items",
                "accepts": ["application/json", "text/plain", "message/*"],
                "multiplicity": "many",
                "required": True,
                "execution_requirement": REQUIRED_FOR_EXECUTION,
            }
        ],
        "outputs": [
            {
                "id": 1,
                "name": "array",
                "title": "Array",
                "emits": ["application/json", "message/*"],
                "multiplicity": "many",
            }
        ],
        "config": {"mode": mode},
    }


def direct_context(*, mode: str, events: tuple[BlockInputEvent, ...]) -> BlockRuntimeContext:
    """Build a direct runtime context for Array Builder unit checks."""

    return BlockRuntimeContext(
        run_id="unit-run",
        node_id="array-builder-unit",
        kind="array_builder",
        title="Array Builder Unit",
        config={"mode": mode},
        inputs={},
        input_content_types={},
        input_message="",
        input_ports=(SimpleNamespace(id=1, name="items", execution_requirement=REQUIRED_FOR_EXECUTION),),
        output_ports=(SimpleNamespace(id=1, name="array"),),
        input_events=events,
        root_dir=ROOT_DIR,
    )


def item_event(edge_id: str, value: str, *, source_node_id: str) -> BlockInputEvent:
    """Return one input event targeting the Array Builder items input."""

    return BlockInputEvent(
        edge_id=edge_id,
        input_port_id=1,
        input_port_name="items",
        source_node_id=source_node_id,
        source_port_id=1,
        value=value,
        content_type="text/plain",
    )


def test_direct_execution() -> None:
    """Validate direct conversion modes without starting the HTTP server."""

    block = ArrayBuilderBlock()
    result = block.execute_runtime(
        direct_context(
            mode="auto",
            events=(
                item_event("edge-a", "hello", source_node_id="text-a"),
                item_event("edge-b", "42", source_node_id="text-b"),
                item_event("edge-c", '{"name":"demo"}', source_node_id="text-c"),
            ),
        )
    )
    expect(result.status == "success", "Array Builder auto must succeed.")
    parsed = json.loads(result.outputs[0].value)
    expect(parsed == ["hello", 42, {"name": "demo"}], "Array Builder auto does not parse the items correctly.")
    expect(result.metadata.get("array_builder", {}).get("item_count") == 3, "The item_count metadata is wrong.")

    number_failure = block.execute_runtime(
        direct_context(
            mode="number",
            events=(item_event("edge-a", "not-a-number", source_node_id="text-a"),),
        )
    )
    expect(number_failure.status == "failed", "Array Builder number must fail on a non-numeric value.")
    expect("invalid numeric item" in str(number_failure.error), "The number mode error is not explicit enough.")


def test_block_ui() -> None:
    """Validate block-owned modal, inspector, and node-card rendering."""

    node = array_builder_node(mode="json")
    modal_html = str(render_block_modal("array_builder", {"node": node, "runtime": {}}).get("html") or "")
    inspector_html = str(render_block_inspector_panel("array_builder", {"node": node}).get("html") or "")
    card_html = str(render_block_node_card("array_builder", {"node": node}).get("html") or "")

    expect('data-block-config-field="mode"' in modal_html, "Le modal doit exposer le mode via le binding générique.")
    expect('<option value="json" selected>' in modal_html, "Le modal doit sélectionner le mode JSON.")
    expect('data-block-config-field="mode"' in inspector_html, "L'inspector doit exposer le mode.")
    expect("Items -&gt; JSON array" in card_html, "La node-card doit afficher le rôle du bloc.")


def run_runtime_case(runtime_mode: str) -> None:
    """Run text -> Array Builder -> display through the public run API."""

    with isolated_server() as server:
        document = graph_payload(
            f"F5 Array Builder {runtime_mode}",
            [
                text_node("text-a", "Text A", "42", 80, 80),
                text_node("text-b", "Text B", '{"name":"demo"}', 80, 240),
                array_builder_node(mode="auto"),
                display_node("display-1", "Display", 760, 160),
            ],
            [
                data_edge("edge-a-array", "text-a", 1, "array-builder-1", 1),
                data_edge("edge-b-array", "text-b", 1, "array-builder-1", 1),
                data_edge("edge-array-display", "array-builder-1", 1, "display-1", 1),
            ],
        )
        created = create_run_api(server, document, runtime_mode=runtime_mode)
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=20)
        expect(run.get("status") == "success", f"The Array Builder {runtime_mode} run must succeed.")
        output = run.get("output_values", {}).get("array-builder-1:1", {}).get("value")
        expect(json.loads(output or "[]") == [42, {"name": "demo"}], f"Sortie Array Builder incorrecte en {runtime_mode}.")
        expect(
            run.get("results", {}).get("array-builder-1", {}).get("array_builder", {}).get("item_count") == 2,
            f"Metadata Array Builder incorrecte en {runtime_mode}.",
        )
        if runtime_mode == "zeromq_active":
            expect(
                run.get("results", {}).get("array-builder-1", {}).get("transport") == "zeromq_active",
                "Array Builder doit être exécuté via zeromq_active.",
            )


def main() -> None:
    test_direct_execution()
    test_block_ui()
    run_runtime_case("centralized")
    run_runtime_case("zeromq_active")
    print("[ok] F5.32_array_builder_block")


if __name__ == "__main__":
    main()
