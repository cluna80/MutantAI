"""
agent.py — MutantAI Agent v3
Upgrades:
- Run-and-fix loop: writes code → runs it → fixes errors → retries up to 3x
- Auto project scan before modification tasks
- Web search for current events
- Vision bypass with auto image resize
"""

import json
import re
import os
from pathlib import Path
from model import generate_raw, should_bypass_agent
from tools import TOOLS_BY_NAME, ALL_TOOLS
from memory import remember_decision, remember_error

TOOL_NAMES = ", ".join(TOOLS_BY_NAME.keys())

SPECIALIST_PROMPTS = {
    "mutant-fbdd": """You are MutantAI-FBDD, an expert computational medicinal chemist fine-tuned on real drug discovery campaigns.
Analyze molecules step by step: properties → pharmacophore → affinity prediction → ADMET → recommendations.
Key knowledge: EGFR top leads -10.08 kcal/mol, HIV Integrase -9.708 kcal/mol, HIV Protease CURE_17G_002 -7.753 kcal/mol.
Give direct scientific reasoning. Do NOT write code.""",
    "mutant-trader": """You are MutantAI-Trader, an expert in sports betting and financial markets.
Your expertise: NFL analysis, horse racing, DraftKings fantasy, Kelly criterion, crypto/DeFi analysis.
Give direct analysis and actionable recommendations.
Always include: edge identification, risk quantification, position sizing, exit criteria.
Be honest about uncertainty. Never chase losses.""",
}


