import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { buildSkillDraftDocument, buildSkillUploadSelection } from "features/skill-import/model/skill-import";
import { useSaveSkillDraft, useUploadSkillSelection } from "features/skill-import/model/use-skill-import";
import { useMemo, useRef, useState, type ChangeEvent } from "react";

type SettingsSectionId = "skills-import" | "models";

type SettingsSection = {
  id: SettingsSectionId;
  label: string;
  eyebrow: string;
  title: string;
  description: string;
  summary: string;
  metrics: Array<{ label: string; value: string }>;
};

type ModelCard = {
  name: string;
  provider: string;
  badge: string;
  summary: string;
  capabilities: string[];
};

type ImportSelection = {
  count: number;
  files: File[];
  label: string;
  names: string[];
  rejectedCount: number;
};

type SkillEditorAction = {
  label: string;
  onClick: (editor: Editor) => void;
  isActive?: (editor: Editor) => boolean;
};

const settingsSections: SettingsSection[] = [
  {
    id: "skills-import",
    label: "Skills import",
    eyebrow: "NightOwl Skills",
    title: "Import skill packages from local files and folders.",
    description:
      "Bring skill packs into the system, validate manifests, and save custom skill drafts into the runtime.",
    summary: "One import surface for markdown files or extracted folders, plus a draft editor that saves into the skills API.",
    metrics: []
  },
  {
    id: "models",
    label: "Models",
    eyebrow: "NightOwl Models",
    title: "Configure providers and model inventory in one grid.",
    description:
      "Define which providers are available, which models are preferred by default, and what runtime guardrails apply.",
    summary: "A visual inventory of Claude, Codex, and other supported model families.",
    metrics: [
      { label: "Enabled providers", value: "4" },
      { label: "Default profiles", value: "6" },
      { label: "Fallback chains", value: "8" }
    ]
  }
];

const modelCards: ModelCard[] = [
  {
    name: "Claude Sonnet 4",
    provider: "Anthropic",
    badge: "Reasoning",
    summary: "Balanced default for long-form planning, approvals, and tool-heavy workflows.",
    capabilities: ["Tools", "Long context", "Fast reasoning"]
  },
  {
    name: "GPT-5 Codex",
    provider: "OpenAI",
    badge: "Coding",
    summary: "Primary coding model for patch generation, repo navigation, and execution guidance.",
    capabilities: ["Code edits", "Tool calls", "Session control"]
  },
  {
    name: "GPT-4.1",
    provider: "OpenAI",
    badge: "General",
    summary: "Fallback general-purpose model for concise responses and lower-latency execution.",
    capabilities: ["General chat", "Summaries", "Fallback"]
  },
  {
    name: "Gemini 2.5 Pro",
    provider: "Google",
    badge: "Vision",
    summary: "Useful when image input or multimodal interpretation is needed in operator flows.",
    capabilities: ["Vision", "Large context", "Reasoning"]
  },
  {
    name: "Kimi K2.5",
    provider: "Moonshot",
    badge: "Throughput",
    summary: "High-throughput model for broad exploration and parallel operator support.",
    capabilities: ["Large context", "Fast scans", "Fallback chain"]
  },
  {
    name: "DeepSeek R1",
    provider: "DeepSeek",
    badge: "Analysis",
    summary: "Used for deliberate analytical passes where slower but more explicit reasoning is acceptable.",
    capabilities: ["Deep analysis", "Structured output", "Policy review"]
  }
];

const skillEditorActions: SkillEditorAction[] = [
  {
    label: "H1",
    onClick: (editor) => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    isActive: (editor) => editor.isActive("heading", { level: 1 })
  },
  {
    label: "H2",
    onClick: (editor) => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    isActive: (editor) => editor.isActive("heading", { level: 2 })
  },
  {
    label: "Bold",
    onClick: (editor) => editor.chain().focus().toggleBold().run(),
    isActive: (editor) => editor.isActive("bold")
  },
  {
    label: "Italic",
    onClick: (editor) => editor.chain().focus().toggleItalic().run(),
    isActive: (editor) => editor.isActive("italic")
  },
  {
    label: "Bullet List",
    onClick: (editor) => editor.chain().focus().toggleBulletList().run(),
    isActive: (editor) => editor.isActive("bulletList")
  },
  {
    label: "Ordered List",
    onClick: (editor) => editor.chain().focus().toggleOrderedList().run(),
    isActive: (editor) => editor.isActive("orderedList")
  },
  {
    label: "Quote",
    onClick: (editor) => editor.chain().focus().toggleBlockquote().run(),
    isActive: (editor) => editor.isActive("blockquote")
  }
];

