import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
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

type ImportCard = {
  id: string;
  title: string;
  platform: string;
  mode: string;
  description: string;
  steps: string[];
};

type ImportSelection = {
  count: number;
  label: string;
  names: string[];
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
      "Bring skill packs into the system, validate manifests, and support platform-specific import paths for operators.",
    summary: "File and folder import flows for macOS and Windows skill bundles.",
    metrics: [
      { label: "Imported bundles", value: "12" },
      { label: "Pending review", value: "3" },
      { label: "Trusted sources", value: "5" }
    ]
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

const importCards: ImportCard[] = [
  {
    id: "macos-file",
    title: "macOS file import",
    platform: "macOS",
    mode: "File",
    description: "Choose a zipped skill package or manifest file from Finder and stage it for validation.",
    steps: ["Open file picker", "Inspect manifest preview", "Queue import into review"]
  },
  {
    id: "macos-folder",
    title: "macOS folder import",
    platform: "macOS",
    mode: "Folder",
    description: "Point to a local skill folder so NightOwl can ingest the full directory structure.",
    steps: ["Open folder chooser", "Scan nested assets", "Validate hooks and dependencies"]
  },
  {
    id: "windows-file",
    title: "Windows file import",
    platform: "Windows",
    mode: "File",
    description: "Import an archived skill bundle or loose manifest from the Windows file explorer.",
    steps: ["Select `.zip` or manifest", "Normalize path separators", "Run trust checks before enablement"]
  },
  {
    id: "windows-folder",
    title: "Windows folder import",
    platform: "Windows",
    mode: "Folder",
    description: "Ingest an extracted skill directory while preserving scripts, assets, and templates.",
    steps: ["Browse folder tree", "Resolve relative assets", "Show import diff before activation"]
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

              <section className="channel-detail-grid">
                {selectedSection.metrics.map((metric) => (
                  <div className="metric-card" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                  </div>
                ))}
              </section>

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
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const [selections, setSelections] = useState<Record<string, ImportSelection>>({});

  function openPicker(cardId: string) {
    inputRefs.current[cardId]?.click();
  }

  function handleSelection(card: ImportCard, event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);

    if (files.length === 0) {
      return;
    }

    const names = files.map((file) => file.webkitRelativePath || file.name);
    const label =
      card.mode === "Folder"
        ? summarizeFolderSelection(names)
        : files.length === 1
          ? files[0].name
          : `${files.length} files selected`;

    setSelections((current) => ({
      ...current,
      [card.id]: {
        count: files.length,
        label,
        names
      }
    }));

    event.target.value = "";
  }

  return (
    <section className="settings-panel-grid">
      <CustomSkillComposer />
      {importCards.map((card) => (
        <article className="settings-detail-card" key={card.title}>
          <input
            className="settings-import-input"
            multiple={card.mode === "Folder"}
            onChange={(event) => handleSelection(card, event)}
            ref={(node) => {
              inputRefs.current[card.id] = node;
              if (node && card.mode === "Folder") {
                node.setAttribute("directory", "");
                node.setAttribute("webkitdirectory", "");
              }
            }}
            type="file"
          />
          <div className="panel__header settings-detail-card__header">
            <div>
              <span className="settings-nav-item__eyebrow">{card.platform}</span>
              <h3>{card.title}</h3>
              <p>{card.description}</p>
            </div>
            <span className="badge">{card.mode}</span>
          </div>
          <div className="settings-import-actions">
            <button className="button button--primary" onClick={() => openPicker(card.id)} type="button">
              Select {card.mode.toLowerCase()}
            </button>
            <button className="button button--ghost" type="button">
              Preview import
            </button>
          </div>
          <div className="settings-import-selection">
            {selections[card.id] ? (
              <>
                <strong>{selections[card.id].label}</strong>
                <span>{selections[card.id].count} item(s) ready for import</span>
                <div className="settings-import-selection__list">
                  {selections[card.id].names.slice(0, 3).map((name) => (
                    <span className="channel-route-pill" key={name}>
                      {name}
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <>
                <strong>No selection yet</strong>
                <span>Use the native picker to choose a file or folder for this platform flow.</span>
              </>
            )}
          </div>
          <div className="settings-detail-card__body">
            {card.steps.map((item) => (
              <div className="settings-detail-row" key={item}>
                <span className="settings-detail-row__dot" aria-hidden="true" />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

function CustomSkillComposer() {
  const [documentHtml, setDocumentHtml] = useState(initialSkillDraft);
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
        </div>

        <EditorContent editor={editor} />
      </div>

      <div className="settings-skill-editor__footer">
        <div className="settings-import-selection">
          <strong>Draft summary</strong>
          <span>{documentStats.words} words</span>
          <span>{documentStats.blocks} content blocks</span>
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
      </div>
    </article>
  );
}

function summarizeFolderSelection(names: string[]) {
  const firstPath = names[0] ?? "";
  const root = firstPath.split("/")[0] || firstPath.split("\\")[0] || "Selected folder";
  return root;
}
