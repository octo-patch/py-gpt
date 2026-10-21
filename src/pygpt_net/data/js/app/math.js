// ==========================================================================
// Math renderer (async, chunked)
// ==========================================================================

class MathRenderer {

	// Math renderer for LaTeX formulas.
	constructor(cfg, raf, asyncer) {
		this.cfg = cfg;
		this.raf = raf;
		this.asyncer = asyncer;
		this.scheduled = false;

		// rAF key used by the central pump (do not change – API compatibility).
		this.rafKey = {
			t: 'Math:render'
		};

		// Pending roots aggregation: if document-level render is requested, it supersedes others.
		this._pendingRoots = new Set();
		this._pendingDoc = false;
	}

	// Async, cooperative KaTeX rendering to avoid long blocking on many formulas.
	async renderAsync(root) {
		if (typeof katex === 'undefined') return;
		const scope = root || document;
		const scripts = Array.from(scope.querySelectorAll('script[type^="math/tex"]'));
		const useToString = (typeof katex.renderToString === 'function');

		// Math placeholders are emitted inside <script type="math/tex">. Script
		// elements are raw-text nodes, so HTML entities produced by escapeHtml()
		// are not decoded by the HTML parser. Decode exactly the single escaping
		// layer added by the placeholder renderer before passing TeX to KaTeX.
		// A callback replacement is intentional: replacements are not scanned
		// again, so an original literal "&lt;" remains "&lt;" rather than "<".
		const decodeEscapedMathText = (raw) => String(raw ?? '').replace(
			/&(amp|lt|gt);/g,
			(_match, entity) => entity === 'amp' ? '&' : (entity === 'lt' ? '<' : '>')
		);


		// KaTeX has no character metrics entry for the standard Unicode ≠ glyph
		// used by our \neq/\ne workaround. Rendering is nevertheless correct;
		// suppress only this known, harmless KaTeX warning and preserve every
		// other console warning. KaTeX rendering itself is synchronous, so the
		// original console.warn is restored immediately after each render call.
		const renderWithoutNeqMetricsWarning = (fn) => {
			if (typeof console === 'undefined' || typeof console.warn !== 'function') {
				return fn();
			}
			const originalWarn = console.warn;
			console.warn = function (...args) {
				const msg = args.length > 0 ? String(args[0]) : '';
				if (msg === "No character metrics for '≠' in style 'Main-Regular' and mode 'math'") {
					return;
				}
				return originalWarn.apply(this, args);
			};
			try {
				return fn();
			} finally {
				console.warn = originalWarn;
			}
		};

		const batchFn = async (script) => {
			if (!script || !script.isConnected) return;
			// Only render math in bot messages
			if (!script.closest('.msg-box.msg-bot')) return;
			const t = script.getAttribute('type') || '';
			const displayMode = t.indexOf('mode=display') > -1;
			// avoid innerText (it may trigger layout). textContent is sufficient here.
			const mathContent = decodeEscapedMathText(script.textContent || '');
			const parent = script.parentNode;
			if (!parent) return;

			try {
				if (useToString) {
					let html = '';
					try {
						html = renderWithoutNeqMetricsWarning(() => katex.renderToString(mathContent, {
							displayMode,
							throwOnError: false,
							// KaTeX 0.16.x normally composes \neq from "=" and the
							// private-use U+E020 overlay glyph. If KaTeX_Main cannot
							// be loaded by WebEngine, U+E020 becomes a missing-glyph box.
							// Render the standard Unicode symbol instead while preserving
							// relation spacing and the original TeX in the MathML annotation.
							macros: {
								'\\neq': '\\mathrel{\\char"2260}',
								'\\ne': '\\mathrel{\\char"2260}'
							}
						}));
					} catch (_) {
						const fb = displayMode ? `\\[${mathContent}\\]` : `\\(${mathContent}\\)`;
						html = (displayMode ? `<div>${Utils.escapeHtml(fb)}</div>` : `<span>${Utils.escapeHtml(fb)}</span>`);
					}
					const host = document.createElement(displayMode ? 'div' : 'span');
					host.innerHTML = html;
					const el = host.firstElementChild || host;
					if (parent.classList && parent.classList.contains('math-pending')) parent.replaceWith(el);
					else parent.replaceChild(el, script);
				} else {
					const el = document.createElement(displayMode ? 'div' : 'span');
					try {
						renderWithoutNeqMetricsWarning(() => katex.render(mathContent, el, {
							displayMode,
							throwOnError: false,
							macros: {
								'\\neq': '\\mathrel{\\char"2260}',
								'\\ne': '\\mathrel{\\char"2260}'
							}
						}));
					} catch (_) {
						el.textContent = (displayMode ? `\\[${mathContent}\\]` : `\\(${mathContent}\\)`);
					}
					if (parent.classList && parent.classList.contains('math-pending')) parent.replaceWith(el);
					else parent.replaceChild(el, script);
				}
			} catch (_) {
				// Keep fallback text intact on any error
			}
		};

		// Process formulas cooperatively (rAF yields).
		await this.asyncer.forEachChunk(scripts, batchFn, 'MathRenderer');
	}

