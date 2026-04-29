"""
custom_tools.py — MutantAI App Builder Tools
Scaffold, learn, and build full-stack apps from description.
Uses APP_NAME placeholder instead of .format() to avoid brace conflicts.
"""

from langchain_core.tools import tool
from pathlib import Path
import json

# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATES = {

    "streamlit": {
        "description": "Streamlit data app / dashboard",
        "files": {
            "app.py": 'import streamlit as st\nimport pandas as pd\n\nst.set_page_config(page_title="APP_NAME", page_icon="🧬", layout="wide")\nst.title("🧬 APP_NAME")\nst.markdown("---")\nst.write("Hello from MutantAI!")\n',
            "requirements.txt": "streamlit\npandas\nplotly\n",
            "README.md": "# APP_NAME\n\nBuilt with MutantAI.\n\n## Run\n```bash\nstreamlit run app.py\n```\n",
        },
        "run_cmd": "streamlit run app.py",
    },

    "streamlit-drug": {
        "description": "Drug discovery Streamlit dashboard with RDKit",
        "files": {
            "app.py": (
                'import streamlit as st\n'
                'from rdkit import Chem\n'
                'from rdkit.Chem import Draw, Descriptors, QED, rdMolDescriptors\n'
                '\n'
                'st.set_page_config(page_title="APP_NAME", page_icon="🧬", layout="wide")\n'
                'st.markdown("<style>html,body,[class*=\'css\']{background:#0a0a0f;color:#e0e0e0}</style>", unsafe_allow_html=True)\n'
                'st.title("🧬 APP_NAME")\n'
                'st.markdown("---")\n'
                '\n'
                'def mol_to_image(smiles):\n'
                '    mol = Chem.MolFromSmiles(smiles)\n'
                '    return Draw.MolToImage(mol, size=(400, 300)) if mol else None\n'
                '\n'
                'def get_properties(smiles):\n'
                '    mol = Chem.MolFromSmiles(smiles)\n'
                '    if not mol: return {}\n'
                '    return {\n'
                '        "MW": round(Descriptors.MolWt(mol), 2),\n'
                '        "LogP": round(Descriptors.MolLogP(mol), 2),\n'
                '        "HBD": rdMolDescriptors.CalcNumHBD(mol),\n'
                '        "HBA": rdMolDescriptors.CalcNumHBA(mol),\n'
                '        "QED": round(QED.qed(mol), 3),\n'
                '        "TPSA": round(Descriptors.TPSA(mol), 2),\n'
                '    }\n'
                '\n'
                'with st.sidebar:\n'
                '    st.markdown("### 🔬 Input")\n'
                '    smiles = st.text_input("SMILES", value="CCOc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCC")\n'
                '    target = st.selectbox("Target", ["EGFR", "HIV Protease", "HIV Integrase", "BACE1", "COVID Mpro"])\n'
                '    analyze_btn = st.button("⚡ Analyze", use_container_width=True)\n'
                '\n'
                'col1, col2 = st.columns([1, 1])\n'
                'with col1:\n'
                '    st.markdown("### Structure")\n'
                '    if smiles:\n'
                '        img = mol_to_image(smiles)\n'
                '        if img: st.image(img, use_container_width=True)\n'
                '        else: st.error("Invalid SMILES")\n'
                'with col2:\n'
                '    st.markdown("### Properties")\n'
                '    if smiles:\n'
                '        for k, v in get_properties(smiles).items():\n'
                '            st.metric(k, v)\n'
                '\n'
                'if analyze_btn and smiles:\n'
                '    props = get_properties(smiles)\n'
                '    ro5 = props.get("MW",999)<=500 and props.get("LogP",999)<=5\n'
                '    st.success(f"Lipinski Ro5: {\'PASS\' if ro5 else \'FAIL\'}")\n'
                '    st.info(f"QED: {props.get(\'QED\',\'N/A\')} ({\'Drug-like\' if props.get(\'QED\',0)>0.5 else \'Needs work\'})")\n'
            ),
            "requirements.txt": "streamlit\npandas\nplotly\nrdkit\n",
            "README.md": "# APP_NAME\n\nDrug discovery dashboard built with MutantAI.\n\n## Run\n```bash\nstreamlit run app.py\n```\n",
        },
        "run_cmd": "streamlit run app.py",
    },

    "fastapi": {
        "description": "FastAPI REST API with health check and CORS",
        "files": {
            "main.py": (
                'from fastapi import FastAPI\n'
                'from fastapi.middleware.cors import CORSMiddleware\n'
                'import uvicorn\n\n'
                'app = FastAPI(title="APP_NAME", version="1.0.0")\n'
                'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\n\n'
                '@app.get("/")\n'
                'async def root():\n'
                '    return {"message": "APP_NAME API", "status": "running"}\n\n'
                '@app.get("/health")\n'
                'async def health():\n'
                '    return {"status": "ok"}\n\n'
                'if __name__ == "__main__":\n'
                '    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)\n'
            ),
            "requirements.txt": "fastapi\nuvicorn[standard]\npydantic\npython-dotenv\n",
            "README.md": "# APP_NAME\n\nFastAPI app built with MutantAI.\n\n## Run\n```bash\nuvicorn main:app --reload\n```\n",
            ".env": "APP_NAME=APP_NAME\nDEBUG=true\n",
        },
        "run_cmd": "uvicorn main:app --reload",
    },

    "fastapi-agent": {
        "description": "FastAPI + Ollama AI agent endpoint",
        "files": {
            "main.py": (
                'from fastapi import FastAPI, HTTPException\n'
                'from fastapi.middleware.cors import CORSMiddleware\n'
                'from pydantic import BaseModel\n'
                'import httpx, uvicorn\n\n'
                'app = FastAPI(title="APP_NAME Agent API")\n'
                'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])\n\n'
                'class ChatRequest(BaseModel):\n'
                '    message: str\n'
                '    model: str = "mutant-coder"\n\n'
                '@app.get("/")\n'
                'async def root():\n'
                '    return {"message": "APP_NAME Agent API"}\n\n'
                '@app.post("/chat")\n'
                'async def chat(req: ChatRequest):\n'
                '    try:\n'
                '        async with httpx.AsyncClient(timeout=60) as c:\n'
                '            r = await c.post("http://localhost:11434/api/chat", json={\n'
                '                "model": req.model,\n'
                '                "messages": [{"role": "user", "content": req.message}],\n'
                '                "stream": False,\n'
                '            })\n'
                '            return {"response": r.json()["message"]["content"]}\n'
                '    except Exception as e:\n'
                '        raise HTTPException(status_code=500, detail=str(e))\n\n'
                'if __name__ == "__main__":\n'
                '    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)\n'
            ),
            "requirements.txt": "fastapi\nuvicorn[standard]\nhttpx\npydantic\npython-dotenv\n",
            "README.md": "# APP_NAME\n\nFastAPI + MutantAI agent.\n\n## Run\n```bash\nuvicorn main:app --reload\n```\n",
        },
        "run_cmd": "uvicorn main:app --reload",
    },

    "react": {
        "description": "React + Vite + Tailwind frontend",
        "files": {
            "index.html": '<!DOCTYPE html>\n<html lang="en">\n  <head><meta charset="UTF-8" /><title>APP_NAME</title></head>\n  <body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.jsx"></script>\n  </body>\n</html>\n',
            "src/main.jsx": "import React from 'react'\nimport ReactDOM from 'react-dom/client'\nimport App from './App'\nimport './index.css'\nReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)\n",
            "src/App.jsx": "export default function App() {\n  return (\n    <div className=\"min-h-screen bg-gray-950 text-white flex flex-col items-center justify-center\">\n      <h1 className=\"text-4xl font-bold text-cyan-400 mb-4\">🧬 APP_NAME</h1>\n      <p className=\"text-gray-400\">Built with MutantAI</p>\n    </div>\n  )\n}\n",
            "src/index.css": "@tailwind base;\n@tailwind components;\n@tailwind utilities;\n",
            "package.json": '{\n  "name": "APP_NAME_LOWER",\n  "version": "0.1.0",\n  "scripts": {"dev": "vite", "build": "vite build"},\n  "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0"},\n  "devDependencies": {"@vitejs/plugin-react": "^4.0.0", "vite": "^4.4.0", "tailwindcss": "^3.3.0"}\n}\n',
            "README.md": "# APP_NAME\n\nReact app built with MutantAI.\n\n## Run\n```bash\nnpm install && npm run dev\n```\n",
        },
        "run_cmd": "npm install && npm run dev",
    },

    "nanodock-agent": {
        "description": "NanoDock-style agent with Arc USDC payments",
        "files": {
            "requirements.txt": "fastapi\nuvicorn\nhttpx\npydantic\nweb3\npython-dotenv\n",
            ".env": "AGENT_WALLET_ADDRESS=\nARC_RPC_URL=\nUSDA_CONTRACT=\n",
            "README.md": "# APP_NAME\n\nNanoDock-style agent. Charges 0.001 USDC per query via Arc.\n",
        },
        "run_cmd": "uvicorn main:app --reload",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_registry() -> dict:
    registry_path = Path(__file__).parent / "learned_templates.json"
    if registry_path.exists():
        try:
            return json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _apply_name(content: str, name: str, name_lower: str) -> str:
    """Safe name substitution — no .format() to avoid brace conflicts."""
    return content.replace("APP_NAME_LOWER", name_lower).replace("APP_NAME", name)


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def scaffold_project(spec: str) -> str:
    """
    Scaffold a complete app project. Use when asked to scaffold, create a project, or build an app.

    Input formats:
    - "name=MyApp template=streamlit-drug"
    - "name=MyAPI template=fastapi path=./projects/myapi"
    - natural: "drug discovery dashboard called DrugDash"

    Built-in: streamlit, streamlit-drug, fastapi, fastapi-agent, react, nanodock-agent
    Plus any learned templates from learn_from_app.
    """
    import re

    name = "MutantApp"
    template_key = None
    output_path = None

    name_match = re.search(r'name=([^\s]+)', spec)
    template_match = re.search(r'template=([^\s]+)', spec)
    path_match = re.search(r'path=([^\s]+)', spec)

    if name_match:
        name = name_match.group(1)
    if template_match:
        template_key = template_match.group(1)
    if path_match:
        output_path = path_match.group(1)

    if not template_key:
        s = spec.lower()
        if any(x in s for x in ["drug", "smiles", "rdkit", "docking", "molecule", "chemistry"]):
            template_key = "streamlit-drug"
        elif any(x in s for x in ["react", "frontend", "vite"]):
            template_key = "react"
        elif any(x in s for x in ["agent endpoint", "ai api", "ollama api"]):
            template_key = "fastapi-agent"
        elif any(x in s for x in ["fastapi", "rest api", "api endpoint"]):
            template_key = "fastapi"
        elif any(x in s for x in ["nanodock", "usdc", "payment", "arc"]):
            template_key = "nanodock-agent"
        else:
            template_key = "streamlit"

    template = TEMPLATES.get(template_key) or _load_registry().get(template_key)

    if not template:
        available = ", ".join(TEMPLATES.keys())
        learned = ", ".join(_load_registry().keys()) or "none yet"
        return f"Unknown template '{template_key}'.\nBuilt-in: {available}\nLearned: {learned}"

    if not output_path:
        output_path = f"./{name.lower().replace(' ', '_')}"

    project_dir = Path(output_path)
    project_dir.mkdir(parents=True, exist_ok=True)

    files_created = []
    name_lower = name.lower().replace(" ", "-")

    for filename, content in template["files"].items():
        filepath = project_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        formatted = _apply_name(content, name, name_lower)
        filepath.write_text(formatted, encoding="utf-8")
        files_created.append(filename)

    run_cmd = template.get("run_cmd", "streamlit run app.py")
    return f"""✅ Project '{name}' scaffolded!

📁 Location: {project_dir.resolve()}
📋 Template: {template_key} — {template.get('description', '')}
📄 Files ({len(files_created)}): {', '.join(files_created)}

🚀 To run:
   cd {output_path}
   {run_cmd}

Next: ask MutantAI to add features!"""


@tool
def list_templates(query: str = "") -> str:
    """List all available app scaffolding templates including learned ones."""
    lines = ["🧬 MutantAI Built-in Templates:\n"]
    for key, t in TEMPLATES.items():
        lines.append(f"  {key:<22} — {t['description']}")
    registry = _load_registry()
    if registry:
        lines.append("\n🧠 Learned Templates:\n")
        for key, t in registry.items():
            lines.append(f"  {key:<22} — {t.get('description', 'custom')}")
    lines.append("\nUsage: scaffold_project name=MyApp template=streamlit-drug")
    return "\n".join(lines)


@tool
def learn_from_app(spec: str) -> str:
    """
    Learn from a working app folder and save as reusable template.
    Input: "path=./physicschemv2 name=drug-dashboard-v2"
    """
    import re

    path_match = re.search(r'path=([^\s]+)', spec)
    name_match = re.search(r'name=([^\s]+)', spec)

    if path_match:
        folder = path_match.group(1)
        name = name_match.group(1) if name_match else Path(folder).name
    else:
        parts = spec.strip().split()
        folder = parts[0] if parts else None
        name = parts[1] if len(parts) > 1 else (folder or "learned-app")

    if not folder:
        return "Usage: learn_from_app path=./physicschemv2 name=drug-dashboard-v2"

    folder_path = Path(folder).resolve()
    if not folder_path.exists():
        return f"Folder not found: {folder_path}"

    CODE_EXT = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
                ".json", ".yaml", ".yml", ".md", ".txt", ".sh", ".toml", ".env"}
    IGNORE = {".venv", "venv", "node_modules", "__pycache__", ".git", "dist", "build"}

    files = {}
    for fp in sorted(folder_path.rglob("*")):
        if any(p in IGNORE for p in fp.parts):
            continue
        if not fp.is_file() or fp.suffix not in CODE_EXT:
            continue
        rel = str(fp.relative_to(folder_path)).replace("\\", "/")
        try:
            files[rel] = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

    if not files:
        return f"No code files found in {folder_path}"

    registry_path = Path(__file__).parent / "learned_templates.json"
    registry = _load_registry()
    registry[name] = {
        "description": f"Learned from {folder} — {len(files)} files",
        "files": files,
        "run_cmd": "streamlit run app.py" if "app.py" in files else "python main.py",
    }
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    return f"""✅ Template '{name}' learned!
📄 Files captured ({len(files)}): {list(files.keys())}
💾 Saved to learned_templates.json
Usage: scaffold_project name=MyNewApp template={name}"""


@tool
def list_learned_templates(query: str = "") -> str:
    """List all templates learned from real working apps."""
    registry = _load_registry()
    if not registry:
        return "No learned templates yet. Use learn_from_app to capture a working app."
    lines = ["🧠 Learned Templates:\n"]
    for name, info in registry.items():
        lines.append(f"  {name:<25} — {info.get('description', 'custom')}")
    lines.append("\nUsage: scaffold_project name=MyApp template=<name>")
    return "\n".join(lines)


@tool
def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Get the current date and time."""
    from datetime import datetime
    try:
        return datetime.now().strftime(format)
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


CUSTOM_TOOLS = [
    scaffold_project,
    list_templates,
    learn_from_app,
    list_learned_templates,
    get_current_time,
]