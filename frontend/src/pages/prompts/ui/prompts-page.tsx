import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchPrompts, updatePrompts } from "shared/api/prompts";

export function PromptsPage() {
  const promptsQuery = useQuery({
    queryKey: ["prompts"],
    queryFn: fetchPrompts,
  });

  const updateMutation = useMutation({
    mutationFn: updatePrompts,
    onSuccess: () => {
      promptsQuery.refetch();
    },
  });

  const handleSave = (role: string, value: string) => {
    updateMutation.mutate({ [role]: value });
  };

  if (promptsQuery.isLoading) {
    return <div className="app-shell">Loading prompts...</div>;
  }

  if (promptsQuery.isError) {
    return (
      <div className="app-shell">
        <div className="app-frame">
          <section className="panel">
            <div className="panel__header">
              <h2>Error</h2>
            </div>
            <div className="panel__body">
              <div className="empty-state">
                <strong>Failed to load prompts</strong>
                <p>Check that the backend is running.</p>
              </div>
            </div>
          </section>
        </div>
      </div>
    );
  }

  const prompts = promptsQuery.data || { main: "", orchestrator: "", leaf: "" };

  return (
    <div className="app-shell">
      <div className="app-frame">
        <header className="topbar">
          <div className="topbar__title">
            <span className="eyebrow">NightOwl</span>
            <h1>Agent Prompts</h1>
            <p>Customize the system prompts for different agent roles.</p>
          </div>
        </header>

        <div className="settings-layout">
          <aside className="settings-sidebar">
            <div className="settings-sidebar__body">
              <button
                className="settings-nav-item settings-nav-item--active"
                type="button"
              >
                <strong>Prompt Configuration</strong>
                <span>Main, Orchestrator, Leaf roles</span>
              </button>
            </div>
          </aside>

          <div className="settings-content">
            <PromptEditor
              title="Main Agent"
              description="The primary agent that handles user requests and spawns children."
              value={prompts.main}
              onSave={(value) => handleSave("main", value)}
              saving={updateMutation.isPending}
            />

            <PromptEditor
              title="Orchestrator Agent"
              description="Child agents that coordinate sub-tasks and can spawn further children."
              value={prompts.orchestrator}
              onSave={(value) => handleSave("orchestrator", value)}
              saving={updateMutation.isPending}
            />

            <PromptEditor
              title="Leaf Agent"
              description="Task-specific agents that cannot spawn children."
              value={prompts.leaf}
              onSave={(value) => handleSave("leaf", value)}
              saving={updateMutation.isPending}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function PromptEditor({
  title,
  description,
  value,
  onSave,
  saving,
}: {
  title: string;
  description: string;
  value: string;
  onSave: (value: string) => void;
  saving: boolean;
}) {
  const [edited, setEdited] = useState(value);
  const hasChanges = edited !== value;

  useEffect(() => {
    setEdited(value);
  }, [value]);

  return (
    <div className="settings-detail-card">
      <div className="settings-detail-card__header">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <div className="settings-skill-editor">
        <textarea
          className="prompt-textarea"
          value={edited}
          onChange={(e) => setEdited(e.target.value)}
          rows={6}
          placeholder={`Enter ${title.toLowerCase()} prompt...`}
        />
      </div>
      <div className="settings-import-actions">
        <button
          className="button button--primary"
          disabled={!hasChanges || saving}
          onClick={() => onSave(edited)}
          type="button"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
        {hasChanges && (
          <button
            className="button button--ghost"
            onClick={() => setEdited(value)}
            type="button"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
