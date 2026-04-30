"""
model.py — MutantAI Multi-Model Brain v3
Routes to the right specialist based on task context.
Models: mutant-general | mutant-coder | mutant-fbdd | mutant-vision | mutant-trader
"""

from langchain_ollama import OllamaLLM
import threading

# ── Model Registry ────────────────────────────────────────────────────────────
MODELS = {
    "mutant-general": {
        "model": "mutant-general",
        "temperature": 0.7,
        "num_predict": 1024,
        "num_ctx": 4096,
        "description": "General knowledge, questions, conversation",
        "keywords": [
            "who is", "what is", "when did", "where is", "why does",
            "how does", "tell me about", "explain", "what are",
            "president", "capital", "history", "science", "math",
            "who was", "what was", "where was", "how many", "how much",
        ],
    },
    "mutant-coder": {
        "model": "mutant-coder",
        "temperature": 0.1,
        "num_predict": 2048,
        "num_ctx": 8192,
        "description": "Code generation, debugging, architecture",
        "keywords": [
            "write code", "create file", "generate image", "generate an",
            "write a function", "write a class", "write a script",
            "implement this", "build an api", "build a server",
            "debug this", "fix this bug", "refactor", "fastapi", "flask",
            "react component", "javascript", "typescript", "npm install",
            "deploy", "docker", "endpoint that",
        ],
    },
    "mutant-fbdd": {
        "model": "mutant-fbdd",
        "temperature": 0.1,
        "num_predict": 2048,
        "num_ctx": 4096,
        "description": "Drug discovery, SMILES, docking, ADMET",
        "keywords": [
            "smiles", "molecule", "docking", "egfr", "admet",
            "binding affinity", "fragment", "scaffold", "vina", "kcal/mol",
            "pharmacophore", "lipinski", "chembl", "rdkit",
            "protease", "kinase", "inhibitor", "ligand", "receptor",
            "bace", "mpro", "thrombin", "alzheimer",
            "predict affinity", "analyze molecule", "drug-like",
            "logp", "hbd", "hba", "qed", "tpsa", "ro5",
            "covalent", "atp binding", "active site",
            "lead optimization", "bioisostere", "scaffold hop",
            "drug discovery", "medicinal chemistry",
        ],
    },
    "mutant-trader": {
        "model": "mutant-trader",
        "temperature": 0.3,
        "num_predict": 1024,
        "num_ctx": 4096,
        "description": "Sports betting, crypto, DeFi, market analysis",
        "keywords": [
            "bet", "betting", "nfl", "horse racing", "draftkings", "fantasy",
            "crypto", "defi", "odds", "xrpl", "kelly criterion", "spread",
            "parlay", "moneyline", "over under", "bitcoin", "ethereum",
            "bankroll", "expected value", "closing line", "prop bet",
            "sharp money", "public money", "arbitrage",
        ],
    },
}

# Priority when tied — domain specialists beat general
ROUTING_PRIORITY = ["mutant-fbdd", "mutant-trader", "mutant-coder", "mutant-general"]
DEFAULT_MODEL = "mutant-coder"

# Direct bypass keywords — skip agentic loop for these
FBDD_BYPASS_KEYWORDS = [
    "smiles", "egfr", "admet",
    "docking score", "vina score", "kcal/mol",
    "predict affinity", "analyze molecule", "pharmacophore",
    "fragment growing", "lead optimization",
]

TRADER_BYPASS_KEYWORDS = [
    "should i bet", "kelly criterion", "nfl pick",
    "horse race", "draftkings lineup", "crypto signal",
]

# ── Model Cache ───────────────────────────────────────────────────────────────
_llm_cache = {}

class TimeoutError(Exception):
    pass

def run_with_timeout(func, timeout_seconds, *args, **kwargs):
    result = [None]
    error = [None]
    completed = [False]

    def target():
        try:
            result[0] = func(*args, **kwargs)
            completed[0] = True
        except Exception as e:
            error[0] = e
            completed[0] = True

    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)

    if not completed[0]:
        raise TimeoutError(f"Timed out after {timeout_seconds}s")
    if error[0]:
        raise error[0]
    return result[0]

