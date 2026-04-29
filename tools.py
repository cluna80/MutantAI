"""
tools.py — Mutant AI core tools (never auto-edited)
Custom tools live in custom_tools.py
"""
import io
from contextlib import redirect_stdout, redirect_stderr
import subprocess, sys, tempfile, os, textwrap, urllib.request, re, ast
from pathlib import Path
from ddgs import DDGS
from langchain_core.tools import tool
from memory import remember_project, get_memory_context, remember_error

CODE_EXTENSIONS = {".py",".js",".ts",".jsx",".tsx",".html",".css",".json",".yaml",".yml",".toml",".md",".env",".sh",".txt",".sql"}
IGNORE_DIRS = {".venv","venv","node_modules","__pycache__",".git",".mypy_cache","dist","build",".next",".cache"}

def _clean_path(path: str, default: str = ".") -> Path:
    if not path or path.strip().lower() in ("none","null",""):
        return Path(default).resolve()
    p = path.strip()
    for bad in ["\\None","/None","\\null","/null"]:
        if p.endswith(bad): p = p[:-len(bad)]
    if not p or p.lower() in ("none","null"): p = default
    return Path(p).expanduser().resolve()

def _strip_hallucinated_junk(code: str) -> str:
    """Remove Observation:, Thought:, Action: lines that models hallucinate"""
    lines = code.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(('Observation:', 'Thought:', 'Action:', 'Observation', 'Thought', 'Action')):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)

def _extract_json_from_malformed(tool_input: str) -> dict:
    """Extract JSON-like data from malformed model inputs"""
    result = {}
    
    # Pattern for write_file: path: 'xxx', content: """yyy"""
    path_match = re.search(r"path\s*:\s*['\"]([^'\"]+)['\"]", tool_input)
    if path_match:
        result["path"] = path_match.group(1)
    
    # Try to extract content from triple quotes
    content_match = re.search(r"content\s*:\s*\"\"\"(.*?)\"\"\"", tool_input, re.DOTALL)
    if content_match:
        result["content"] = content_match.group(1)
    
    # Try single quotes
    if "content" not in result:
        content_match = re.search(r"content\s*:\s*['\"](.*?)['\"]", tool_input, re.DOTALL)
        if content_match:
            result["content"] = content_match.group(1)
    
    # Try simple key=value format
    if not result:
        parts = tool_input.split(",")
        for part in parts:
            if ":" in part:
                key, val = part.split(":", 1)
                key = key.strip().strip("'\"")
                val = val.strip().strip("'\"")
                if key in ["path", "content"]:
                    result[key] = val
    
    return result


@tool
def run_code_fast(code: str) -> str:
    """Execute Python code faster using exec with captured output."""
    code = _strip_hallucinated_junk(code)
    
    # Capture output
    f = io.StringIO()
    try:
        with redirect_stdout(f), redirect_stderr(f):
            exec(code, {'__name__': '__main__'})
        output = f.getvalue()
        return f"Output:\n{output}" if output else "Ran with no output."
    except Exception as e:
        return f"Error: {e}"

@tool
def run_code(code: str) -> str:
    """Execute Python code and return output. Input is Python code as a string."""
    # Strip hallucinated junk first
    code = _strip_hallucinated_junk(code)
    
    # Remove any markdown code fences
    code = re.sub(r"```python\s*", "", code)
    code = re.sub(r"```\s*", "", code)
    
    # If code starts with "Action Input:" or similar, extract the actual code
    if "Action Input:" in code:
        code = code.split("Action Input:", 1)[1].strip()
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(textwrap.dedent(code)); tmp = f.name
    try:
        r = subprocess.run([sys.executable, tmp], capture_output=True, text=True, timeout=30)
        out, err = r.stdout.strip(), r.stderr.strip()
        if r.returncode == 0: return f"Output:\n{out}" if out else "Ran with no output."
        remember_error(err[:200], "auto-retry")
        return f"Error:\n{err}\n{out}"
    except subprocess.TimeoutExpired: return "Error: Timed out."
    finally: os.unlink(tmp)

@tool
def run_shell(command: str) -> str:
    """Run any shell command: pip, npm, git, etc. Input is the command string."""
    command = _strip_hallucinated_junk(command)
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=120)
        out, err = r.stdout.strip(), r.stderr.strip()
        return f"Success:\n{out}" if r.returncode == 0 else f"Failed:\n{err}\n{out}"
    except subprocess.TimeoutExpired: return "Error: Timed out."
    except Exception as e: return f"Error: {e}"

