// -----------------------------------------------------------------------------
// Role: Owns Array Builder modal behavior hooks.
// File Name: block_modal.js
// Author: Alexandre EL
// Email: alex@hackinvent.com
// Created Date: 2026-07-07
// -----------------------------------------------------------------------------

(() => {
  /**
   * Array Builder currently relies on the shared generic block field bindings.
   * This file is intentionally small but keeps the modal surface owned by the
   * block package, so future Array Builder interactions stay local to the block.
   */
  document.addEventListener("cw:block-modal-mounted", (event) => {
    const root = event?.detail?.root;
    if (!(root instanceof HTMLElement) || root.dataset.nodeKind !== "array_builder") {
      return;
    }
    root.dataset.arrayBuilderModalReady = "true";
  });
})();
