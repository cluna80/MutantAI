"""
hackathon_tools.py — MutantAI Hackathon Mode
Analyzes hackathon briefs and creates completion plans.
"""

from langchain_core.tools import tool
from pathlib import Path
import json
from datetime import datetime

HACKATHONS_FILE = Path(__file__).parent / "hackathons.json"

def _load_hackathons() -> dict:
    if HACKATHONS_FILE.exists():
        try:
            return json.loads(HACKATHONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def _save_hackathons(data: dict):
    HACKATHONS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


@tool
def analyze_hackathon(brief: str) -> str:
    """
    Analyze a hackathon brief and create a completion plan.
    Paste the full hackathon description as input.
    MutantAI will identify tracks, requirements, deadlines, and map
    your existing projects to what needs to be built.
    """
    import re

    brief_lower = brief.lower()

    # Extract deadline
    deadline = "Unknown"
    date_patterns = [
        r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}[\s,]+\d{4}',
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[\s.]+\d{1,2}[\s,]+\d{4}',
        r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+\w+\s+\d{1,2}\s+\d{4}',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, brief_lower)
        if match:
            deadline = match.group(0).title()
            break

    # Extract prize pool
    prize = "Unknown"
    prize_match = re.search(r'\$[\d,]+\+?\s*(?:total\s*)?prize', brief_lower)
    if prize_match:
        prize = prize_match.group(0)

    # Identify tracks
    tracks = []
    track_keywords = {
        "AI Agents & Agentic Workflows": ["agent", "agentic", "workflow", "langchain", "crewai", "autogen"],
        "Fine-Tuning on AMD GPUs": ["fine-tun", "finetun", "lora", "qlora", "sft", "domain-specific llm"],
        "Vision & Multimodal AI": ["vision", "multimodal", "image", "video", "audio"],
        "Build in Public": ["build in public", "ship it", "social media", "open-source"],
        "Per-API Monetization": ["api", "monetiz", "per-request", "per-call"],
        "Agent-to-Agent Payment": ["agent-to-agent", "machine-to-machine", "nanopayment", "usdc"],
        "Usage-Based Compute": ["usage-based", "per-query", "per-compute"],
    }
    for track_name, keywords in track_keywords.items():
        if any(kw in brief_lower for kw in keywords):
            tracks.append(track_name)

    # Identify tech stack requirements
    tech_stack = []
    tech_keywords = ["langchain", "crewai", "autogen", "pytorch", "rocm", "hugging face",
                     "qwen", "llama", "mistral", "vllm", "streamlit", "fastapi", "react",
                     "usdc", "arc", "nanopayment", "solidity"]
    for tech in tech_keywords:
        if tech in brief_lower:
            tech_stack.append(tech.title())

    # Map to existing MutantAI projects
    existing_projects = {
        "MutantAI Platform": {
            "covers": ["AI Agents & Agentic Workflows", "Vision & Multimodal AI"],
            "evidence": "Multi-model ReAct agent, 16 tools, LangChain, Qwen models, vision + image gen",
            "github": "https://github.com/cluna80/MutantAI",
        },
        "Fine-tuned Qwen2.5-7B (FBDD)": {
            "covers": ["Fine-Tuning on AMD GPUs"],
            "evidence": "Fine-tuned on AMD MI300X, ROCm, PyTorch, HuggingFace TRL, drug discovery domain",
            "hf": "https://huggingface.co/cluna80/qwen-fbdd-7b-v2-merge",
        },
        "NanoDock": {
            "covers": ["Agent-to-Agent Payment", "Per-API Monetization"],
            "evidence": "Arc USDC nanopayments, ERC-8004 agents, 125+ onchain transactions",
            "github": "https://github.com/cluna80/NanoDock",
        },
        "PhysicsChem Discovery Platform": {
            "covers": ["AI Agents & Agentic Workflows"],
            "evidence": "Autonomous drug discovery agent, Vina docking, ADMET profiling",
        },
    }

    # Save hackathon to registry
    hackathons = _load_hackathons()
    hack_id = f"hack_{len(hackathons) + 1}"
    hackathons[hack_id] = {
        "brief_preview": brief[:300],
        "deadline": deadline,
        "prize": prize,
        "tracks": tracks,
        "tech_stack": tech_stack,
        "saved_at": datetime.now().isoformat(),
        "status": "analyzing",
    }
    _save_hackathons(hackathons)

    # Build completion plan
    output = f"""
🏆 HACKATHON ANALYSIS COMPLETE
================================

📅 Deadline: {deadline}
💰 Prize Pool: {prize}
🆔 Saved as: {hack_id}

🎯 TRACKS DETECTED ({len(tracks)}):
{chr(10).join(f'  ✅ {t}' for t in tracks) if tracks else '  ⚠️ No specific tracks detected'}

🛠️ TECH STACK REQUIRED:
{chr(10).join(f'  • {t}' for t in tech_stack) if tech_stack else '  • Not specified'}

📦 YOUR EXISTING PROJECTS THAT QUALIFY:
"""
    for proj_name, proj_info in existing_projects.items():
        covered = [t for t in proj_info["covers"] if any(t in track for track in tracks)]
        if covered or not tracks:
            output += f"\n  🧬 {proj_name}"
            output += f"\n     Covers: {', '.join(proj_info['covers'])}"
            output += f"\n     Evidence: {proj_info['evidence']}"
            if "github" in proj_info:
                output += f"\n     GitHub: {proj_info['github']}"
            if "hf" in proj_info:
                output += f"\n     HuggingFace: {proj_info['hf']}"
            output += "\n"

    output += f"""
📋 ACTION PLAN:
"""
    action_items = []

    if "Fine-Tuning on AMD GPUs" in tracks or "fine-tun" in brief_lower:
        action_items.append("✅ DONE — Fine-tuned Qwen2.5-7B on MI300X with ROCm")
        action_items.append("✅ DONE — Dataset on HuggingFace: cluna80/fbdd-qwen-dataset-v2")

    if "AI Agents" in str(tracks) or "agent" in brief_lower:
        action_items.append("✅ DONE — MutantAI multi-model agent with LangChain + Qwen")
        action_items.append("✅ DONE — 16 tools, memory, scaffold, vision, image gen")

    if "Vision" in str(tracks) or "multimodal" in brief_lower:
        action_items.append("✅ DONE — Vision model (moondream) + FLUX.1 image generation")

    if "hugging face" in brief_lower or "space" in brief_lower:
        action_items.append("✅ DONE — HF Space: https://huggingface.co/spaces/Cluna80/qwen-fbdd-demo")
        action_items.append("⚠️ TODO — Join hackathon HF organization and publish Space there")

    if "build in public" in brief_lower or "social media" in brief_lower:
        action_items.append("⚠️ TODO — Post 2 tweets tagging @AIatAMD and @lablab")
        action_items.append("⚠️ TODO — Write feedback about ROCm/AMD Developer Cloud experience")

    if "open-source" in brief_lower:
        action_items.append("✅ DONE — GitHub: https://github.com/cluna80/MutantAI (public)")

    action_items.append("⚠️ TODO — Submit project on lablab.ai before deadline")
    action_items.append("⚠️ TODO — Write project description highlighting AMD stack usage")

    for item in action_items:
        output += f"  {item}\n"

    output += f"""
💡 SUBMISSION CHECKLIST:
  □ GitHub repo public with README
  □ HuggingFace Space live and working
  □ 2 social media posts with required tags
  □ Feedback about AMD developer experience written
  □ Project submitted on lablab.ai

Ask MutantAI: "create hackathon submission for {hack_id}" to generate the write-up.
Ask MutantAI: "show hackathons" to see all saved hackathons.
"""
    return output


@tool
def show_hackathons(query: str = "") -> str:
    """Show all saved hackathons and their status."""
    hackathons = _load_hackathons()
    if not hackathons:
        return "No hackathons saved yet. Use analyze_hackathon to add one."

    lines = ["🏆 Saved Hackathons:\n"]
    for hack_id, info in hackathons.items():
        lines.append(f"  {hack_id}")
        lines.append(f"    Deadline: {info.get('deadline', 'Unknown')}")
        lines.append(f"    Prize: {info.get('prize', 'Unknown')}")
        lines.append(f"    Tracks: {', '.join(info.get('tracks', []))}")
        lines.append(f"    Status: {info.get('status', 'unknown')}")
        lines.append("")
    return "\n".join(lines)


@tool
def create_hackathon_submission(hack_id: str) -> str:
    """
    Generate a complete hackathon submission write-up for a saved hackathon.
    Input is the hackathon ID (e.g. hack_1).
    """
    hackathons = _load_hackathons()
    if hack_id not in hackathons:
        available = list(hackathons.keys())
        return f"Hackathon {hack_id} not found. Available: {available}"

    info = hackathons[hack_id]
    tracks = info.get("tracks", [])

    submission = f"""# MutantAI — Hackathon Submission

## Project Overview
MutantAI is a multi-model local AI agent platform that combines fine-tuned LLMs,
agentic workflows, vision, and image generation — all running on consumer hardware,
powered by AMD MI300X for training.

## AMD Technology Used
- **AMD Instinct MI300X**: Fine-tuned Qwen2.5-7B on drug discovery data (3,266 examples)
- **ROCm 7.2 + PyTorch 2.5.1**: Training infrastructure
- **AMD Developer Cloud**: 3 MI300X sessions — training, merging, GGUF conversion

## What Was Built

### Track 1: AI Agents & Agentic Workflows
- Multi-model ReAct agent with 5 specialist models
- 16 tools: code execution, web search, scaffolding, vision, image gen
- LangChain tool framework + custom Ollama routing
- Persistent memory across sessions
- Self-learning app builder (learn_from_app → scaffold_project)
- Run-and-fix loop: writes code → tests → auto-fixes up to 3x

### Track 2: Fine-Tuning on AMD GPUs
- Base model: Qwen/Qwen2.5-7B-Instruct
- Dataset: 3,266 chain-of-thought drug discovery instruction pairs
- Training: AMD MI300X, ROCm, HuggingFace TRL SFTTrainer, LoRA r=8
- Result: Loss 3.28 → 0.24, predicts binding affinity in kcal/mol
- Deployed: GGUF Q4_K_M running locally on GTX 1660 Ti via Ollama

### Track 3: Vision & Multimodal AI
- Vision: moondream model analyzes molecular structures, charts, screenshots
- Image generation: FLUX.1-schnell via HuggingFace Inference API
- Multi-modal input: text + image → analysis + generation

## Links
- GitHub: https://github.com/cluna80/MutantAI
- HuggingFace Model: https://huggingface.co/cluna80/qwen-fbdd-7b-v2-merge
- HuggingFace Space: https://huggingface.co/spaces/Cluna80/qwen-fbdd-demo
- Dataset: https://huggingface.co/datasets/cluna80/fbdd-qwen-dataset-v2

## Why This Matters
Traditional drug discovery AI costs $50K+/year in cloud compute.
MutantAI fine-tuned a specialist model on AMD MI300X for ~$5 total,
deployed it locally for free, and wrapped it in a full agentic platform
that builds apps, generates images, and searches the web.

## AMD Feedback
ROCm 7.2 on MI300X was smooth for PyTorch training. SFTTrainer required
minor fixes (group_by_length removal, processing_class instead of tokenizer)
but ran stably. The 192GB VRAM handled Qwen2.5-7B with headroom to spare.
llama.cpp GGUF conversion worked perfectly. Main friction: repo creation
requires manual step on HuggingFace website (API token lacks create_repo rights).
"""

    # Save submission
    output_path = Path(__file__).parent / f"submission_{hack_id}.md"
    output_path.write_text(submission, encoding="utf-8")

    # Update status
    hackathons[hack_id]["status"] = "submission_ready"
    _save_hackathons(hackathons)

    return f"""✅ Submission written to {output_path}

Preview:
{submission[:500]}...

Full submission saved. Edit it to add specific details about this hackathon's requirements.
Submit at lablab.ai with your GitHub and HuggingFace Space links."""


HACKATHON_TOOLS = [analyze_hackathon, show_hackathons, create_hackathon_submission]
