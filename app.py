#!/usr/bin/env python3
import ast
import sys
import streamlit as st
from typing import List, Tuple

st.set_page_config(page_title="Strip Python Function Bodies", page_icon="🧹", layout="centered")
st.title("🧹 Strip Python Function Bodies (Keep Docstrings)")
st.write(
    "Upload a .py file or paste code. This app removes all statements inside every function/method, "
    "keeping only the function signature and the docstring (if present). "
    "If a function has no docstring, a `pass` is inserted to remain syntactically valid.\n\n"
    "Comments and formatting outside functions are preserved. Comments inside functions are removed.\n\n"
    "_Note: Uses AST locations to surgically edit bodies (no full unparse). Python 3.8+ recommended._"
)

if sys.version_info < (3, 8):
    st.warning("This app works best on Python 3.8+ (requires end positions on AST nodes).")

def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr):
        return False
    val = stmt.value
    if isinstance(val, ast.Constant):
        return isinstance(val.value, str)
    try:
        if isinstance(val, ast.Str):  # type: ignore[attr-defined]
            return isinstance(val.s, str)  # type: ignore[attr-defined]
    except Exception:
        pass
    return False

def _line_starts(text: str) -> List[int]:
    # Returns the absolute start index (0-based) for each line (1-based line numbers)
    # line_starts[lineno-1] + col_offset => absolute index
    starts = [0]
    acc = 0
    for line in text.splitlines(keepends=True):
        acc += len(line)
        starts.append(acc)
    return starts

def _abs_index(line_starts: List[int], lineno: int, col: int) -> int:
    return line_starts[lineno - 1] + col

def _dedupe_overlapping_ranges(ranges: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
    # Remove ranges that are fully contained within earlier kept ranges.
    # Sort by start, then by end descending; then keep non-contained.
    ranges_sorted = sorted(ranges, key=lambda x: (x[0], -x[1]))
    kept: List[Tuple[int, int, str]] = []
    current_end = -1
    for s, e, repl in ranges_sorted:
        if s >= current_end:
            kept.append((s, e, repl))
            current_end = e
        else:
            # Overlap: only keep the outermost (already kept) range
            # If fully contained, skip; if partially overlapping, AST should prevent this case for function bodies.
            continue
    return kept

def transform_source_preserve_outside_comments(source: str) -> str:
    """
    Replace only the body regions of functions/methods with either:
      - The original docstring (if present as first statement), or
      - A single 'pass' at the correct indentation
    Leaves everything else (including top-level comments and formatting) unchanged.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse Python source: {e}") from e

    line_starts = _line_starts(source)
    lines = source.splitlines(keepends=True)

    replacements: List[Tuple[int, int, str]] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._handle(node)
            # We still visit nested to gather ranges, but will dedupe overlaps later
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._handle(node)
            self.generic_visit(node)

        def _handle(self, node: ast.AST) -> None:
            body = getattr(node, "body", None)
            if not body:
                return
            first = body[0]
            last = body[-1]

            # end positions needed (Python 3.8+)
            if not hasattr(last, "end_lineno") or not hasattr(last, "end_col_offset"):
                raise RuntimeError("Python 3.8+ is required (AST end positions not available).")

            start_idx = _abs_index(line_starts, first.lineno, first.col_offset)
            end_idx = _abs_index(line_starts, last.end_lineno, last.end_col_offset)

            # Build replacement
            if _is_docstring_stmt(first):
                seg = ast.get_source_segment(source, first)
                if seg is None:
                    # Fallback: reconstruct a minimal docstring preserving indentation
                    indent = lines[first.lineno - 1][: first.col_offset]
                    doc_text = ""
                    val = first.value  # type: ignore[attr-defined]
                    if isinstance(val, ast.Constant) and isinstance(val.value, str):
                        doc_text = val.value
                    else:
                        try:
                            # legacy ast.Str
                            doc_text = val.s  # type: ignore[attr-defined]
                        except Exception:
                            doc_text = ""
                    # Use triple quotes; no escaping attempt for robustness
                    seg = f'{indent}"""' + doc_text + '"""'
                replacement = seg
            else:
                # No docstring: insert 'pass' with correct indentation
                first_line = lines[first.lineno - 1]
                indent = first_line[: first.col_offset]
                replacement = f"{indent}pass"

            replacements.append((start_idx, end_idx, replacement))

    Visitor().visit(tree)

    if not replacements:
        # Nothing to change
        return source

    # Remove nested/overlapping inner ranges; keep outermost
    replacements = _dedupe_overlapping_ranges(replacements)
    # Apply from end to start so indices remain valid
    new_src = source
    for s, e, repl in sorted(replacements, key=lambda x: x[0], reverse=True):
        new_src = new_src[:s] + repl + new_src[e:]

    # Ensure a trailing newline if original had one
    if source.endswith("\n") and not new_src.endswith("\n"):
        new_src += "\n"
    return new_src

# --- UI: Choose input method ---
method = st.radio("Choose input method", ["Upload file", "Paste code"], index=1, horizontal=True)

uploaded = None
pasted_text = None

if method == "Upload file":
    uploaded = st.file_uploader("Upload a Python file", type=["py"])
else:
    pasted_text = st.text_area(
        "Paste Python code",
        height=300,
        placeholder="Paste your .py code here...",
    )

# Enable Transform button only when we have input
can_process = (uploaded is not None) if method == "Upload file" else bool(pasted_text and pasted_text.strip())
process = st.button("Transform", type="primary", disabled=not can_process)

if process:
    try:
        if method == "Upload file":
            raw = uploaded.read()
            text = None
            for enc in ("utf-8", "utf-8-sig", "latin-1"):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                st.error("Could not decode file. Please upload a UTF-8 encoded .py file.")
                st.stop()
            base_name = uploaded.name.rsplit(".", 1)[0]
            out_name = f"{base_name}_stripped.py"
        else:
            text = pasted_text or ""
            base_name = "pasted"
            out_name = f"{base_name}_stripped.py"

        new_source = transform_source_preserve_outside_comments(text)

        st.success("Transformation complete.")
        st.download_button(
            "Download transformed file",
            data=new_source.encode("utf-8"),
            file_name=out_name,
            mime="text/x-python",
        )

        st.subheader("Preview (copyable)")
        st.code(new_source, language="python")

    except Exception as e:
        st.error(f"Error: {e}")

with st.expander("Details and behavior"):
    st.markdown(
        "- Keeps function/method names, arguments, decorators, and return annotations.\n"
        "- Preserves only the docstring as the body (if present); otherwise inserts `pass`.\n"
        "- Preserves comments and formatting outside functions (e.g., section headers).\n"
        "- Removes comments and code inside functions to leave only the docstring or `pass`.\n"
        "- Works for top-level functions, class methods, and async functions."
    )