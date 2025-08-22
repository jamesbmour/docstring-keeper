### 🧹 Strip Python Function Bodies (Keep Docstrings)

A small Streamlit app that removes all code inside Python functions/methods while preserving:
- The function/method signature (name, arguments, decorators, return annotation)
- The docstring (if present)
- All comments and formatting outside functions (e.g., top-level headers like `################################ Streamlit UI ################################`)

If a function has no docstring, the app inserts a single `pass` to keep the code syntactically valid.

---

#### Features
- Upload a .py file or paste code directly
- Keeps docstrings inside functions; removes all other in-body statements and comments
- Preserves non-indented (top-level) comments and formatting outside functions
- Preview the transformed code in a copyable code block
- Download the transformed file with a sensible filename

---

#### How it works
The app parses your code with Python’s AST, finds function and method body ranges using node start/end positions, and replaces only those ranges with either:
- The original docstring (if present as the first statement), or
- A correctly indented `pass`

Because it only edits function-body text spans and leaves the rest untouched, top-level comments and formatting outside functions are preserved.

---

#### Requirements
- Python 3.8+ (requires AST end positions available from Python 3.8 onward)
- Streamlit

---

#### Installation
```bash
pip install streamlit
```

---

#### Run the app
```bash
streamlit run app.py
```

- The app will open in your browser (usually http://localhost:8501).
- Choose your input method:
  - Upload file: select a .py file
  - Paste code: paste your Python code into the text area
- Click “Transform”
- Copy the preview or download the transformed file

---

#### Example

Before:
```python
def parse(url):
    """Extract owner and repo name from a GitHub URL."""
    # Use regex to find owner and repo in a standard GitHub URL.
    m = re.match(r"https?://github\.com/([^/\s]+)/([^/\s#?]+)", url or "")
    # Raise an error if the URL format is invalid.
    if not m:
        raise ValueError("Enter a valid GitHub URL like https://github.com/owner/repo")
    owner, repo = m.group(1), m.group(2)
    return owner, repo[:-4] if repo.endswith(".git") else repo  # Clean .git suffix if present
```

After:
```python
def parse(url):
    """Extract owner and repo name from a GitHub URL."""
```

Top-level comments are kept:
```python
################################ Streamlit UI ################################
def main():
    """Main function to run the Streamlit app."""
```

---

#### Known limitations
- Code must be valid Python that can be parsed by `ast.parse`.
- Comments and code inside function bodies are removed (only the docstring is kept).
- The app does not reformat code; it preserves original formatting outside functions.

---

#### Troubleshooting
- SyntaxError: Ensure the input is valid Python code.
- Version warning: Use Python 3.8+.
- Encoding issues: The app attempts UTF-8, UTF-8 with BOM, then Latin-1 for uploaded files. If decoding fails, re-save the file as UTF-8.

---

#### Contributing
Issues and PRs are welcome. Ideas:
- Optional: keep first N inline comments above a function
- Add a “keep pass even if docstring exists” toggle
- CLI wrapper and tests

---

#### License
MIT