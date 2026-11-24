// Pure page logic for aliasing_pages (v8): which paged objects are visible on which page.
// Paged objects carry a scripting name with a page prefix (gui.md section 5).

export const PAGE_PREFIXES = ["mod_", "tone_", "out_"] as const;

/**
 * Visibility of the object named `varname` on page `page` (0 Mod, 1 Tone, 2 Out):
 * true / false for paged objects, null for objects that are not on a page.
 */
export function visibilityFor(varname: string | null | undefined, page: number): boolean | null {
	if (!varname) return null;
	const p = PAGE_PREFIXES.findIndex((prefix) => varname.startsWith(prefix));
	if (p < 0) return null;
	return p === clampPage(page);
}

export function clampPage(page: number): number {
	if (!Number.isFinite(page)) return 0;
	return Math.min(PAGE_PREFIXES.length - 1, Math.max(0, Math.round(page)));
}
