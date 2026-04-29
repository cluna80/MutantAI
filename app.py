"""
app.py — Mutant AI Streamlit Interface v2
Features: project memory panel, tools, agentic UI, Plan-Write-Test-Fix-Deliver workflow
Run: streamlit run app.py
"""
import os
os.environ["SSL_CERT_FILE"] = __import__("certifi").where()
import streamlit as st
from agent import run_agent
from memory import get_memory_context, remember_project, remember_preference, clear_memory
from dotenv import load_dotenv
load_dotenv()

# ── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mutant AI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
    background-color: #0a0a0f;
    color: #e0e0e0;
}
[data-testid="stSidebar"] {
    background: #0d0d1a;
    border-right: 1px solid #1f1f3a;
}
.mutant-title {
    font-family: 'Share Tech Mono', monospace;
    font-size: 2.2rem;
    color: #00ffcc;
    text-shadow: 0 0 20px #00ffcc88;
    letter-spacing: 4px;
    margin-bottom: 0;
}
.mutant-sub {
    color: #666;
    font-size: 0.85rem;
    letter-spacing: 2px;
    margin-top: 0;
    font-family: 'Share Tech Mono', monospace;
}
.msg-user {
    background: #12122a;
    border-left: 3px solid #7b5ea7;
    padding: 14px 18px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
}
.msg-assistant {
    background: #0d1a15;
    border-left: 3px solid #00ffcc;
    padding: 14px 18px;
    border-radius: 0 8px 8px 0;
    margin: 10px 0;
}
.msg-tool {
    background: #1a1a0d;
    border-left: 3px solid #ffcc00;
    padding: 10px 14px;
    border-radius: 0 6px 6px 0;
    margin: 6px 0 6px 20px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.78rem;
    color: #aaa;
    white-space: pre-wrap;
    word-break: break-word;
}
.badge-user  { color: #7b5ea7; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.badge-ai    { color: #00ffcc; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.badge-tool  { color: #ffcc00; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.memory-box  {
    background: #0d0d1a;
    border: 1px solid #1f1f3a;
    border-radius: 6px;
    padding: 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.72rem;
    color: #888;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
}
.stButton > button {
    background: linear-gradient(135deg, #00ffcc22, #7b5ea722);
    border: 1px solid #00ffcc55;
    color: #00ffcc;
    font-family: 'Share Tech Mono', monospace;
    letter-spacing: 2px;
    font-size: 0.8rem;
    padding: 8px 20px;
    border-radius: 4px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00ffcc44, #7b5ea744);
    border-color: #00ffcc;
    box-shadow: 0 0 12px #00ffcc44;
}
hr { border-color: #1f1f3a; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #00ffcc44; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ── Simple greeting handler ────────────────────────────────────────────────
SIMPLE_GREETINGS = {
    "hi": "Hey! 👋 I'm Mutant AI. Give me a coding task and I'll **plan it → write it → test it → fix it → deliver it**. What should we build? 🚀",
    "hello": "Hello! Ready to code? Tell me what to build and I'll follow my **Plan → Write → Test → Fix → Deliver** workflow. 💻",
    "hey": "Hey! Need some code? Just describe what you want to build! 🔥",
    "sup": "Sup? Give me a coding challenge! 🧬",
    "good morning": "Morning! Ready to build something awesome? 💪",
    "good evening": "Evening! Let's write some code. What's the task? 🌙",
}

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="mutant-title">🧬 MUTANT</p>', unsafe_allow_html=True)
    st.markdown('<p class="mutant-sub">// autonomous coding agent</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**⚡ ACTIVE TOOLS (11)**")
    tools_list = [
        ("🐍", "run_code", "Execute Python"),
        ("💻", "run_shell", "npm / pip / git"),
        ("📂", "read_file", "Read files"),
        ("✏️", "write_file", "Write files"),
        ("🩹", "patch_file", "Surgical edits"),
        ("📁", "list_dir", "Browse dirs"),
        ("🗂️", "scan_project", "Scan codebase"),
        ("🌐", "web_search", "DuckDuckGo"),
        ("📋", "plan_coding_task", "Plan first!"),
        ("💾", "save_memory", "Save context"),
        ("🧠", "get_memory", "Recall context"),
    ]
    for icon, name, desc in tools_list:
        st.markdown(f"{icon} `{name}` — {desc}")

    st.markdown("---")

    # Project Memory Panel
    st.markdown("**🧠 PROJECT MEMORY**")
    mem = get_memory_context()
    st.markdown(f'<div class="memory-box">{mem}</div>', unsafe_allow_html=True)

    with st.expander("➕ Add memory"):
        mem_key = st.text_input("Key (e.g. framework)", key="mem_key")
        mem_val = st.text_input("Value (e.g. React + FastAPI)", key="mem_val")
        if st.button("💾 Save"):
            if mem_key and mem_val:
                remember_project(mem_key, mem_val)
                st.success(f"Saved: {mem_key}")
                st.rerun()

    if st.button("🗑️ Clear Memory"):
        clear_memory()
        st.rerun()

    st.markdown("---")

    # Example prompts
    st.markdown("**💡 EXAMPLE PROMPTS**")
    examples = [
        "Scan my project and give me an overview",
        "Write a Python function that calculates Fibonacci numbers",
        "Create a simple web server with Flask",
        "Fix the bug in app.py",
        "Remember that I'm using React + Tailwind",
    ]
    for ep in examples:
        if st.button(ep, key=ep):
            st.session_state["prefill"] = ep

    st.markdown("---")
    if st.button("🗑️ CLEAR CHAT"):
        st.session_state.messages = []
        st.session_state.history = []
        st.rerun()

# ── State ──────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []
if "workflow_reminded" not in st.session_state:
    st.session_state.workflow_reminded = False

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown('<h1 class="mutant-title">🧬 MUTANT AI</h1>', unsafe_allow_html=True)
st.markdown('<p class="mutant-sub">// mutant-coder · mutant-fbdd · mutant-vision · mutant-trader · 11 Tools · Memory · Local</p>', unsafe_allow_html=True)
st.markdown("---")

# ── Workflow reminder (first message only) ─────────────────────────────────
if not st.session_state.workflow_reminded and not st.session_state.messages:
    st.info("💡 **Mutant AI now follows: PLAN → WRITE → TEST → FIX → DELIVER**\n\nFor coding tasks, I'll plan first, then write code, test it, fix any errors, and deliver working code. Just tell me what to build!")
    st.session_state.workflow_reminded = True

# ── Chat Display ───────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    role, content = msg["role"], msg["content"]
    if role == "user":
        st.markdown('<p class="badge-user">▸ YOU</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-user">{content}</div>', unsafe_allow_html=True)
    elif role == "assistant":
        st.markdown('<p class="badge-ai">▸ MUTANT AI</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-assistant">{content}</div>', unsafe_allow_html=True)
    elif role == "tool":
        st.markdown('<p class="badge-tool">⚙ TOOL</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="msg-tool">{content}</div>', unsafe_allow_html=True)

# ── Input ──────────────────────────────────────────────────────────────────
st.markdown("---")
prefill = st.session_state.pop("prefill", "")
user_input = st.text_area(
    "Message",
    value=prefill,
    placeholder="Ask Mutant AI to build, fix, or code anything. I'll plan it, write it, test it, and deliver it!",
    height=100,
    label_visibility="collapsed",
)

col_send, _ = st.columns([1, 5])
with col_send:
    send = st.button("⚡ SEND", use_container_width=True)

if send and user_input.strip():
    user_msg = user_input.strip()
    
    # Check for simple greetings FIRST
    greeting_response = SIMPLE_GREETINGS.get(user_msg.lower().strip())
    if greeting_response:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        st.session_state.messages.append({"role": "assistant", "content": greeting_response})
        st.session_state.history.append({"role": "user", "content": user_msg})
        st.session_state.history.append({"role": "assistant", "content": greeting_response})
        st.rerun()
    
    # Otherwise run the agent
    st.session_state.messages.append({"role": "user", "content": user_msg})

    with st.spinner("🧬 Mutant AI planning and coding..."):
        for role, content, is_tool_step in run_agent(user_msg, st.session_state.history):
            st.session_state.messages.append({"role": role, "content": content})
            if role == "assistant" and not is_tool_step:
                st.session_state.history.append({"role": "user", "content": user_msg})
                st.session_state.history.append({"role": "assistant", "content": content})

    st.rerun()