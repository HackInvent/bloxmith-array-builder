import { withProperties } from "./properties.js";

// -----------------------------------------------------------------------------
// Role: Owns Array Builder modal behavior hooks.
// File Name: block_modal.js
// Author: Alexandre EL
// Email: alex@hackinvent.com
// Created Date: 2026-07-07
// -----------------------------------------------------------------------------

/**
 * Mark the modal as owned by this release; the shared generic field bindings
 * still handle the configuration itself. The surface keeps its own module so a
 * future Array Builder interaction stays local to the block package.
 *
 * @param {HTMLElement} root - Mounted Array Builder modal root.
 */
function mountOwned(root) {
  if (root instanceof HTMLElement) {
    root.dataset.arrayBuilderModalReady = "true";
  }
}

/** Keep the block behavior and add properties-only accessibility. */
export function mount(root, ...args) {
  return withProperties(mountOwned).call(this, root, ...args);
}