@tool
def read_file(path: str) -> str:
    """Read a file. Input is the file path."""
    path = _strip_hallucinated_junk(path)
    try:
        p = _clean_path(path)
        lines = p.read_text(encoding="utf-8").split("\n")
        return f"File: {p} ({len(lines)} lines)\n\n" + "\n".join(f"{i+1:4d} | {l}" for i,l in enumerate(lines))
    except Exception as e: return f"Error: {e}"

@tool
def write_file(path: str, content: str) -> str:
    """Write content to a file. Args: path (file path), content (text to write)."""
    # Clean up inputs
    path = _strip_hallucinated_junk(path.strip())
    content = _strip_hallucinated_junk(content)
    
    # If content is a string that looks like malformed JSON, try to extract
    if content.startswith("path:") or "content:" in content:
        extracted = _extract_json_from_malformed(path + " " + content)
        if "path" in extracted:
            path = extracted["path"]
        if "content" in extracted:
            content = extracted["content"]
    
    try:
        p = _clean_path(path, "output.py")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {content.count(chr(10))+1} lines to {p}"
    except Exception as e: return f"Error: {e}"

@tool
def patch_file(path: str, old_code: str, new_code: str) -> str:
    """Replace a code block in a file. Args: path, old_code (exact text to replace), new_code."""
    path = _strip_hallucinated_junk(path)
    old_code = _strip_hallucinated_junk(old_code)
    new_code = _strip_hallucinated_junk(new_code)
    try:
        p = _clean_path(path)
        orig = p.read_text(encoding="utf-8")
        if old_code not in orig: return f"Code block not found in {p}."
        p.write_text(orig.replace(old_code, new_code, 1), encoding="utf-8")
        return f"Patched {p}."
    except Exception as e: return f"Error: {e}"

@tool
def list_dir(path: str) -> str:
    """List files in a directory. Use '.' for current directory."""
    path = _strip_hallucinated_junk(path)
    try:
        p = _clean_path(path)
        lines = []
        for e in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name)):
            if e.is_dir(): lines.append(f"[DIR]  {e.name}/")
            else:
                sz = e.stat().st_size
                lines.append(f"[FILE] {e.name} ({sz//1024}KB)" if sz>1024 else f"[FILE] {e.name} ({sz}B)")
        return f"{p}:\n" + "\n".join(lines)
    except Exception as e: return f"Error: {e}"

@tool
def scan_project(path: str) -> str:
    """Scan a project folder and return code file contents. Pass '.' for current directory."""
    path = _strip_hallucinated_junk(path)
    try:
        root = _clean_path(path)
        out = [f"Project: {root}"]
        count = 0
        for fp in sorted(root.rglob("*")):
            if any(p in IGNORE_DIRS for p in fp.parts): continue
            if not fp.is_file() or fp.suffix not in CODE_EXTENSIONS: continue
            rel = fp.relative_to(root)
            try:
                lines = fp.read_text(encoding="utf-8", errors="ignore").split("\n")
                count += 1
                out.append(f"\n--- {rel} ({len(lines)} lines) ---")
                out.append("\n".join(lines[:50]))
                if len(lines) > 50: out.append(f"...({len(lines)-50} more)")
            except: out.append(f"--- {rel} (unreadable) ---")
        out.insert(1, f"Found {count} files\n")
        remember_project("last_scan", str(root))
        return "\n".join(out)
    except Exception as e: return f"Error: {e}"

@tool
def web_search(query: str) -> str:
    """Search the web with DuckDuckGo. Input is a search query."""
    query = _strip_hallucinated_junk(query)
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results: return f"No results for: {query}"
        out = [f"Results for '{query}':\n"]
        for i,r in enumerate(results,1):
            out.append(f"{i}. {r.get('title','')}\n   {r.get('body','')}\n   {r.get('href','')}\n")
        return "\n".join(out)
    except Exception as e: return f"Search error: {e}"

