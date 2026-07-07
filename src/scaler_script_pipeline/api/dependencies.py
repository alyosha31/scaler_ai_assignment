from functools import lru_cache

from scaler_script_pipeline.core.config import get_settings
from scaler_script_pipeline.services.claude import ClaudeClient
from scaler_script_pipeline.services.evaluator import EvaluationRunner
from scaler_script_pipeline.services.pipeline import ScriptPipeline
from scaler_script_pipeline.services.tracing import TraceStore
from scaler_script_pipeline.services.validator import BriefValidator
from scaler_script_pipeline.storage.repository import ProjectRepository


@lru_cache
def get_repository() -> ProjectRepository:
    settings = get_settings()
    repository = ProjectRepository(settings.database_url)
    repository.init_db()
    return repository


@lru_cache
def get_trace_store() -> TraceStore:
    settings = get_settings()
    return TraceStore(settings.trace_dir, enabled=settings.trace_enabled)


@lru_cache
def get_pipeline() -> ScriptPipeline:
    settings = get_settings()
    trace_store = get_trace_store()
    claude = ClaudeClient(settings, trace_store=trace_store)
    return ScriptPipeline(
        repository=get_repository(),
        validator=BriefValidator(),
        claude=claude,
        evaluator=EvaluationRunner(claude, settings),
    )
