# MutantAI — Hackathon Submission

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
