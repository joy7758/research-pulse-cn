import type { WorkspaceCreateInput, WorkspaceListItemViewModel } from "../lib/types";

type WorkspaceListPanelProps = {
  items: WorkspaceListItemViewModel[];
  selectedWorkspaceId: string | null;
  createInput: WorkspaceCreateInput;
  loading: boolean;
  onSelect: (workspaceId: string) => void;
  onCreateInputChange: (patch: Partial<WorkspaceCreateInput>) => void;
  onCreate: () => void;
};

export function WorkspaceListPanel({
  items,
  selectedWorkspaceId,
  createInput,
  loading,
  onSelect,
  onCreateInputChange,
  onCreate,
}: WorkspaceListPanelProps) {
  return (
    <aside className="workspace-list-panel">
      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Workspace list</p>
            <h2>Group workspaces</h2>
          </div>
        </div>
        {items.length === 0 ? (
          <div className="empty-state">No workspaces yet. Create one to start the board flow.</div>
        ) : (
          <ul className="workspace-list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={item.id === selectedWorkspaceId ? "workspace-item active" : "workspace-item"}
                  onClick={() => onSelect(item.id)}
                >
                  <div className="workspace-item-header">
                    <strong>{item.name}</strong>
                    <span className={`status-pill ${item.status}`}>{item.status}</span>
                  </div>
                  <div className="workspace-item-meta">
                    <span>{item.slug}</span>
                    <span>
                      {item.memberCount ?? "—"} members / {item.paperCount ?? "—"} papers
                    </span>
                  </div>
                  {item.description ? <p>{item.description}</p> : null}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel-card">
        <div className="panel-card-header">
          <div>
            <p className="eyebrow">Create workspace</p>
            <h2>New group workspace</h2>
          </div>
        </div>
        <div className="field-grid">
          <label className="field-stack">
            <span>Slug</span>
            <input
              type="text"
              value={createInput.slug}
              onChange={(event) => onCreateInputChange({ slug: event.target.value })}
              placeholder="materials-group"
            />
          </label>
          <label className="field-stack">
            <span>Name</span>
            <input
              type="text"
              value={createInput.name}
              onChange={(event) => onCreateInputChange({ name: event.target.value })}
              placeholder="Materials Group"
            />
          </label>
        </div>
        <label className="field-stack">
          <span>Description</span>
          <textarea
            value={createInput.description}
            onChange={(event) => onCreateInputChange({ description: event.target.value })}
            rows={3}
            placeholder="Short internal summary for the shared workspace"
          />
        </label>
        <div className="button-row">
          <button type="button" className="button-primary" onClick={onCreate} disabled={loading}>
            {loading ? "Creating..." : "Create workspace"}
          </button>
        </div>
      </section>
    </aside>
  );
}