def _get_llm(model_key: str) -> OllamaLLM:
    if model_key in _llm_cache:
        return _llm_cache[model_key]

    config = MODELS.get(model_key, MODELS[DEFAULT_MODEL])
    print(f"[MutantAI] Loading {model_key}...")

    llm = OllamaLLM(
        model=config["model"],
        temperature=config["temperature"],
        num_predict=config["num_predict"],
        num_ctx=config["num_ctx"],
        repeat_penalty=1.1,
        top_k=40,
        top_p=0.9,
        num_thread=8,
        stop=["<|im_end|>", "<|endoftext|>"],
    )

    _llm_cache[model_key] = llm
    print(f"[MutantAI] {model_key} ready")
    return llm

# ── Auto Router ───────────────────────────────────────────────────────────────
def route_to_model(messages: list[dict]) -> str:
    text = " ".join(
        m["content"].lower()
        for m in messages[-3:]
        if m["role"] in ("user", "system")
    )

    scores = {}
    for model_key, config in MODELS.items():
        score = sum(1 for kw in config["keywords"] if kw in text)
        scores[model_key] = score

    max_score = max(scores.values())

    if max_score == 0:
        print(f"[MutantAI] No keywords matched → {DEFAULT_MODEL}")
        return DEFAULT_MODEL

    # Break ties using priority
    tied = [k for k, v in scores.items() if v == max_score]
    best = DEFAULT_MODEL
    for p in ROUTING_PRIORITY:
        if p in tied:
            best = p
            break

    print(f"[MutantAI] → {best} (scores: {scores})")
    return best

def should_bypass_agent(message: str) -> str | None:
    """
    Returns specialist model key if this message should skip the
    agentic tool loop and go directly to a specialist for reasoning.
    """
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in FBDD_BYPASS_KEYWORDS):
        print(f"[MutantAI] FBDD bypass triggered")
        return "mutant-fbdd"

    if any(kw in msg_lower for kw in TRADER_BYPASS_KEYWORDS):
        print(f"[MutantAI] Trader bypass triggered")
        return "mutant-trader"

    return None

# ── Generate ──────────────────────────────────────────────────────────────────
def generate_raw(messages: list[dict], timeout_seconds: int = 45,
                 force_model: str = None) -> str:

    model_key = force_model if force_model else route_to_model(messages)
    llm = _get_llm(model_key)

    prompt_parts = []
    for msg in messages:
        role, content = msg["role"], msg["content"]
        if role == "system":
            prompt_parts.append(f"<|im_start|>system\n{content}<|im_end|>")
        elif role == "user":
            prompt_parts.append(f"<|im_start|>user\n{content}<|im_end|>")
        elif role == "assistant":
            prompt_parts.append(f"<|im_start|>assistant\n{content}<|im_end|>")

    prompt_parts.append("<|im_start|>assistant\n")
    prompt = "\n".join(prompt_parts)

    try:
        response = run_with_timeout(llm.invoke, timeout_seconds, prompt)
        response = response.strip()
        if response.endswith("<|im_end|>"):
            response = response[:-len("<|im_end|>")].strip()
        return response
    except TimeoutError:
        return "Request timed out. Please try again."
    except Exception as e:
        print(f"[MutantAI] {model_key} failed: {e}")
        if model_key != DEFAULT_MODEL:
            print(f"[MutantAI] Falling back to {DEFAULT_MODEL}")
            return generate_raw(messages, timeout_seconds, force_model=DEFAULT_MODEL)
        return f"Error: {e}"

# ── Convenience ───────────────────────────────────────────────────────────────
def generate_with_fbdd(messages, timeout_seconds=45):
    return generate_raw(messages, timeout_seconds, force_model="mutant-fbdd")

def generate_with_trader(messages, timeout_seconds=45):
    return generate_raw(messages, timeout_seconds, force_model="mutant-trader")

def get_active_model(messages):
    return route_to_model(messages)