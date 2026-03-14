import { useMutation } from "@tanstack/react-query";
import { saveSkillContent, uploadSkillFile } from "shared/api/skills";

export function useSaveSkillDraft() {
  return useMutation({
    mutationFn: ({ content }: { content: string }) => saveSkillContent(content)
  });
}

export function useUploadSkillSelection() {
  return useMutation({
    mutationFn: async ({ files }: { files: File[] }) => Promise.all(files.map((file) => uploadSkillFile(file)))
  });
}