	// Schedule math rendering for a root. Coalesces multiple calls.
	schedule(root, _delayIgnored = 0, forceNow = false) {
		// If KaTeX is not available, honor no-op. API stays intact.
		if (typeof katex === 'undefined') return;

		// Normalize root (default to whole document).
		const targetRoot = root || document;

		// Fast existence check to avoid arming rAF when nothing to do, but still
		// keep aggregation semantics: if a job is already scheduled we can still
		// merge new roots into the pending set when they actually contain math.
		let hasMath = true;
		if (!forceNow) {
			try {
				hasMath = !!(targetRoot && targetRoot.querySelector && targetRoot.querySelector('script[type^="math/tex"]'));
			} catch (_) {
				hasMath = false;
			}
			if (!hasMath) return; // nothing to render for this root; safe early exit
		}

		// Aggregate roots so nothing is lost while one job is already scheduled.
		if (targetRoot === document || targetRoot === document.documentElement || targetRoot === document.body) {
			this._pendingDoc = true; // promote to a full-document sweep
			this._pendingRoots.clear(); // small optimization (document covers all)
		} else if (!this._pendingDoc) {
			this._pendingRoots.add(targetRoot);
		}

		// If a task is already scheduled, do not arm another – coalescing will take care of it.
		if (this.scheduled && this.raf && typeof this.raf.isScheduled === 'function' && this.raf.isScheduled(this.rafKey)) return;

		this.scheduled = true;
		const priority = forceNow ? 0 : 2;

		// Single rAF job drains all pending roots; renderAsync remains public and unchanged.
		this.raf.schedule(this.rafKey, () => {
			this.scheduled = false;

			const useDoc = this._pendingDoc;
			const roots = [];

			if (useDoc) {
				roots.push(document);
			} else {
				this._pendingRoots.forEach((r) => {
					// Only keep connected elements to avoid useless work.
					try {
						if (r && (r.isConnected === undefined || r.isConnected)) roots.push(r);
					} catch (_) {
						// Conservative: keep the root; renderAsync guards internally.
						roots.push(r);
					}
				});
			}

			// Reset aggregation state before running (new calls can aggregate afresh).
			this._pendingDoc = false;
			this._pendingRoots.clear();

			// Fire-and-forget async drain; keep renderAsync API intact.
			(async () => {
				for (let i = 0; i < roots.length; i++) {
					try {
						await this.renderAsync(roots[i]);
					} catch (_) {
						/* swallow – resilient */
					}
				}
			})();
		}, 'Math', priority);
	}

	// Cleanup pending work and state.
	cleanup() {
		try {
			this.raf.cancelGroup('Math');
		} catch (_) {}
		this.scheduled = false;

		// Ensure pending state is fully cleared on cleanup.
		try {
			this._pendingRoots.clear();
		} catch (_) {}
		this._pendingDoc = false;
	}
}