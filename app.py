#!/usr/bin/env python3
import ast
import sys
import streamlit as st

st.set_page_config(page_title="Strip Python Function Bodies", page_icon="🧹", layout="centered")
st.title("🧹 Strip Python Function Bodies (Keep Docstrings)")
st.write(
    "Upload a .py file. This app removes all statements inside every function/method, "
    "keeping only the function signature and the docstring (if present). "
    "If a function has no docstring, a `pass` is inserted to remain syntactically valid.\n\n"
    "_Note: Formatting and comments are not preserved (AST-based transform). Requires Python 3.9+._"
)

if sys.version_info < (3, 9):
    st.warning("This app requires Python 3.9+ (uses ast.unparse). Please upgrade your Python environment.")

def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    if not isinstance(stmt, ast.Expr):
        return False
    val = stmt.value
    if isinstance(val, ast.Constant):
        return isinstance(val.value, str)
    # Fallback for very old versions (Streamlit typically runs on 3.9+ anyway)
    try:
        import ast as _ast
        if isinstance(val, _ast.Str):  # type: ignore[attr-defined]
            return isinstance(val.s, str)  # type: ignore[attr-defined]
    except Exception:
        pass
    return False

class StripFunctionBodies(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        new_node = node
        if new_node.body and _is_docstring_stmt(new_node.body[0]):
            new_node.body = [new_node.body[0]]
        else:
            new_node.body = [ast.Pass()]
        self._visit_header(new_node)
        return new_node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        new_node = node
        if new_node.body and _is_docstring_stmt(new_node.body[0]):
            new_node.body = [new_node.body[0]]
        else:
            new_node.body = [ast.Pass()]
        self._visit_header(new_node)
        return new_node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        # Walk into class body so methods get transformed
        return self.generic_visit(node)

    def _visit_header(self, node: ast.AST) -> None:
        # Visit decorators (keep them intact but visit nested nodes)
        if hasattr(node, "decorator_list"):
            node.decorator_list = [self.visit(d) for d in getattr(node, "decorator_list")]
        # Visit return annotation
        if hasattr(node, "returns") and getattr(node, "returns") is not None:
            node.returns = self.visit(getattr(node, "returns"))  # type: ignore[assignment]

def transform_source(source: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse Python source: {e}") from e

    new_tree = StripFunctionBodies().visit(tree)
    ast.fix_missing_locations(new_tree)

    if not hasattr(ast, "unparse"):
        raise RuntimeError("Python 3.9+ is required (ast.unparse not available).")

    new_source = ast.unparse(new_tree)
    if not new_source.endswith("\n"):
        new_source += "\n"
    return new_source

uploaded = st.file_uploader("Upload a Python file", type=["py"])
process = st.button("Transform", type="primary", disabled=(uploaded is None))

if uploaded is not None and process:
    # Read and decode the uploaded file
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
    else:
        try:
            new_source = transform_source(text)
            base_name = uploaded.name.rsplit(".", 1)[0]
            out_name = f"{base_name}_stripped.py"

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
        "- Works for top-level functions, class methods, and async functions.\n"
        "- Comments and original formatting are not preserved (AST-based)."
    )