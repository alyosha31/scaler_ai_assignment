import json
import queue

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from ai_tutor.api.dependencies import get_pipeline, get_trace_store
from ai_tutor.core.models import (
    ClaudeError,
    InstructorBrief,
    ScriptProject,
    SegmentEditRequest,
    SegmentRegenerateRequest,
    SignOffRequest,
)
from ai_tutor.services.pipeline import ScriptPipeline
from ai_tutor.services.tracing import TraceStore

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/projects", response_model=ScriptProject)
def create_project(
    brief: InstructorBrief,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    try:
        return pipeline.generate_project(brief)
    except ClaudeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/projects", response_model=list[ScriptProject])
def list_projects(pipeline: ScriptPipeline = Depends(get_pipeline)) -> list[ScriptProject]:
    return pipeline.list_projects()


@router.get("/projects/{project_id}", response_model=ScriptProject)
def get_project(
    project_id: str,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    return pipeline.get_project(project_id)


@router.post("/projects/{project_id}/segments/{segment_id}/edit", response_model=ScriptProject)
def edit_segment(
    project_id: str,
    segment_id: str,
    request: SegmentEditRequest,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    return pipeline.edit_segment(project_id, segment_id, request)


@router.post("/projects/{project_id}/segments/{segment_id}/regenerate", response_model=ScriptProject)
def regenerate_segment(
    project_id: str,
    segment_id: str,
    request: SegmentRegenerateRequest,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    try:
        return pipeline.regenerate_segment(project_id, segment_id, request)
    except ClaudeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/projects/{project_id}/evaluate", response_model=ScriptProject)
def evaluate_project(
    project_id: str,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    try:
        return pipeline.evaluate_project(project_id)
    except ClaudeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/projects/{project_id}/sign-off", response_model=ScriptProject)
def sign_off(
    project_id: str,
    request: SignOffRequest,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> ScriptProject:
    return pipeline.sign_off(project_id, request)


@router.get("/projects/{project_id}/export/markdown")
def export_markdown(
    project_id: str,
    pipeline: ScriptPipeline = Depends(get_pipeline),
) -> Response:
    markdown = pipeline.export_markdown(project_id)
    return Response(
        content=markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{project_id}.md"'},
    )


@router.get("/traces")
def list_traces(
    limit: int = 50,
    project_id: str | None = None,
    trace_store: TraceStore = Depends(get_trace_store),
) -> list[dict]:
    return trace_store.list_traces(limit=limit, project_id=project_id)


@router.get("/traces/stream")
def stream_traces(
    project_id: str | None = None,
    trace_store: TraceStore = Depends(get_trace_store),
) -> StreamingResponse:
    subscriber = trace_store.subscribe()

    def events():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    summary = subscriber.get(timeout=15)
                except queue.Empty:
                    yield ": heartbeat\n\n"
                    continue
                if project_id and summary.get("project_id") != project_id:
                    continue
                yield f"event: trace\ndata: {json.dumps(summary)}\n\n"
        finally:
            trace_store.unsubscribe(subscriber)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/traces/{trace_id}")
def get_trace(
    trace_id: str,
    trace_store: TraceStore = Depends(get_trace_store),
) -> dict:
    trace = trace_store.get_trace(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
