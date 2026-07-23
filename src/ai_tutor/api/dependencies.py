from functools import lru_cache

from ai_tutor.core.config import get_settings
from ai_tutor.services.claude import ClaudeClient
from ai_tutor.services.evaluator import EvaluationRunner
from ai_tutor.services.pipeline import ScriptPipeline
from ai_tutor.services.tracing import TraceStore
from ai_tutor.services.validator import BriefValidator
from ai_tutor.storage.repository import ProjectRepository


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
