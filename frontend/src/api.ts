import type { InstructorBrief, ScriptProject } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function createProject(brief: InstructorBrief) {
  return request<ScriptProject>('/projects', {
    method: 'POST',
    body: JSON.stringify(brief),
  })
}

export function listProjects() {
  return request<ScriptProject[]>('/projects')
}

export function getProject(projectId: string) {
  return request<ScriptProject>(`/projects/${projectId}`)
}

export function editSegment(
  projectId: string,
  segmentId: string,
  instructor_narration: string,
  instructor_feedback: string,
) {
  return request<ScriptProject>(`/projects/${projectId}/segments/${segmentId}/edit`, {
    method: 'POST',
    body: JSON.stringify({ instructor_narration, instructor_feedback }),
  })
}

export function regenerateSegment(projectId: string, segmentId: string, instruction: string, reason: string) {
  return request<ScriptProject>(`/projects/${projectId}/segments/${segmentId}/regenerate`, {
    method: 'POST',
    body: JSON.stringify({ instruction, reason }),
  })
}

export function signOffProject(projectId: string, instructor_name: string, final_notes: string) {
  return request<ScriptProject>(`/projects/${projectId}/sign-off`, {
    method: 'POST',
    body: JSON.stringify({ instructor_name, final_notes, approved: true }),
  })
}

export function markdownExportUrl(projectId: string) {
  return `${API_BASE}/projects/${projectId}/export/markdown`
}
