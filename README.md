# Array Builder

<!-- block-metadata:start -->
[![Block version: 0.1.0](https://img.shields.io/badge/block-0.1.0-blue)](model.json)
[![BloxSmith compatibility: 1.0.9](https://img.shields.io/badge/BloxSmith-1.0.9-brightgreen)](compatibility.json)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Verified BloxSmith versions: **1.0.9** (bundled-block tests; see [test evidence](compatibility.json)).
<!-- block-metadata:end -->


## Purpose

Build a JSON array from every value received on the `items` input. Use this block when several upstream blocks must feed one runtime list.

Unlike the static List block, Array Builder collects runtime messages. Unlike Merge, it produces a JSON array rather than concatenated text.

## Ports

- **Input `items`**: multiplicity `many`, required for execution. The runtime waits for all non-feedback data connections on this input before executing.
- **Output `array`**: a raw JSON array with content type `application/json`.

## Configuration

| `mode` | Behavior |
| --- | --- |
| `auto` | Parse each value as JSON; keep the original text if parsing fails. |
| `text` | Keep every value as text. |
| `number` | Require every value to be a valid JSON number. |
| `json` | Require every value to be valid JSON. |

## Example

Given three upstream messages:

```text
hello
42
{"name":"demo"}
```

In `auto` mode, the output is:

```json
[
  "hello",
  42,
  {"name": "demo"}
]
```

## Constraints

Invalid values fail explicitly in `number` and `json` modes. Item order follows the deterministic input-event order supplied by the runtime. The array has no `{"item": ...}` wrapper; Iterator accepts this format.

Strict modes reject `NaN`, `Infinity`, `-Infinity` and numeric overflow such as
`1e999`, including non-finite values nested in JSON. In `auto` mode these inputs
stay as their original text. Every successful output is valid JSON; an invalid
strict conversion emits no output. The block-owned suite verifies both runtime
modes with bundled, managed and linked packages against the current Studio.

## Compatibility policy

[compatibility.json](compatibility.json) records HackInvent's verified BloxSmith versions and test evidence. Only the versions listed above have been verified, using the block-owned suites in a **bundled-block test installation**. This is not a certification of managed-package installation, every browser/OS, or live provider availability. Other framework versions are unverified, not necessarily incompatible.

The block-version badge follows `model.json`, not a published Git tag. `unversioned` means that no block release version is declared; no number is inferred from the framework version. The framework still uses `model.json` for its runtime/install contract; the tester-owned JSON does not replace it. Official integration tests run in the private `bloxmith-blocs` workspace. Test helpers and the proprietary framework are not bundled in this public block repository.

## Properties ergonomics

Modal and inspector styles are owned by this package and scoped to its exact
release. Forms adapt to narrow panels, checkboxes stay beside their labels, and
long values do not widen the inspector. Existing labels are associated with
controls; keyboard navigation complements the block’s own tab handlers.
These presentation helpers do not change port bindings, authored settings,
runtime behavior or the block’s original surface cleanup.
