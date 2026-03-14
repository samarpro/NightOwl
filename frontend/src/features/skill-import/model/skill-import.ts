export type SkillUploadSelection = {
  candidates: File[];
  rejectedCount: number;
  totalCount: number;
  label: string;
  names: string[];
};

export type SkillDraftDocument = {
  content: string;
  description: string;
  name: string;
  title: string;
};

export function buildSkillDraftDocument(documentHtml: string): SkillDraftDocument {
  const normalizedHtml = documentHtml.trim();
  const title =
    getHtmlText(normalizedHtml, /<h[12][^>]*>([\s\S]*?)<\/h[12]>/i) || "Custom Skill Draft";
  const description =
    getHtmlText(normalizedHtml, /<p[^>]*>([\s\S]*?)<\/p>/i) ||
    "Custom skill created in the NightOwl settings workspace.";
  const name = normalizeSkillName(title);
  const body = normalizedHtml || `<h1>${escapeHtml(title)}</h1>`;
  const safeDescription = JSON.stringify(description);

  return {
    content: `---
name: ${name}
description: ${safeDescription}
user_invocable: true
---

${body}
`,
    description,
    name,
    title
  };
}

export function buildSkillUploadSelection(files: File[], mode: "files" | "folder"): SkillUploadSelection {
  const candidates =
    mode === "folder"
      ? files.filter((file) => file.name.toLowerCase() === "skill.md")
      : files.filter((file) => isMarkdownFile(file.name));
  const names = candidates.map((file) => file.webkitRelativePath || file.name);
  const label =
    candidates.length === 0
      ? mode === "folder"
        ? "No SKILL.md files found in this folder"
        : "No markdown skill files selected"
      : mode === "folder"
        ? summarizeFolderSelection(names)
        : candidates.length === 1
          ? names[0]
          : `${candidates.length} skill files selected`;

  return {
    candidates,
    rejectedCount: Math.max(files.length - candidates.length, 0),
    totalCount: files.length,
    label,
    names
  };
}

function normalizeSkillName(value: string) {
  const normalized = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");

  return normalized.length > 0 ? normalized : "custom-skill";
}

function getHtmlText(value: string, pattern: RegExp) {
  const match = value.match(pattern);
  if (!match?.[1]) {
    return "";
  }

  return match[1].replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function isMarkdownFile(name: string) {
  return /\.(md|markdown)$/i.test(name);
}

function summarizeFolderSelection(names: string[]) {
  const firstPath = names[0] ?? "";
  return firstPath.split("/")[0] || firstPath.split("\\")[0] || "Selected folder";
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
