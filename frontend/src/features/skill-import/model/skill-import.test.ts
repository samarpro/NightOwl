import { describe, expect, it } from "vitest";
import { buildSkillDraftDocument, buildSkillUploadSelection } from "features/skill-import/model/skill-import";

describe("buildSkillDraftDocument", () => {
  it("builds valid skill frontmatter from editor html", () => {
    const result = buildSkillDraftDocument(`
      <h1>Release Notes Helper</h1>
      <p>Prepare release notes from merged pull requests.</p>
      <ul><li>Collect merged PRs</li></ul>
    `);

    expect(result.name).toBe("release-notes-helper");
    expect(result.description).toBe("Prepare release notes from merged pull requests.");
    expect(result.content).toContain("name: release-notes-helper");
    expect(result.content).toContain('description: "Prepare release notes from merged pull requests."');
  });
});

describe("buildSkillUploadSelection", () => {
  it("keeps markdown files from direct file uploads", () => {
    const files = [
      new File(["# a"], "SKILL.md", { type: "text/markdown" }),
      new File(["ignore"], "notes.txt", { type: "text/plain" })
    ];

    const result = buildSkillUploadSelection(files, "files");

    expect(result.candidates).toHaveLength(1);
    expect(result.rejectedCount).toBe(1);
  });

  it("keeps nested skill manifests from folder uploads", () => {
    const file = new File(["# a"], "SKILL.md", { type: "text/markdown" });
    Object.defineProperty(file, "webkitRelativePath", {
      configurable: true,
      value: "demo-skill/SKILL.md"
    });

    const result = buildSkillUploadSelection(
      [file, new File(["ignore"], "README.md", { type: "text/markdown" })],
      "folder"
    );

    expect(result.candidates).toHaveLength(1);
    expect(result.label).toBe("demo-skill");
  });
});
