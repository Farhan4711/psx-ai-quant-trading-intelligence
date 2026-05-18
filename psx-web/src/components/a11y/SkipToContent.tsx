/**
 * Skip-to-main-content link — Phase 11 Step 97 a11y win.
 *
 * Renders as the very first focusable element on the page. Visually
 * hidden until it receives keyboard focus, at which point it jumps to
 * the top-left of the viewport so screen-reader / keyboard-only users
 * can bypass the persistent header nav (which is ~15 links on the
 * authenticated layout).
 *
 * Usage: put `<SkipToContent />` as the first child of the page's
 * root layout div, and put `id="main-content"` on the <main> element.
 */
export function SkipToContent() {
  return (
    <a
      href="#main-content"
      className="
        sr-only
        focus:not-sr-only
        focus:fixed focus:left-4 focus:top-4 focus:z-[100]
        focus:rounded-md focus:bg-blue-600 focus:px-3 focus:py-1.5
        focus:text-sm focus:font-medium focus:text-white
        focus:shadow-lg focus:outline-none focus:ring-2
        focus:ring-blue-300 focus:ring-offset-2
      "
    >
      Skip to main content
    </a>
  );
}