const initialSkillDraft = `
<h1>Custom Skill Draft</h1>
<p>Describe the custom skill your operators should be able to use.</p>
<h2>Purpose</h2>
<p>Summarize what this skill should do and when it should be used.</p>
<h2>Instructions</h2>
<ul>
  <li>State the trigger or user intent.</li>
  <li>List the steps the skill should follow.</li>
  <li>Call out any safety or approval requirements.</li>
</ul>
<blockquote>
  <p>Use this draft area to write the content that will later become your SKILL.md instructions.</p>
</blockquote>
`;

export function SettingsPage() {
  const [selectedSectionId, setSelectedSectionId] = useState<SettingsSectionId>("skills-import");
  const [activeModelName, setActiveModelName] = useState("GPT-5 Codex");
  const selectedSection = useMemo(
    () => settingsSections.find((section) => section.id === selectedSectionId) ?? settingsSections[0],
    [selectedSectionId],
  );

  return (
    <div className="app-shell">
      <div className="app-frame">
        <header className="topbar">
          <div className="topbar__title">
            <span className="eyebrow">NightOwl Settings</span>
            <h1>Separate operational settings for imports, providers, and model policy.</h1>
            <p>
              Sessions and Channels keep their own frames. Settings now has a dedicated workspace for
              skill import flows and model administration.
            </p>
          </div>
          <div className="status-row">
            <span className="pill">{settingsSections.length} sections</span>
            <span className="pill">2 primary domains</span>
            <span className="pill">config surface</span>
          </div>
        </header>

        <div className="settings-layout">
          <aside className="settings-sidebar">
            <div className="panel__header">
              <div>
                <h2>Settings</h2>
                <p>Choose the operational domain you want to configure.</p>
              </div>
            </div>
            <div className="settings-sidebar__body">
              {settingsSections.map((section) => (
                <button
                  className="settings-nav-item"
                  data-selected={selectedSection.id === section.id}
                  key={section.id}
                  onClick={() => setSelectedSectionId(section.id)}
                  type="button"
                >
                  <span className="settings-nav-item__eyebrow">{section.eyebrow}</span>
                  <strong>{section.label}</strong>
                  <span>{section.summary}</span>
                </button>
              ))}
            </div>
          </aside>

          <section className="panel">
            <div className="panel__header">
              <div>
                <h2>{selectedSection.label}</h2>
                <p>{selectedSection.description}</p>
              </div>
            </div>

            <div className="panel__body settings-content">
              <section className="settings-hero">
                <span className="eyebrow">{selectedSection.eyebrow}</span>
                <h3>{selectedSection.title}</h3>
                <p>{selectedSection.summary}</p>
              </section>

              {selectedSection.metrics.length > 0 ? (
                <section className="channel-detail-grid">
                  {selectedSection.metrics.map((metric) => (
                    <div className="metric-card" key={metric.label}>
                      <span>{metric.label}</span>
                      <strong>{metric.value}</strong>
                    </div>
                  ))}
                </section>
              ) : null}

              {selectedSection.id === "models" ? (
                <ModelsPanel activeModelName={activeModelName} onUseModel={setActiveModelName} />
              ) : (
                <SkillsImportPanel />
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function ModelsPanel({
  activeModelName,
  onUseModel
}: {
  activeModelName: string;
  onUseModel: (modelName: string) => void;
}) {
  return (
    <section className="settings-panel-grid settings-panel-grid--models">
      {modelCards.map((model) => (
        <article
          className="settings-detail-card settings-detail-card--model"
          data-active={model.name === activeModelName}
          key={model.name}
        >
          <div className="settings-model-card__top">
            <div>
              <span className="settings-model-card__provider">{model.provider}</span>
              <h3>{model.name}</h3>
            </div>
            <span className={`badge badge--channel ${model.name === activeModelName ? "badge--active" : ""}`}>
              {model.name === activeModelName ? "In use" : model.badge}
            </span>
          </div>
          <p className="settings-model-card__summary">{model.summary}</p>
          <div className="settings-model-card__capabilities">
            {model.capabilities.map((capability) => (
              <span className="channel-route-pill" key={capability}>
                {capability}
              </span>
            ))}
          </div>
          <div className="settings-model-card__actions">
            <button
              className={model.name === activeModelName ? "button button--ghost" : "button button--primary"}
              disabled={model.name === activeModelName}
              onClick={() => onUseModel(model.name)}
              type="button"
            >
              {model.name === activeModelName ? "Current model" : "Use"}
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}

function SkillsImportPanel() {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);
  const [selection, setSelection] = useState<ImportSelection | null>(null);
  const uploadMutation = useUploadSkillSelection();

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function openFolderPicker() {
    folderInputRef.current?.click();
  }

  function handleSelection(mode: "files" | "folder", event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);

    if (files.length === 0) {
      return;
    }

    const nextSelection = buildSkillUploadSelection(files, mode);

    setSelection({
      count: nextSelection.candidates.length,
      files: nextSelection.candidates,
      label: nextSelection.label,
      names: nextSelection.names,
      rejectedCount: nextSelection.rejectedCount
    });

    event.target.value = "";
  }

  return (
    <section className="settings-panel-grid">
      <CustomSkillComposer />
      <article className="settings-detail-card">
        <input
          accept=".md,.markdown,text/markdown"
          className="settings-import-input"
          multiple
          onChange={(event) => handleSelection("files", event)}
          ref={fileInputRef}
          type="file"
        />
        <input
          className="settings-import-input"
          multiple
          onChange={(event) => handleSelection("folder", event)}
          ref={(node) => {
            folderInputRef.current = node;
            if (node) {
              node.setAttribute("directory", "");
              node.setAttribute("webkitdirectory", "");
            }
          }}
          type="file"
        />
        <div className="panel__header settings-detail-card__header">
          <div>
            <span className="settings-nav-item__eyebrow">Unified import</span>
            <h3>Import skill markdown from files or extracted folders.</h3>
            <p>
              Use one queue for direct markdown uploads or folder scans. Folder imports upload nested
              <code>SKILL.md</code> files because the current API does not accept bundled resources yet.
            </p>
          </div>
          <span className="badge">API-backed</span>
        </div>
        <div className="settings-import-actions">
          <button className="button button--primary" onClick={openFilePicker} type="button">
            Select files
          </button>
          <button className="button button--ghost" onClick={openFolderPicker} type="button">
            Select folder
          </button>
          <button
            className="button button--primary"
            disabled={!selection || selection.count === 0 || uploadMutation.isPending}
            onClick={() => {
              if (!selection || selection.count === 0) {
                return;
              }

              void uploadMutation.mutateAsync({
                files: selection.files
              });
            }}
            type="button"
          >
            {uploadMutation.isPending ? "Uploading..." : "Upload selection"}
          </button>
        </div>
        <div className="settings-import-selection">
          {selection ? (
            <>
              <strong>{selection.label}</strong>
              <span>{selection.count} skill file(s) ready for upload</span>
              {selection.rejectedCount > 0 ? (
                <span>{selection.rejectedCount} non-skill file(s) skipped from this selection</span>
              ) : null}
              <div className="settings-import-selection__list">
                {selection.names.slice(0, 4).map((name) => (
                  <span className="channel-route-pill" key={name}>
                    {name}
                  </span>
                ))}
              </div>
            </>
          ) : (
            <>
              <strong>No selection yet</strong>
              <span>Select markdown files or scan an extracted folder for nested skill manifests.</span>
            </>
          )}
          {uploadMutation.isError ? <span>{uploadMutation.error.message}</span> : null}
          {uploadMutation.isSuccess ? (
            <span>{uploadMutation.data.length} skill file(s) saved to the skills API.</span>
          ) : null}
        </div>
        <div className="settings-detail-card__body">
          {[
            "Direct file upload accepts markdown documents with YAML frontmatter.",
            "Folder upload scans for nested SKILL.md files and ignores everything else.",
            "Each queued skill is sent to /api/v1/skills/upload and stored immediately."
          ].map((item) => (
            <div className="settings-detail-row" key={item}>
              <span className="settings-detail-row__dot" aria-hidden="true" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function CustomSkillComposer() {
  const [documentHtml, setDocumentHtml] = useState(initialSkillDraft);
  const saveMutation = useSaveSkillDraft();
  const editor = useEditor({
    extensions: [StarterKit],
    content: initialSkillDraft,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        "aria-label": "Custom skill editor"
      }
    },
    onUpdate: ({ editor: currentEditor }) => {
      setDocumentHtml(currentEditor.getHTML());
    }
  });

  const documentStats = useMemo(() => {
    const plainText = editor?.getText().trim() ?? "";
    const words = plainText.length === 0 ? 0 : plainText.split(/\s+/).length;
    const blocks = documentHtml
      .split(/<\/p>|<\/li>|<\/blockquote>/)
      .map((segment) => segment.replace(/<[^>]+>/g, "").trim())
      .filter(Boolean).length;

    return {
      blocks,
      words
    };
  }, [documentHtml, editor]);

  const draftDocument = useMemo(() => buildSkillDraftDocument(documentHtml), [documentHtml]);

  return (
    <article className="settings-detail-card settings-detail-card--skill-editor">
      <div className="panel__header settings-detail-card__header">
        <div>
          <span className="settings-nav-item__eyebrow">Custom skill draft</span>
          <h3>Write custom skills directly in the settings workspace.</h3>
          <p>Use the editor to draft the instructions, role notes, and safety guidance for a new skill.</p>
        </div>
        <span className="badge">Tiptap</span>
      </div>

      <div className="settings-skill-editor">
        <div className="settings-skill-editor__toolbar" aria-label="Editor formatting">
          {skillEditorActions.map((action) => (
            <button
              className="button button--ghost settings-skill-editor__tool"
              data-active={editor ? action.isActive?.(editor) ?? false : false}
              disabled={!editor}
              key={action.label}
              onClick={() => {
                if (editor) {
                  action.onClick(editor);
                }
              }}
              type="button"
            >
              {action.label}
            </button>
          ))}
          <button
            className="button button--ghost settings-skill-editor__tool"
            disabled={!editor}
            onClick={() => {
              editor?.commands.clearContent();
              editor?.commands.focus();
            }}
            type="button"
          >
            Clear
          </button>
          <button
            className="button button--primary settings-skill-editor__tool"
            disabled={saveMutation.isPending}
            onClick={() => {
              void saveMutation.mutateAsync({
                content: draftDocument.content
              });
            }}
            type="button"
          >
            {saveMutation.isPending ? "Saving..." : "Save skill"}
          </button>
        </div>

        <EditorContent editor={editor} />
      </div>

      <div className="settings-skill-editor__footer">
        <div className="settings-import-selection">
          <strong>Draft summary</strong>
          <span>{documentStats.words} words</span>
          <span>{documentStats.blocks} content blocks</span>
          <span>Saved as <code>{draftDocument.name}</code></span>
        </div>
        <div className="settings-import-selection">
          <strong>Good skill sections</strong>
          <div className="settings-import-selection__list">
            <span className="channel-route-pill">Trigger</span>
            <span className="channel-route-pill">Workflow</span>
            <span className="channel-route-pill">Tooling</span>
            <span className="channel-route-pill">Safety</span>
          </div>
        </div>
        <div className="settings-import-selection">
          <strong>Save status</strong>
          {saveMutation.isError ? <span>{saveMutation.error.message}</span> : null}
          {saveMutation.isSuccess ? <span>Saved to skills API as {saveMutation.data.name}.</span> : null}
          {!saveMutation.isError && !saveMutation.isSuccess ? (
            <span>Save writes a generated SKILL.md document to the API.</span>
          ) : null}
        </div>
      </div>
    </article>
  );
}
