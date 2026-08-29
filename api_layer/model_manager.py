"""
api_layer/model_manager.py
============================
Dynamic Transformer Model Manager for CyberRiskIQ.

Provides autonomous hot-swapping between HuggingFace transformer models
with graceful fallback to deterministic template synthesis when local
inference fails.

Model Tiers:
  - Tier 1 (Semantic Embeddings): sentence-transformers/all-MiniLM-L6-v2
                                   → BAAI/bge-small-en-v1.5
  - Tier 2 (Local Generation):    microsoft/Phi-3-mini-4k-instruct
                                   → Qwen/Qwen2.5-Coder-3B-Instruct
  - Tier 3 (Fallback):            Deterministic f-string templates (zero-math)
"""
import gc
import logging
from typing import Optional, Callable

logger = logging.getLogger("model_manager")

# ── Embedding Model Candidates ──────────────────────────────────────────────
EMBEDDING_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en-v1.5",
]

# ── Generation Model Candidates ─────────────────────────────────────────────
GENERATION_MODELS = [
    "microsoft/Phi-3-mini-4k-instruct",
    "Qwen/Qwen2.5-Coder-3B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct",
]


def _purge_gpu_cache() -> None:
    """Purge GPU memory and run garbage collection."""
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except ImportError:
        pass
    gc.collect()


class ModelManager:
    """Manages lifecycle of local transformer models with hot-swap fallback."""

    def __init__(self) -> None:
        self._active_embedding_model: Optional[str] = None
        self._active_generation_model: Optional[str] = None
        self._embedding_pipeline: Optional[object] = None
        self._generation_pipeline: Optional[object] = None
        self._embedding_idx: int = 0
        self._generation_idx: int = 0
        self._fallback_active: bool = False

    @property
    def active_embedding(self) -> Optional[str]:
        return self._active_embedding_model

    @property
    def active_generation(self) -> Optional[str]:
        return self._active_generation_model

    @property
    def is_fallback(self) -> bool:
        return self._fallback_active

    def status(self) -> dict:
        """Return current model status."""
        return {
            "embedding_model": self._active_embedding_model or "none",
            "generation_model": self._active_generation_model or "none",
            "fallback_active": self._fallback_active,
            "embedding_candidates": EMBEDDING_MODELS,
            "generation_candidates": GENERATION_MODELS,
        }

    # ── Embedding Model Management ──────────────────────────────────────────
    def load_embedding_model(self, model_name: Optional[str] = None) -> bool:
        """Load an embedding model. Returns True on success."""
        candidates = [model_name] if model_name else EMBEDDING_MODELS
        for name in candidates:
            try:
                _purge_gpu_cache()
                logger.info(f"Loading embedding model: {name}")
                from sentence_transformers import SentenceTransformer
                self._embedding_pipeline = SentenceTransformer(name)
                self._active_embedding_model = name
                logger.info(f"Successfully loaded embedding model: {name}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load embedding model {name}: {e}")
                continue
        logger.error("All embedding model candidates failed.")
        return False

    def swap_embedding_model(self) -> bool:
        """Hot-swap to next embedding model candidate."""
        _purge_gpu_cache()
        self._embedding_pipeline = None
        self._embedding_idx = (self._embedding_idx + 1) % len(EMBEDDING_MODELS)
        candidate = EMBEDDING_MODELS[self._embedding_idx]
        logger.info(f"Hot-swapping embedding model to: {candidate}")
        return self.load_embedding_model(candidate)

    # ── Generation Model Management ─────────────────────────────────────────
    def load_generation_model(self, model_name: Optional[str] = None) -> bool:
        """Load a local generation model. Returns True on success."""
        candidates = [model_name] if model_name else GENERATION_MODELS
        for name in candidates:
            try:
                _purge_gpu_cache()
                logger.info(f"Loading generation model: {name}")
                from transformers import pipeline as hf_pipeline
                self._generation_pipeline = hf_pipeline(
                    "text-generation",
                    model=name,
                    max_new_tokens=512,
                    do_sample=True,
                    temperature=0.7,
                )
                self._active_generation_model = name
                logger.info(f"Successfully loaded generation model: {name}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load generation model {name}: {e}")
                continue

        logger.error("All generation model candidates failed — activating template fallback.")
        self._fallback_active = True
        return False

    def swap_generation_model(self) -> bool:
        """Hot-swap to next generation model candidate."""
        _purge_gpu_cache()
        self._generation_pipeline = None
        self._generation_idx = (self._generation_idx + 1) % len(GENERATION_MODELS)
        candidate = GENERATION_MODELS[self._generation_idx]
        logger.info(f"Hot-swapping generation model to: {candidate}")
        return self.load_generation_model(candidate)

    def activate_template_fallback(self) -> None:
        """Activate deterministic template synthesis fallback."""
        _purge_gpu_cache()
        self._generation_pipeline = None
        self._embedding_pipeline = None
        self._active_generation_model = None
        self._active_embedding_model = None
        self._fallback_active = True
        logger.info("Template fallback activated — zero-math deterministic synthesis guaranteed.")

    def generate(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        """Generate text using local model with auto-fallback on failure."""
        if self._fallback_active or not self._generation_pipeline:
            return None  # Caller uses template fallback
        try:
            full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
            result = self._generation_pipeline(full_prompt)
            if result and len(result) > 0:
                return result[0].get("generated_text", "")
        except Exception as e:
            logger.warning(f"Local generation failed: {e}. Attempting model swap.")
            if not self.swap_generation_model():
                self.activate_template_fallback()
        return None

    def embed(self, texts: list) -> Optional[list]:
        """Generate embeddings using local model with auto-fallback."""
        if not self._embedding_pipeline:
            return None
        try:
            return self._embedding_pipeline.encode(texts).tolist()
        except Exception as e:
            logger.warning(f"Embedding failed: {e}. Attempting model swap.")
            if not self.swap_embedding_model():
                logger.error("All embedding models failed.")
            return None


# ── Module-level singleton ──────────────────────────────────────────────────
model_manager = ModelManager()
