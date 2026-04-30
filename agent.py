"""
agent.py — MutantAI Agent v2
Adds specialist bypass: FBDD and trader queries skip the tool loop
and go directly to the domain expert for pure reasoning.
"""

import json
import re
import os
from pathlib import Path
from model import generate_raw, should_bypass_agent
from tools import TOOLS_BY_NAME, ALL_TOOLS
from memory import remember_decision, remember_error

TOOL_NAMES = ", ".join(TOOLS_BY_NAME.keys())

# ── Specialist system prompts for bypass mode ─────────────────────────────────
SPECIALIST_PROMPTS = {
    "mutant-fbdd": """You are MutantAI-FBDD, an expert computational medicinal chemist specializing in FBDD.
Analyze molecules step by step: properties → pharmacophore → affinity prediction → ADMET → recommendations.
Key knowledge: EGFR top leads -10.08 kcal/mol, HIV Integrase -9.708 kcal/mol, HIV Protease CURE_17G_002 -7.753 kcal/mol.
Give direct scientific reasoning. Do NOT write code.""",
    "mutant-trader": """You are MutantAI-Trader, an expert in sports betting and financial markets.
Your expertise: NFL analysis, horse racing, DraftKings fantasy, Kelly criterion,
crypto/DeFi analysis, XRPL, value identification, bankroll management.
Give direct analysis and actionable recommendations.
Always include: edge identification, risk quantification, position sizing, exit criteria.
Be honest about uncertainty. Never chase losses.""",
}


def _parse_response(text: str):
    """Parse model response - handles Action/Action Input pairs."""
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
                print(f"[DEBUG] Strategy 1 succeeded: {len(content)} chars")
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
                        print(f"[DEBUG] Strategy 2 succeeded: {len(content)} chars")
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
            print(f"[DEBUG] Strategy 3a succeeded: {len(content)} chars")
            return path, content

    content_match = re.search(r'"content"\s*:\s*"(.+?)"(?:\s*\}|\s*$)', tool_input, re.DOTALL)
    if content_match:
        content = content_match.group(1)
        content = content.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
        if content and len(content) > 20:
            print(f"[DEBUG] Strategy 3b succeeded: {len(content)} chars")
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
                        print(f"[DEBUG] Strategy 3c succeeded: {len(content)} chars")
                        return path, content
    except Exception as e:
        print(f"[DEBUG] Strategy 3c failed: {e}")

    code_match = re.search(r'```python\n(.*?)```', tool_input, re.DOTALL)
    if not code_match:
        code_match = re.search(r'```\n(.*?)```', tool_input, re.DOTALL)
    if code_match:
        content = code_match.group(1).strip()
        if not path:
            path = "script.py"
        print(f"[DEBUG] Strategy 4 succeeded: {len(content)} chars")
        return path, content

    print(f"[DEBUG] All strategies failed. path={path}, content={len(content) if content else 0}")
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
                return (
                    f"❌ Failed to extract content.\n"
                    f"  path found: {path is not None}\n"
                    f"  content found: {content is not None}\n"
                    f"  raw length: {len(tool_input)}"
                )
            is_complete, issues = validate_complete_code(content, path)
            if not is_complete:
                issues_text = "\n".join(f"  ⚠️ {issue}" for issue in issues)
                return f"❌ REJECTED - Code incomplete!\n{issues_text}\n\nPlease write COMPLETE, runnable code."
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
    "hi": "Hey! I'm MutantAI 🧬 — multi-model agent brain. I can analyze molecules, write code, analyze markets, and see images. What do you need?",
    "hello": "Hello! MutantAI ready. I route your request to the right specialist — FBDD, Coder, Trader, or Vision. What should we work on?",
    "hey": "Hey! Give me a task — drug discovery, coding, betting analysis, or show me an image 🧬",
    "run code": "I'll test the latest Python file.",
    "test": "I'll test the code.",
}

def _is_greeting(msg: str) -> bool:
    return msg.lower().strip() in SIMPLE_GREETINGS