def _parse_response(text: str):
    final_match = re.search(r"Final Answer\s*:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
    if final_match:
        return [("final", None, final_match.group(1).strip())]

    actions = []
    pattern_same = r"Action:\s*(\w+)\s+Action Input:\s*(.+?)(?=\n\s*Action:|\n\s*Final Answer:|$)"
    matches = re.findall(pattern_same, text, re.DOTALL | re.IGNORECASE)

    if not matches:
        pattern_sep = r"Action:\s*(\w+)\s*\nAction Input:\s*(.+?)(?=\n\s*Action:|\n\s*Thought:|\n\s*Final Answer:|$)"
        matches = re.findall(pattern_sep, text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        tool_name = match[0].strip()
        tool_input = match[1].strip()
        if tool_input.startswith('"') and tool_input.endswith('"'):
            tool_input = tool_input[1:-1]
        if tool_input.startswith("'") and tool_input.endswith("'"):
            tool_input = tool_input[1:-1]
        tool_input = re.sub(r"^```json\s*", "", tool_input)
        tool_input = re.sub(r"^```\s*", "", tool_input)
        tool_input = re.sub(r"```$", "", tool_input)
        actions.append(("action", tool_name, tool_input))

    return actions if actions else [("incomplete", None, text.strip())]


def _fix_nested_json(tool_input: str) -> dict:
    if tool_input.strip().startswith('{"path": "{"'):
        try:
            outer = json.loads(tool_input)
            if "path" in outer and isinstance(outer["path"], str):
                inner_match = re.search(r'\{[^{}]*"path"[^{}]*"content"[^{}]*\}', outer["path"])
                if inner_match:
                    inner = json.loads(inner_match.group())
                    if "path" in inner and "content" in inner:
                        return inner
        except Exception:
            pass
    return None


def validate_complete_code(content: str, filename: str) -> tuple[bool, list[str]]:
    issues = []
    if not content or len(content.strip()) < 50:
        issues.append(f"File too short ({len(content)} chars)")
        return False, issues
    hard_placeholders = ['# Your code here', '# TODO', '# FIXME', 'placeholder', 'implement this']
    for placeholder in hard_placeholders:
        if placeholder.lower() in content.lower():
            issues.append(f"Contains placeholder: '{placeholder}'")
    empty_patterns = [
        r'def \w+\([^)]*\):\s*\n\s*pass\s*\n',
        r'def \w+\([^)]*\):\s*\n\s*\.\.\.\s*\n',
        r'class \w+[^:]*:\s*\n\s*pass\s*\n',
    ]
    for pattern in empty_patterns:
        if re.search(pattern, content, re.MULTILINE):
            issues.append("Contains empty function or class body")
            break
    return len(issues) == 0, issues


def _extract_write_file_content(tool_input: str) -> tuple[str | None, str | None]:
    print(f"[DEBUG RAW INPUT]\n{repr(tool_input[:800])}\n[END DEBUG]")
    path = None
    content = None

    try:
        parsed = json.loads(tool_input)
        if isinstance(parsed, dict):
            path = parsed.get("path")
            content = parsed.get("content")
            if path and content:
                return path, content
    except Exception:
        pass

    try:
        start = tool_input.find('{')
        end = tool_input.rfind('}')
        if start != -1 and end != -1:
            inner = tool_input[start:end + 1]
            fixed = inner.replace('\r\n', '\\n').replace('\r', '\\n')
            content_start = fixed.find('"content"')
            if content_start != -1:
                colon_idx = fixed.find(':', content_start)
                q_open = fixed.find('"', colon_idx + 1)
                if q_open != -1:
                    i = q_open + 1
                    buf = []
                    while i < len(fixed):
                        c = fixed[i]
                        if c == '\\' and i + 1 < len(fixed):
                            buf.append(c)
                            buf.append(fixed[i + 1])
                            i += 2
                            continue
                        if c == '"':
                            break
                        if c == '\n':
                            buf.append('\\n')
                        elif c == '\t':
                            buf.append('\\t')
                        else:
                            buf.append(c)
                        i += 1
                    content_str = ''.join(buf)
                    rebuilt = fixed[:q_open + 1] + content_str + fixed[i:]
                    parsed = json.loads(rebuilt)
                    path = parsed.get("path")
                    content = parsed.get("content")
                    if path and content:
                        return path, content
    except Exception as e:
        print(f"[DEBUG] Strategy 2 failed: {e}")

    path_match = re.search(r'"path"\s*:\s*"([^"]+)"', tool_input)
    if not path_match:
        path_match = re.search(r"'path'\s*:\s*'([^']+)'", tool_input)
    if path_match:
        path = path_match.group(1)

    content_match = re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', tool_input, re.DOTALL)
    if content_match:
        raw = content_match.group(1)
        content = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
        if content and len(content) > 20:
            return path, content

    content_match = re.search(r'"content"\s*:\s*"(.+?)"(?:\s*\}|\s*$)', tool_input, re.DOTALL)
    if content_match:
        content = content_match.group(1)
        content = content.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        if content and len(content) > 20:
            return path, content

    try:
        ci = tool_input.find('"content"')
        if ci != -1:
            colon = tool_input.find(':', ci)
            q1 = tool_input.find('"', colon + 1)
            if q1 != -1:
                last_brace = tool_input.rfind('}')
                sub = tool_input[q1 + 1:last_brace]
                q2 = sub.rfind('"')
                if q2 > 0:
                    raw = sub[:q2]
                    content = raw.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                    if content and len(content) > 20:
                        return path, content
    except Exception:
        pass

    code_match = re.search(r'```python\n(.*?)```', tool_input, re.DOTALL)
    if not code_match:
        code_match = re.search(r'```\n(.*?)```', tool_input, re.DOTALL)
    if code_match:
        content = code_match.group(1).strip()
        if not path:
            path = "script.py"
        return path, content

    return path, content


def _call_tool(tool_name: str, tool_input: str) -> str:
    if tool_name not in TOOLS_BY_NAME:
        return f"Unknown tool '{tool_name}'. Available: {TOOL_NAMES}"
    try:
        t = TOOLS_BY_NAME[tool_name]
        fixed_input = _fix_nested_json(tool_input)
        if fixed_input:
            try:
                return str(t.invoke(fixed_input))
            except Exception as e:
                print(f"[DEBUG] Fixed JSON failed: {e}")

        if tool_name == "write_file":
            path, content = _extract_write_file_content(tool_input)
            if not path or not content:
                return f"Failed to extract content. path={path is not None}, content={content is not None}"
            # Strip hallucinated sys.path injection lines
            clean_lines = [l for l in content.split("\n") 
                          if "__import__('sys').path" not in l
                          and "path.dirname(__import__" not in l]
            content = "\n".join(clean_lines)
            
            is_complete, issues = validate_complete_code(content, path)
            if not is_complete:
                issues_text = "\n".join(f"  {issue}" for issue in issues)
                return f"REJECTED - Code incomplete!\n{issues_text}\n\nWrite COMPLETE, runnable code."
            result = t.invoke({"path": path, "content": content})
            return f"{result}\n✅ Code validated: {len(content)} characters"

        try:
            parsed = json.loads(tool_input)
            if isinstance(parsed, dict):
                return str(t.invoke(parsed))
        except Exception:
            pass

        return str(t.invoke(tool_input))
    except Exception as e:
        return f"Tool error: {e}"


def _run_file(filepath: str) -> tuple[bool, str]:
    """Run a Python file. Returns (success, output)."""
    import subprocess, sys
    try:
        r = subprocess.run(
            [sys.executable, filepath],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode == 0:
            return True, r.stdout.strip() or "Ran successfully."
        else:
            return False, r.stderr.strip() or r.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout after 30s."
    except Exception as e:
        return False, str(e)


def _fix_code(filepath: str, error: str, original_request: str) -> str | None:
    """Ask mutant-coder to fix a broken file."""
    try:
        current_code = Path(filepath).read_text(encoding="utf-8")
    except Exception:
        return None

    fix_prompt = f"""Fix this Python code. It has an error.

ORIGINAL REQUEST: {original_request}

CURRENT CODE:
```python
{current_code[:2000]}
```

ERROR:
{error[:500]}

Write the COMPLETE fixed file using write_file with path: {filepath}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_AGENT_SHORT},
        {"role": "user", "content": fix_prompt},
    ]
    return generate_raw(messages, timeout_seconds=60, force_model="mutant-coder")


def verify_file_created(filepath: str) -> bool:
    if not Path(filepath).exists():
        return False
    return Path(filepath).stat().st_size > 10


def extract_filepath_from_input(value: str) -> str:
    path_match = re.search(r'"path"\s*:\s*"([^"]+)"', value)
    if path_match:
        return path_match.group(1)
    path_match = re.search(r"'path'\s*:\s*'([^']+)'", value)
    if path_match:
        return path_match.group(1)
    return None


SIMPLE_GREETINGS = {
    "hi": "Hey! I'm MutantAI 🧬 — 5 specialist models, 16 tools, image gen, self-fixing code loop. What should we build?",
    "hello": "Hello! MutantAI ready. I write code, fix my own errors, analyze molecules, generate images, search the web. What's the task?",
    "hey": "Hey! Drug discovery, app building, market analysis, image generation — what do you need? 🧬",
    "run code": "I'll test the latest Python file.",
    "test": "I'll test the code.",
}

def _is_greeting(msg: str) -> bool:
    return msg.lower().strip() in SIMPLE_GREETINGS

CURRENT_EVENTS_KEYWORDS = [
    "who is the", "who is president", "current president",
    "latest news", "what happened", "recently", "today",
    "2025", "2026", "current", "right now",
    "stock price", "weather in", "game score", "who won",
]

CODING_TASK_KEYWORDS = [
    "add feature", "add a", "modify", "update", "fix the bug",
    "improve", "extend", "integrate", "connect", "wire up",
    "refactor", "edit", "change the", "in my project",
]


def run_agent(user_message: str, history: list[dict], max_steps: int = 6):
    """
    Yields (role, content, is_tool_step).
    Flow:
    1. Greetings → instant
    2. Current events → web search
    3. Vision → /image bypass
    4. FBDD/Trader → specialist bypass
    5. Coding tasks → auto scan + write + run + fix loop (up to 3 fix attempts)
    6. Everything else → agentic tool loop
    """

    # ── 1. Greetings ──────────────────────────────────────────────────────────
    if user_message.lower().strip() == "run code":
        py_files = list(Path(".").glob("*.py"))
        if py_files:
            latest_py = max(py_files, key=lambda p: p.stat().st_mtime)
            yield "assistant", f"🔨 run_code ({latest_py})", True
            observation = _call_tool("run_code", f"exec(open('{latest_py}').read())")
            yield "tool", f"📤 {observation}", True
        else:
            yield "assistant", "No Python files found to run.", False
        return

    if _is_greeting(user_message):
        yield "assistant", SIMPLE_GREETINGS[user_message.lower().strip()], False
        return

    # ── 2. Current events → web search ────────────────────────────────────────
    if any(kw in user_message.lower() for kw in CURRENT_EVENTS_KEYWORDS):
        print("[MutantAI] Current events → web search")
        observation = _call_tool("web_search", user_message)
        yield "tool", f"📤 {observation}", True
        lines = [l.strip() for l in observation.split("\n")
                 if l.strip() and not l.startswith("http") and not l.startswith("__")]
        summary = " ".join(lines[:6])[:500]
        yield "assistant", f"🌐 {summary}", False
        return

    # ── 3. Vision bypass ──────────────────────────────────────────────────────
    if user_message.startswith("/image "):
        parts = user_message.split("\n", 1)
        image_path = parts[0].replace("/image ", "").strip()
        prompt = parts[1].strip() if len(parts) > 1 else "Describe this image in detail."
        try:
            import requests, base64
            from PIL import Image as PILImage
            import io
            img = PILImage.open(image_path)
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode()
            response = requests.post("http://localhost:11434/api/chat", json={
                "model": "mutant-vision",
                "messages": [{"role": "user", "content": prompt, "images": [img_b64]}],
                "stream": False,
            }, timeout=300)
            resp_json = response.json()
            result = resp_json.get("message", {}).get("content", str(resp_json))
            yield "assistant", f"👁️ VISION · {result}", False
        except Exception as e:
            yield "assistant", f"Vision error: {e}", False
        return

    # ── 4. Specialist bypass (FBDD / Trader) ──────────────────────────────────
    bypass_model = should_bypass_agent(user_message)
    if bypass_model:
        print(f"[MutantAI] Specialist bypass → {bypass_model}")
        system_prompt = SPECIALIST_PROMPTS.get(bypass_model, "You are a helpful expert.")
        messages = [{"role": "system", "content": system_prompt}]
        messages += history[-4:]
        messages.append({"role": "user", "content": user_message})
        try:
            response = generate_raw(messages, timeout_seconds=120, force_model=bypass_model)
            label = "🧬 FBDD" if bypass_model == "mutant-fbdd" else "📈 TRADER"
            yield "assistant", f"{label} · {response}", False
        except Exception as e:
            yield "assistant", f"Specialist error: {e}", False
        return

    # ── 5. Auto project scan for modification tasks ────────────────────────────
    needs_scan = any(kw in user_message.lower() for kw in CODING_TASK_KEYWORDS)
    project_context = ""
    if needs_scan:
        print("[MutantAI] Auto-scanning project...")
        yield "assistant", "🗂️ Scanning project for context...", True
        scan_result = _call_tool("scan_project", ".")
        project_context = f"\n\nPROJECT CONTEXT:\n{scan_result[:2000]}"
        yield "tool", f"📤 Project scanned — context loaded", True

    # ── 6. Agentic tool loop with run-and-fix ─────────────────────────────────
    messages = [{"role": "system", "content": SYSTEM_PROMPT_AGENT_SHORT}]
    messages += history[-4:]
    messages.append({"role": "user", "content": user_message + project_context})

    scratchpad = ""
    files_created = set()
    completed_actions = set()
    step = 0

    while step < max_steps:
        print(f"\n[DEBUG] Step {step + 1}")

        try:
            if scratchpad:
                ctx = messages.copy()
                ctx[-1] = {"role": "user", "content": user_message + project_context + "\n\n[Progress]\n" + scratchpad}
                response = generate_raw(ctx, timeout_seconds=90)
            else:
                response = generate_raw(messages, timeout_seconds=90)
        except Exception as e:
            yield "assistant", f"Error: {e}. Try a simpler request.", False
            return

        print(f"[DEBUG] Response length: {len(response)}")

        has_code = '```python' in response or 'def ' in response or 'import ' in response
        has_write_file = 'Action: write_file' in response or 'Action:write_file' in response

        if has_code and not has_write_file and len(response) < 500:
            yield "assistant", response, False
            return

        parsed_items = _parse_response(response)
        actions = [p for p in parsed_items if p[0] == "action"]

        if not actions:
            if len(response) > 20 and step == 0:
                yield "assistant", response, False
            else:
                yield "assistant", "Task completed.", False
            return

        action_executed = False
        for kind, tool_name, value in actions:
            action_key = f"{tool_name}_{value[:100]}"
            if action_key in completed_actions:
                continue

            yield "assistant", f"🔨 {tool_name}", True
            observation = _call_tool(tool_name, value)

            # ── Run-and-fix loop ───────────────────────────────────────────
            if tool_name == "write_file" and "REJECTED" not in observation and "Failed" not in observation:
                filepath = extract_filepath_from_input(value)
                if filepath and verify_file_created(filepath):
                    files_created.add(filepath)
                    size = Path(filepath).stat().st_size
                    observation += f"\n✅ Verified: {filepath} ({size} bytes)"
                    yield "tool", f"📤 {observation}", True

                    # Only auto-run pure Python scripts, not Streamlit/Flask apps
                    is_runnable = (filepath.endswith(".py") and
                                   not any(skip in filepath for skip in
                                           ["app.py", "streamlit", "flask", "fastapi"]))

                    if is_runnable:
                        yield "assistant", f"▶️ Testing {filepath}...", True
                        success, run_output = _run_file(filepath)

                        if success:
                            yield "tool", f"📤 ✅ Runs correctly:\n{run_output[:300]}", True
                            yield "assistant", f"✅ `{filepath}` works!\n```\n{run_output[:200]}\n```", False
                            return
                        else:
                            yield "tool", f"📤 ❌ Error:\n{run_output[:300]}", True

                            fixed = False
                            for attempt in range(1, 4):
                                yield "assistant", f"🔧 Auto-fixing (attempt {attempt}/3)...", True
                                fix_response = _fix_code(filepath, run_output, user_message)

                                if fix_response:
                                    fix_actions = [p for p in _parse_response(fix_response) if p[0] == "action"]
                                    for _, ft, fv in fix_actions:
                                        if ft == "write_file":
                                            fix_obs = _call_tool("write_file", fv)
                                            yield "tool", f"📤 {fix_obs}", True
                                            success, run_output = _run_file(filepath)
                                            if success:
                                                yield "tool", f"📤 ✅ Fixed!\n{run_output[:200]}", True
                                                yield "assistant", f"✅ Fixed after {attempt} attempt(s)!\n```\n{run_output[:150]}\n```", False
                                                fixed = True
                                                break
                                            else:
                                                yield "tool", f"📤 ❌ Attempt {attempt} failed:\n{run_output[:150]}", True
                                if fixed:
                                    return

                            if not fixed:
                                yield "assistant", f"⚠️ Could not auto-fix after 3 attempts.\nLast error:\n```\n{run_output[:300]}\n```", False
                                return
                    else:
                        yield "assistant", f"✅ Created `{filepath}`", False
                        return

                    completed_actions.add(action_key)
                    action_executed = True
                    scratchpad += f"\n{tool_name}: {observation[:200]}\n"
                    continue

            completed_actions.add(action_key)
            action_executed = True
            yield "tool", f"📤 {observation}", True
            scratchpad += f"\n{tool_name}: {observation[:200]}\n"

            if tool_name == "generate_image" and "✅" in observation:
                yield "assistant", "🎨 Image created!", False
                return
            if tool_name == "scaffold_project" and "✅" in observation:
                yield "assistant", "🏗️ Project scaffolded! Check the folder and run the app.", False
                return
            if tool_name == "learn_from_app" and "✅" in observation:
                yield "assistant", "🎓 Template learned! Use it with scaffold_project.", False
                return

        step += 1

        if action_executed and files_created:
            yield "assistant", f"✅ Created: {', '.join(files_created)}", False
            return

    if files_created:
        yield "assistant", f"✅ Done! Created: {', '.join(files_created)}", False
    else:
        yield "assistant", "Task completed.", False


SYSTEM_PROMPT_AGENT_SHORT = """You are MutantAI-Coder, an expert coding assistant that writes COMPLETE, runnable code.

IMPORTANT TOOL ROUTING:
- To scaffold/create/build a SPECIFIC named app → use scaffold_project
- To generate/create/make an image → use generate_image
- To DESCRIBE or LIST what apps can be built → answer directly without tools
- To list templates → use list_templates
- To learn from a working app → use learn_from_app
- To write a code file → use write_file

TOOL FORMAT:

scaffold_project:
Action: scaffold_project
Action Input: name=MyApp template=streamlit-drug

generate_image:
Action: generate_image
Action Input: 3D molecular structure dark background scientific

learn_from_app:
Action: learn_from_app
Action Input: path=./physicschemv2 name=drug-dashboard-v2

write_file:
Action: write_file
Action Input: {"path": "script.py", "content": "import os\\nprint('hello')\\n"}

CRITICAL RULES for write_file:
- Action Input must be valid JSON on ONE LINE
- Use \\n for newlines inside content string
- Never truncate or use placeholders like # TODO
- Always include if __name__ == '__main__' block
- Write COMPLETE, immediately runnable code
"""