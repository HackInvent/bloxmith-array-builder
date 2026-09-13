# -----------------------------------------------------------------------------
# Role: Builds a JSON array from all values received on one multi input.
# File Name: block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-07-07
# -----------------------------------------------------------------------------

from __future__ import annotations

from html import escape
from typing import Any
import json

from bloxsmith_app.block_api import (
    APPLICATION_JSON,
    BlockDefinition,
    BlockRuntimeContext,
    BlockRuntimeOutput,
    BlockRuntimeResult,
    render_inspector_template,
    render_node_card_template,
    TEXT_PLAIN,
)


ARRAY_BUILDER_MODES = ("auto", "text", "number", "json")


# Functional behavior:
# FB1 - Collect every runtime value received on the required many input as one array item.
# FB2 - Convert each item according to mode: auto, text, number, or json.
# FB3 - Emit one JSON array on every declared output port.
# FB4 - Fail clearly when strict modes number/json receive an invalid item.
# FB5 - Render block-owned node card, modal, and inspector panel without framework-specific business logic.
class ArrayBuilderBlock(BlockDefinition):
    """Autonomous block that converts multiple incoming values into one JSON array."""

    kind = "array_builder"

    def ui_assets(self, surface: str = "modal") -> list[dict[str, str]]:
        """Return block-owned frontend assets for the requested UI surface."""

        if surface == "modal":
            return [{"kind": "js", "path": "assets/js/block_modal.js"}]
        return []

    def render_node_card(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the Array Builder canvas card body."""

        mode = self.normalize_mode((node.get("config") or {}).get("mode") if isinstance(node.get("config"), dict) else "")
        return render_node_card_template(
            block=self,
            node=node,
            node_classes=["array-builder-node"],
            replacements={
                "title": node.get("title") or self.default_title(),
                "preview": "Items -> JSON array",
                "mode": f"mode: {mode}",
            },
        )

    def render_inspector_panel(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the block-owned inspector with the array conversion mode."""

        mode = self.normalize_mode((node.get("config") or {}).get("mode") if isinstance(node.get("config"), dict) else "")
        template = (self.directory / "inspector_panel.html").read_text(encoding="utf-8")
        html = render_inspector_template(
            template=template,
            node={**node, "type": self.kind, "kind": self.kind},
            payload=payload,
            replacements={
                "mode_options": self._mode_options_html(mode),
                "description": escape("Construit un tableau JSON avec une entrée par valeur reçue sur le port Items."),
            },
        )
        return {"html": html, "context": {"node_id": str(node.get("id") or ""), "mode": mode, "full_panel": True}}

    def render_modal(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the block-owned modal from the local template."""

        mode = self.normalize_mode((node.get("config") or {}).get("mode") if isinstance(node.get("config"), dict) else "")
        template = (self.directory / "block_modal.html").read_text(encoding="utf-8")
        html = self._render_generic_modal_template(template=template, node=node, payload=payload or {})
        html = html.replace("{{ mode_options }}", self._mode_options_html(mode))
        html = html.replace(
            "{{ mode_help }}",
            escape("auto parse JSON/nombres si possible; text garde le texte; number/json sont stricts."),
        )
        return {"html": html, "context": {"node_id": str(node.get("id") or ""), "node_kind": self.kind, "mode": mode}}

    def normalize_mode(self, value: Any) -> str:
        """Return a supported conversion mode, defaulting to auto.

        Args:
            value: Raw mode value from node configuration.
        """

        mode = str(value or "").strip().lower()
        return mode if mode in ARRAY_BUILDER_MODES else "auto"

    def collect_values(self, context: BlockRuntimeContext) -> list[str]:
        """Return runtime values to append to the output array.

        Args:
            context: Generic runtime context carrying input attributes and provenance events.
        """

        event_values = [
            str(event.value if event.value is not None else "")
            for event in getattr(context, "input_events", ())
            if int(getattr(event, "input_port_id", 0) or 0) == 1
            or str(getattr(event, "input_port_name", "") or "").strip().lower() == "items"
        ]
        if event_values:
            return event_values
        raw_value = str(context.input_value("items", "1", default=context.input_message) or "")
        if not raw_value:
            return []
        return raw_value.split("\n\n")

    def convert_item(self, value: Any, *, mode: str) -> Any:
        """Convert one received value according to the configured array mode.

        Args:
            value: Raw item value received by the input port.
            mode: Normalized conversion mode.
        """

        if mode == "text":
            return "" if value is None else str(value)
        if mode == "number":
            return self._parse_number(value)
        if mode == "json":
            return self._parse_json(value)
        return self._parse_auto(value)

    def execute_runtime(self, context: BlockRuntimeContext) -> BlockRuntimeResult:
        """Build and emit the JSON array for the current runtime batch."""

        mode = self.normalize_mode(context.config.get("mode"))
        raw_values = self.collect_values(context)
        try:
            array_items = [self.convert_item(value, mode=mode) for value in raw_values]
        except ValueError as exc:
            message = str(exc)
            return BlockRuntimeResult(
                status="failed",
                outputs=[],
                logs=[f"[array-builder-error] {context.node_id}: {message}"],
                error=message,
                exit_code=1,
                last_message=message,
                content_type=TEXT_PLAIN,
                worker_received="-",
            )

        payload = json.dumps(array_items, ensure_ascii=False, indent=2)
        outputs = [
            BlockRuntimeOutput(
                port_id=int(getattr(port, "id", 0) or 0),
                port_name=str(getattr(port, "name", "") or ""),
                value=payload,
                content_type=APPLICATION_JSON,
            )
            for port in context.output_ports
        ]
        summary = f"{len(array_items)} item(s), mode {mode}"
        return BlockRuntimeResult(
            status="success",
            outputs=outputs,
            logs=[f"[array-builder] {context.node_id}: {summary}."],
            last_message=payload,
            content_type=APPLICATION_JSON,
            worker_received=summary,
            metadata={"array_builder": {"item_count": len(array_items), "mode": mode}},
        )

    def _parse_auto(self, value: Any) -> Any:
        """Parse JSON-looking text while preserving plain strings."""

        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return ""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value

    def _parse_json(self, value: Any) -> Any:
        """Parse one item as strict JSON or raise a clear ValueError."""

        if not isinstance(value, str):
            return value
        try:
            return json.loads(value.strip())
        except json.JSONDecodeError as exc:
            raise ValueError(f"item JSON invalide: {value[:80]}") from exc

    def _parse_number(self, value: Any) -> int | float:
        """Parse one item as a JSON number and reject booleans/objects."""

        try:
            parsed = self._parse_json(value)
        except ValueError as exc:
            raise ValueError(f"item numérique invalide: {str(value)[:80]}") from exc
        if isinstance(parsed, bool) or not isinstance(parsed, (int, float)):
            raise ValueError(f"item numérique invalide: {str(value)[:80]}")
        return parsed

    def _mode_options_html(self, selected_mode: str) -> str:
        """Render the conversion mode select options."""

        labels = {
            "auto": "Auto",
            "text": "Text",
            "number": "Number",
            "json": "JSON",
        }
        return "\n".join(
            f'<option value="{escape(mode, quote=True)}"{" selected" if mode == selected_mode else ""}>'
            f"{escape(label)}</option>"
            for mode, label in labels.items()
        )
