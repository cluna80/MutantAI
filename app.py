"""
app.py — MutantAI Streamlit Interface v2
Multi-model brain: mutant-coder · mutant-fbdd · mutant-vision · mutant-trader
15 Tools · Memory · Scaffold App Builder · Self-Learning Loop
Run: streamlit run app.py
"""
import os
os.environ["SSL_CERT_FILE"] = __import__("certifi").where()
import streamlit as st
from agent import run_agent
from memory import get_memory_context, remember_project, clear_memory
from dotenv import load_dotenv
from pathlib import Path
import tempfile
load_dotenv()

st.set_page_config(
    page_title="MutantAI",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Rajdhani', sans-serif; background-color: #0a0a0f; color: #e0e0e0; }
[data-testid="stSidebar"] { background: #0d0d1a; border-right: 1px solid #1f1f3a; }
.mutant-title { font-family: 'Share Tech Mono', monospace; font-size: 2.2rem; color: #00ffcc; text-shadow: 0 0 20px #00ffcc88; letter-spacing: 4px; margin-bottom: 0; }
.mutant-sub { color: #666; font-size: 0.85rem; letter-spacing: 2px; margin-top: 0; font-family: 'Share Tech Mono', monospace; }
.msg-user { background: #12122a; border-left: 3px solid #7b5ea7; padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 10px 0; }
.msg-assistant { background: #0d1a15; border-left: 3px solid #00ffcc; padding: 14px 18px; border-radius: 0 8px 8px 0; margin: 10px 0; }
.msg-tool { background: #1a1a0d; border-left: 3px solid #ffcc00; padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 6px 0 6px 20px; font-family: 'Share Tech Mono', monospace; font-size: 0.78rem; color: #aaa; white-space: pre-wrap; word-break: break-word; }
.badge-user { color: #7b5ea7; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.badge-ai { color: #00ffcc; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.badge-tool { color: #ffcc00; font-size: 0.7rem; letter-spacing: 2px; font-family: 'Share Tech Mono', monospace; }
.memory-box { background: #0d0d1a; border: 1px solid #1f1f3a; border-radius: 6px; padding: 10px; font-family: 'Share Tech Mono', monospace; font-size: 0.72rem; color: #888; white-space: pre-wrap; max-height: 200px; overflow-y: auto; }
.stButton > button { background: linear-gradient(135deg, #00ffcc22, #7b5ea722); border: 1px solid #00ffcc55; color: #00ffcc; font-family: 'Share Tech Mono', monospace; letter-spacing: 2px; font-size: 0.8rem; padding: 8px 20px; border-radius: 4px; transition: all 0.2s; }
.stButton > button:hover { background: linear-gradient(135deg, #00ffcc44, #7b5ea744); border-color: #00ffcc; box-shadow: 0 0 12px #00ffcc44; }
hr { border-color: #1f1f3a; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #00ffcc44; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

SIMPLE_GREETINGS = {
    "hi": "Hey! 👋 I'm MutantAI — multi-model agent brain. I can build apps, analyze molecules, write code, and analyze markets. What should we build? 🚀",
    "hello": "Hello! MutantAI ready. Tell me what to build — I'll scaffold it, code it, test it, and deliver it. 💻",
    "hey": "Hey! Drug discovery, app building, market analysis — what's the task? 🧬",
    "sup": "Sup? Give me a challenge! 🧬",
    "good morning": "Morning! Ready to build something awesome? 💪",
    "good evening": "Evening! Let's build. What's the task? 🌙",
}

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    logo_path = "generated_images/generated_1777473810.png"
    import os
    if os.path.exists(logo_path):
        st.image(logo_path, width=120)
    else:
        st.markdown('<p class="mutant-title">🧬 MUTANT</p>', unsafe_allow_html=True)
    st.markdown('<p class="mutant-sub">// multi-model agent brain</p>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("**🤖 ACTIVE MODELS**")
    st.markdown("🧬 `mutant-fbdd` — Drug discovery")
    st.markdown("💻 `mutant-coder` — Code generation")
    st.markdown("👁️ `mutant-vision` — Image analysis")
    st.markdown("📈 `mutant-trader` — Markets & betting")
    st.markdown("---")

    st.markdown("**⚡ ACTIVE TOOLS (16)**")
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
        ("🏗️", "scaffold_project", "Build full apps"),
        ("📚", "list_templates", "List templates"),
        ("🎓", "learn_from_app", "Learn from code"),
        ("🕒", "get_current_time", "Current time"),
        ("🎨", "generate_image", "Generate images"),
    ]
    for icon, name, desc in tools_list:
        st.markdown(f"{icon} `{name}` — {desc}")

    st.markdown("---")

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

    st.markdown("**💡 EXAMPLE PROMPTS**")
    examples = [
        "scaffold a drug discovery app called MyDrug",
        "predict binding affinity for SMILES CCOc1cc2ncnc against EGFR",
        "write a FastAPI endpoint for SMILES analysis",
        "list templates",
        "what makes a good NFL value bet",
        "scan my project and give me an overview",
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
st.markdown('<p class="mutant-sub">// mutant-coder · mutant-fbdd · mutant-vision · mutant-trader · 15 Tools · Memory · Local</p>', unsafe_allow_html=True)
st.markdown("---")

if not st.session_state.workflow_reminded and not st.session_state.messages:
    st.info("💡 **MutantAI v2** — Multi-model agent brain with 4 specialists and 15 tools.\n\nTry: *scaffold a drug discovery app* · *analyze this SMILES* · *what's a good NFL bet* · *build a FastAPI endpoint*")
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
        # Show generated images inline
        if "generated_images" in content and ".png" in content:
            import re
            paths = re.findall(r'C:\\[^\s]+\.png', content)
            for p in paths:
                try:
                    st.image(p, use_container_width=True)
                except:
                    pass

# ── Input ──────────────────────────────────────────────────────────────────
st.markdown("---")
prefill = st.session_state.pop("prefill", "")

uploaded_file = st.file_uploader("📎 Attach image for mutant-vision", type=["png","jpg","jpeg","webp"], label_visibility="visible")
if uploaded_file:
    from pathlib import Path
    import tempfile
    st.image(uploaded_file, width=250)
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        st.session_state["image_path"] = tmp.name
    st.caption(f"📎 {uploaded_file.name} attached — mutant-vision will analyze it")
user_input = st.text_area(
    "Message",
    value=prefill,
    placeholder="scaffold an app · analyze a molecule · write code · ask about markets · describe this image",
    height=100,
    label_visibility="collapsed",
)

col_send, _ = st.columns([1, 5])
with col_send:
    send = st.button("⚡ SEND", use_container_width=True)

if send and (user_input.strip() or st.session_state.get("image_path")):
    user_msg = user_input.strip() or "What do you see? Describe in detail."
    image_path = st.session_state.pop("image_path", None)
    if image_path:
        user_msg = f"/image {image_path}\n{user_msg}"

    greeting_response = SIMPLE_GREETINGS.get(user_msg.lower().strip())
    if greeting_response:
        st.session_state.messages.append({"role": "user", "content": user_msg})
        st.session_state.messages.append({"role": "assistant", "content": greeting_response})
        st.session_state.history.append({"role": "user", "content": user_msg})
        st.session_state.history.append({"role": "assistant", "content": greeting_response})
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": user_msg})

    with st.spinner("🧬 MutantAI thinking..."):
        for role, content, is_tool_step in run_agent(user_msg, st.session_state.history):
            st.session_state.messages.append({"role": role, "content": content})
            if role == "assistant" and not is_tool_step:
                st.session_state.history.append({"role": "user", "content": user_msg})
                st.session_state.history.append({"role": "assistant", "content": content})

    st.rerun()