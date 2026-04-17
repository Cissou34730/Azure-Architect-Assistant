import { useEffect, useState } from "react";
import {
  projectNotesApi,
  type ProjectNote,
  type ProjectNoteCategory,
} from "../../api/projectNotesService";

const PROJECT_NOTES_UPDATED_EVENT = "project-notes-updated";

const DEFAULT_CATEGORY: ProjectNoteCategory = "context";

export function ProjectNotesPanel({
  projectId,
}: {
  readonly projectId: string;
}) {
  const [notes, setNotes] = useState<readonly ProjectNote[]>([]);
  const [category, setCategory] = useState<ProjectNoteCategory>(DEFAULT_CATEGORY);
  const [content, setContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadNotes = async () => {
      setLoading(true);
      try {
        const response = await projectNotesApi.list(projectId);
        if (active) {
          setNotes(response.notes);
          setError(null);
        }
      } catch (loadError) {
        if (active) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load project notes.");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    const handleRefresh = (event: Event) => {
      const detail = (event as CustomEvent<{ projectId?: string }>).detail;
      if (detail?.projectId === projectId) {
        void loadNotes();
      }
    };

    void loadNotes();
    window.addEventListener(PROJECT_NOTES_UPDATED_EVENT, handleRefresh);
    return () => {
      active = false;
      window.removeEventListener(PROJECT_NOTES_UPDATED_EVENT, handleRefresh);
    };
  }, [projectId]);

  const resetForm = () => {
    setCategory(DEFAULT_CATEGORY);
    setContent("");
    setEditingNoteId(null);
  };

  const publishUpdatedEvent = () => {
    window.dispatchEvent(
      new CustomEvent(PROJECT_NOTES_UPDATED_EVENT, {
        detail: { projectId },
      }),
    );
  };

  const handleSubmit = async () => {
    const trimmedContent = content.trim();
    if (trimmedContent.length === 0) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (editingNoteId === null) {
        const response = await projectNotesApi.create(projectId, {
          category,
          content: trimmedContent,
          sourceMessageId: null,
        });
        setNotes((current) => [response.note, ...current]);
      } else {
        const response = await projectNotesApi.update(projectId, editingNoteId, {
          category,
          content: trimmedContent,
          sourceMessageId: null,
        });
        setNotes((current) =>
          current.map((note) => (note.id === editingNoteId ? response.note : note)),
        );
      }
      publishUpdatedEvent();
      resetForm();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Failed to save project note.");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (note: ProjectNote) => {
    setEditingNoteId(note.id);
    setCategory(note.category);
    setContent(note.content);
  };

  const handleDelete = async (noteId: string) => {
    setSaving(true);
    setError(null);
    try {
      await projectNotesApi.remove(projectId, noteId);
      setNotes((current) => current.filter((note) => note.id !== noteId));
      publishUpdatedEvent();
      if (editingNoteId === noteId) {
        resetForm();
      }
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Failed to delete project note.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <div className="rounded-xl border border-border bg-card p-4">
        <div className="mb-3">
          <h2 className="text-base font-semibold text-foreground">Project notes</h2>
          <p className="text-sm text-secondary">
            Pin decisions, context, risks, and unresolved questions that should survive chat turns.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-[180px_1fr]">
          <label className="flex flex-col gap-1.5 text-sm text-secondary">
            <span className="font-medium text-foreground">Category</span>
            <select
              value={category}
              onChange={(event) => {
                setCategory(event.target.value as ProjectNoteCategory);
              }}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-foreground"
              disabled={saving}
              aria-label="Category"
            >
              <option value="context">Context</option>
              <option value="decision">Decision</option>
              <option value="question">Question</option>
              <option value="risk">Risk</option>
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-sm text-secondary">
            <span className="font-medium text-foreground">Note content</span>
            <textarea
              value={content}
              onChange={(event) => {
                setContent(event.target.value);
              }}
              rows={4}
              className="rounded-lg border border-border bg-surface px-3 py-2 text-foreground"
              disabled={saving}
              aria-label="Note content"
            />
          </label>
        </div>

        <div className="mt-3 flex items-center justify-between">
          <div className="min-h-5 text-sm text-danger">{error}</div>
          <div className="flex gap-2">
            {editingNoteId !== null && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-md border border-border px-3 py-2 text-sm text-secondary hover:bg-surface"
              >
                Cancel
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                void handleSubmit();
              }}
              disabled={saving || content.trim().length === 0}
              className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-inverse hover:bg-brand-strong disabled:cursor-not-allowed disabled:opacity-50"
            >
              {editingNoteId === null ? "Add note" : "Save note"}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto rounded-xl border border-border bg-card p-4">
        {loading ? (
          <p className="text-sm text-secondary">Loading notes…</p>
        ) : notes.length === 0 ? (
          <p className="text-sm text-secondary">No project notes yet.</p>
        ) : (
          <ul className="space-y-3">
            {notes.map((note) => (
              <li key={note.id} className="rounded-lg border border-border bg-surface p-3">
                <div className="mb-2 flex items-center justify-between gap-3">
                  <div>
                    <span className="rounded-full bg-brand-soft px-2 py-1 text-xs font-semibold uppercase tracking-wide text-brand-strong">
                      {note.category}
                    </span>
                    <p className="mt-2 text-sm text-foreground">{note.content}</p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        handleEdit(note);
                      }}
                      className="rounded-md border border-border px-2 py-1 text-xs text-secondary hover:bg-card"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        void handleDelete(note.id);
                      }}
                      className="rounded-md border border-danger-line px-2 py-1 text-xs text-danger hover:bg-danger-soft"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <p className="text-xs text-dim">Updated {new Date(note.updatedAt).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