@tool
def fetch_url(url: str) -> str:
    """Fetch HTML/text from a URL. Input is the URL."""
    url = _strip_hallucinated_junk(url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.read().decode("utf-8", errors="ignore")[:3000]
    except Exception as e: return f"Error: {e}"

@tool
def save_memory(key: str, value: str) -> str:
    """Save a project fact to memory. Args: key (e.g. 'framework'), value (e.g. 'React')."""
    key = _strip_hallucinated_junk(key)
    value = _strip_hallucinated_junk(value)
    return remember_project(key, value)

@tool
def get_memory(query: str) -> str:
    """Get all stored project memory. Input can be anything."""
    return get_memory_context()

@tool
def plan_coding_task(goal: str) -> str:
    """Break down a coding task into steps. Use this FIRST for any coding task."""
    goal = _strip_hallucinated_junk(goal)
    return f"""📋 **IMPLEMENTATION PLAN: {goal}**

**1. UNDERSTAND**
- Requirements: {goal}
- Success criteria: Working, tested code

**2. FILES NEEDED**
- Files to create/modify: Determine the main file(s) needed

**3. STEP-BY-STEP**
- Step 1: Setup/imports and basic structure
- Step 2: Core logic implementation
- Step 3: Error handling and edge cases
- Step 4: Testing and verification

**4. EDGE CASES**
- What could go wrong: Invalid inputs, missing requirements
- How to handle: Try/except, validation, fallbacks

**5. TESTING PLAN**
- How to verify: Run with test inputs, check outputs

Now write the code following this plan. Use write_file to save the code."""

@tool
def create_tool(tool_code: str) -> str:
    """
    Save a new tool to custom_tools.py. Input is plain Python @tool function code only.
    NO yaml, NO markdown, NO imports from tools.py.
    Example: @tool\\ndef hello(x: str) -> str:\\n    \\'Say hello.\\'\\n    return f\\'Hello {x}\\'
    """
    try:
        # Strip markdown fences
        tool_code = re.sub(r"```python\s*", "", tool_code)
        tool_code = re.sub(r"```\s*", "", tool_code)
        # Strip hallucinated junk
        tool_code = _strip_hallucinated_junk(tool_code)
        # Extract from @tool onward
        m = re.search(r"(@tool.*)", tool_code, re.DOTALL)
        if m: tool_code = m.group(1).strip()
        else:
            fm = re.search(r"(def \w+\(.*)", tool_code, re.DOTALL)
            if fm: tool_code = "@tool\n" + fm.group(1)
            else: return "Error: No function found. Write plain Python only."
        # Get name
        nm = re.search(r"def (\w+)\(", tool_code)
        if not nm: return "Error: No function name found."
        name = nm.group(1)
        # Reject circular imports
        if "from tools import" in tool_code or "import tools" in tool_code:
            return "Error: Do not import from tools.py in a custom tool."
        # Validate syntax
        try: ast.parse(tool_code)
        except SyntaxError as e: return f"Syntax error: {e}"
        # Write to custom_tools.py
        ct_path = Path(__file__).parent / "custom_tools.py"
        orig = ct_path.read_text(encoding="utf-8") if ct_path.exists() else "# Custom tools for Mutant AI\nCUSTOM_TOOLS = []\n"
        if f"def {name}" in orig: return f"Tool '{name}' already exists."
        if "CUSTOM_TOOLS = []" in orig:
            new = orig.replace("CUSTOM_TOOLS = []", f"{tool_code}\n\nCUSTOM_TOOLS = [{name}]")
        else:
            new = re.sub(r"CUSTOM_TOOLS = \[([^\]]*)\]",
                lambda m2: f"CUSTOM_TOOLS = [{(m2.group(1).strip()+', ') if m2.group(1).strip() else ''}{name}]", orig)
            new = new.rstrip() + f"\n\n{tool_code}\n"
        try: ast.parse(new)
        except SyntaxError as e: return f"File syntax error: {e}"
        ct_path.write_text(new, encoding="utf-8")
        remember_project("last_tool_added", name)
        return f"Tool '{name}' saved! Restart Streamlit to activate."
    except Exception as e: return f"Error: {e}"


# Load custom tools safely
_CUSTOM_TOOLS = []
try:
    import importlib, importlib.util
    _spec = importlib.util.spec_from_file_location("custom_tools", Path(__file__).parent / "custom_tools.py")
    _ct = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_ct)
    _CUSTOM_TOOLS = getattr(_ct, "CUSTOM_TOOLS", [])
    print(f"[Mutant AI] Loaded {len(_CUSTOM_TOOLS)} custom tool(s).")
except Exception as _e:
    print(f"[Mutant AI] custom_tools warning: {_e}")

# Also try to load get_current_time if it exists in custom_tools
try:
    from custom_tools import get_current_time
    if get_current_time not in _CUSTOM_TOOLS:
        _CUSTOM_TOOLS.append(get_current_time)
except ImportError:
    pass

ALL_TOOLS = [
    run_code, run_shell, read_file, write_file, patch_file,
    list_dir, scan_project, web_search, fetch_url,
    save_memory, get_memory, plan_coding_task, create_tool,
] + _CUSTOM_TOOLS

TOOLS_BY_NAME = {t.name: t for t in ALL_TOOLS}