#!/bin/bash
# Patch app.py to add image upload for mutant-vision
# Run from mutant_ai_starter folder: bash app_patch.sh

python3 - << 'PYEOF'
content = open('app.py', encoding='utf-8').read()

# 1. Add Path import after load_dotenv
content = content.replace(
    'from dotenv import load_dotenv\nload_dotenv()',
    'from dotenv import load_dotenv\nfrom pathlib import Path\nimport tempfile\nload_dotenv()'
)

# 2. Replace the input section
old_input = '''# ── Input ──────────────────────────────────────────────────────────────────
st.markdown("---")
prefill = st.session_state.pop("prefill", "")
user_input = st.text_area(
    "Message",
    value=prefill,
    placeholder="scaffold an app · analyze a molecule · write code · ask about markets · show me an image",
    height=100,
    label_visibility="collapsed",
)

col_send, _ = st.columns([1, 5])
with col_send:
    send = st.button("⚡ SEND", use_container_width=True)'''

new_input = '''# ── Input ──────────────────────────────────────────────────────────────────
st.markdown("---")
prefill = st.session_state.pop("prefill", "")

# Image upload for mutant-vision
uploaded_file = st.file_uploader(
    "📎 Attach image for mutant-vision (optional)",
    type=["png", "jpg", "jpeg", "gif", "webp"],
    label_visibility="visible",
)
if uploaded_file:
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
    send = st.button("⚡ SEND", use_container_width=True)'''

content = content.replace(old_input, new_input)

# 3. Patch send handler to inject image path
old_send = 'if send and user_input.strip():\n    user_msg = user_input.strip()'
new_send = '''if send and (user_input.strip() or st.session_state.get("image_path")):
    user_msg = user_input.strip() or "What do you see in this image? Describe it in detail."
    image_path = st.session_state.pop("image_path", None)
    if image_path:
        user_msg = f"/image {image_path}\\n{user_msg}"'''

content = content.replace(old_send, new_send)

open('app.py', 'w', encoding='utf-8').write(content)
print("✅ app.py patched successfully!")
PYEOF