def run_agent(user_message: str, history: list[dict], max_steps: int = 5):
    """
    Yields (role, content, is_tool_step).
    
    Flow:
    1. Greetings → instant response
    2. FBDD/Trader queries → specialist bypass (direct reasoning, no tools)
    3. Everything else → full agentic tool loop with mutant-coder
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
    # Vision bypass — /image prefix
    if user_message.startswith("/image "):
        parts = user_message.split("\n", 1)
        image_path = parts[0].replace("/image ", "").strip()
        prompt = parts[1].strip() if len(parts) > 1 else "Describe this image in detail."
        try:
            import requests, base64
            from PIL import Image
            import io
            img = Image.open(image_path)
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
            if "message" in resp_json:
                result = resp_json["message"]["content"]
            elif "error" in resp_json:
                result = f"Model error: {resp_json['error']}"
            else:
                result = str(resp_json)
            yield "assistant", f"👁️ VISION · {result}", False
        except Exception as e:
            yield "assistant", f"Vision error: {e}", False
        return



    # ── 1.5 General knowledge — use web search for current events ──────────
    CURRENT_EVENTS_KEYWORDS = [
        "who is the", "who is president", "current president",
        "latest news", "what happened", "recently", "today",
        "2024", "2025", "2026", "current", "right now",
        "stock price", "weather", "score", "winner",
    ]
    if any(kw in user_message.lower() for kw in CURRENT_EVENTS_KEYWORDS):
        print("[MutantAI] Current events → web search")
        observation = _call_tool("web_search", user_message)
        yield "tool", f"📤 {observation}", True
        # Extract answer from search results directly
        lines = [l.strip() for l in observation.split("\n") if l.strip() and not l.startswith("http")]
        summary = " ".join(lines[:5])[:400]
        yield "assistant", f"Based on web search: {summary}", False
        return

    # ── 2. Specialist bypass (FBDD / Trader) ──────────────────────────────────
    bypass_model = should_bypass_agent(user_message)
    if bypass_model:
        print(f"[MutantAI] Specialist bypass → {bypass_model}")
        system_prompt = SPECIALIST_PROMPTS.get(bypass_model, "You are a helpful expert assistant.")
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        # Include recent history for context
        messages += history[-4:]
        messages.append({"role": "user", "content": user_message})

        try:
            response = generate_raw(messages, timeout_seconds=120, force_model=bypass_model)
            model_label = "🧬 FBDD" if bypass_model == "mutant-fbdd" else "📈 TRADER"
            yield "assistant", f"{model_label} · {response}", False
        except Exception as e:
            yield "assistant", f"Specialist error: {e}", False
        return

    # ── 3. Full agentic tool loop (mutant-coder) ──────────────────────────────
    messages = [{"role": "system", "content": SYSTEM_PROMPT_AGENT_SHORT}]
    messages += history[-4:]
    messages.append({"role": "user", "content": user_message})

    scratchpad = ""
    files_created = set()
    completed_actions = set()
    rejected_files = set()
    step = 0

    while step < max_steps:
        print(f"\n[DEBUG] Step {step + 1}")

        try:
            if scratchpad:
                ctx = messages.copy()
                ctx[-1] = {"role": "user", "content": user_message + "\n\n[Progress]\n" + scratchpad}
                response = generate_raw(ctx, timeout_seconds=45)
            else:
                response = generate_raw(messages, timeout_seconds=45)
        except Exception as e:
            yield "assistant", f"Error: {e}. Please try a simpler request.", False
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
                yield "assistant", "Please specify what you'd like me to create.", False
            return

        action_executed = False
        for kind, tool_name, value in actions:
            action_key = f"{tool_name}_{value[:100]}"
            if action_key in completed_actions:
                continue

            if tool_name == "write_file":
                filepath = extract_filepath_from_input(value)
                if filepath and filepath in rejected_files:
                    yield "tool", f"⏭️ File {filepath} was rejected.", True
                    continue

            yield "assistant", f"🔨 {tool_name}", True
            observation = _call_tool(tool_name, value)

            if tool_name == "write_file" and "REJECTED" not in observation and "Failed" not in observation:
                filepath = extract_filepath_from_input(value)
                if filepath and verify_file_created(filepath):
                    files_created.add(filepath)
                    size = Path(filepath).stat().st_size
                    observation += f"\n✅ File verified: {filepath} ({size} bytes)"

            completed_actions.add(action_key)
            action_executed = True
            yield "tool", f"📤 {observation}", True
            scratchpad += f"\n{tool_name}: {observation[:200]}\n"

            # Auto-complete for generation tools
            if tool_name == "generate_image" and "✅" in observation:
                yield "assistant", "🎨 Image created! Prompt saved to generated_images folder.", False
                return
            if tool_name == "scaffold_project" and "✅" in observation:
                yield "assistant", f"🏗️ Project scaffolded! Check the folder and run the app.", False
                return

        step += 1

        if action_executed and files_created:
            yield "assistant", f"✅ Created: {', '.join(files_created)}", False
            return

    if files_created:
        yield "assistant", f"✅ Done! Created: {', '.join(files_created)}", False
    else:
        yield "assistant", "Task completed.", False


SYSTEM_PROMPT_AGENT_SHORT = """You are MutantAI-Coder, an expert coding assistant and app builder.

IMPORTANT TOOL ROUTING:
- To scaffold/create/build a SPECIFIC named app → use scaffold_project
- To LIST or DESCRIBE what apps can be built → answer directly without tools
- To generate/create/make an image → use generate_image
- To list available templates → use list_templates  
- To learn from a working app → use learn_from_app
- To write a code file → use write_file

TOOL FORMAT — Action Input is always a plain STRING, never JSON:

scaffold_project:
Action: scaffold_project
Action Input: name=MutantDrug template=streamlit-drug

list_templates:
Action: list_templates
Action Input: all

learn_from_app:
Action: learn_from_app
Action Input: path=./physicschemv2 name=drug-dashboard-v2

generate_image:
Action: generate_image
Action Input: 3D molecular structure HIV protease inhibitor dark background scientific

write_file:
Action: write_file
Action Input: {"path": "app.py", "content": "import streamlit as st\\nst.title('Hello')\\n"}

CRITICAL RULES for write_file only:
- Action Input must be valid JSON on ONE LINE
- Use \\n for newlines inside content string
- Never use placeholders like # TODO
"""