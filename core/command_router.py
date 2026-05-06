from __future__ import annotations

from pathlib import Path

from browser.chatgpt_controller import ChatGPTController
from core.memory_manager import MemoryManager
from core.paper_workspace import PaperWorkspaceManager
from core.prompt_builder import PromptBuilder
from core.topic_extractor import extract_first_recommended_topic
from core.workflow_graph import PaperWorkflowGraph
from core.workflow_state import PaperWorkflowState


class CommandRouter:
    def __init__(
        self,
        workspace: PaperWorkspaceManager,
        memory: MemoryManager,
        prompts: PromptBuilder,
        chatgpt: ChatGPTController,
    ) -> None:
        self.workspace = workspace
        self.memory = memory
        self.prompts = prompts
        self.chatgpt = chatgpt
        self.workflow = PaperWorkflowGraph(workspace, memory, prompts, chatgpt)
        self.active_paper_id: str | None = None

    async def paper_create(self, topic_area: str, keywords_or_focus: str) -> str:
        discovery_state: PaperWorkflowState = await self.workflow.ainvoke(
            {
                "command": "paper_create",
                "topic_area": topic_area,
                "keywords_or_focus": keywords_or_focus,
            }
        )
        self._raise_if_error(discovery_state)
        paper_id = discovery_state["paper_id"]
        selected_topic = extract_first_recommended_topic(discovery_state["latest_response"])

        validation_state: PaperWorkflowState = await self.workflow.ainvoke(
            {
                "command": "paper_validate",
                "paper_id": paper_id,
                "selected_topic": selected_topic,
            }
        )
        self._raise_if_error(validation_state)

        final_state: PaperWorkflowState = await self.workflow.ainvoke(
            {"command": "paper_finalize", "paper_id": paper_id}
        )
        self._raise_if_error(final_state)
        self.active_paper_id = paper_id

        rename_note = (
            f"\nChat rename warning: `{final_state['rename_error']}`"
            if final_state.get("rename_error")
            else ""
        )
        folder_note = (
            f"\nFolder rename warning: `{final_state['folder_rename_error']}`"
            if final_state.get("folder_rename_error")
            else ""
        )
        return (
            f"Created and finalized `{paper_id}`.\n"
            f"Auto-selected first topic: {selected_topic}\n"
            f"Title: {final_state.get('title', 'Untitled')}\n"
            f"Abstract words: {final_state.get('abstract_word_count', 0)}\n"
            f"Workspace: `{final_state.get('workspace_path', discovery_state['workspace_path'])}`\n"
            f"Saved files:\n"
            f"- `{discovery_state['response_file']}`\n"
            f"- `{validation_state['response_file']}`\n"
            f"- `{final_state.get('response_file', '')}`\n"
            f"- `{final_state.get('final_file', '')}`"
            f"{rename_note}{folder_note}"
        )

    async def paper_validate(self, paper_id: str, selected_topic: str) -> str:
        state: PaperWorkflowState = await self.workflow.ainvoke(
            {
                "command": "paper_validate",
                "paper_id": paper_id,
                "selected_topic": selected_topic,
            }
        )
        self._raise_if_error(state)
        self.active_paper_id = paper_id
        return (
            f"Validated `{paper_id}` and saved ChatGPT response.\n"
            f"Selected topic: {selected_topic}\n"
            f"Saved: `{state['response_file']}`"
        )

    async def paper_finalize(self, paper_id: str) -> str:
        state: PaperWorkflowState = await self.workflow.ainvoke(
            {"command": "paper_finalize", "paper_id": paper_id}
        )
        self._raise_if_error(state)
        self.active_paper_id = paper_id
        rename_note = (
            f"\nChat rename warning: `{state['rename_error']}`" if state.get("rename_error") else ""
        )
        folder_note = (
            f"\nFolder rename warning: `{state['folder_rename_error']}`"
            if state.get("folder_rename_error")
            else ""
        )
        return (
            f"Finalized `{paper_id}`.\n"
            f"Title: {state.get('title', 'Untitled')}\n"
            f"Abstract words: {state.get('abstract_word_count', 0)}\n"
            f"Chat/folder name: `{state.get('chat_name', '')}`\n"
            f"Saved: `{state.get('final_file', '')}`"
            f"{rename_note}{folder_note}"
        )

    async def paper_auto_continue(self, paper_id: str) -> str:
        metadata = self.workspace.load_metadata(paper_id)
        discovery_path = Path(metadata["workspace_path"]) / "01_topic_discovery.md"
        if not discovery_path.exists():
            raise RuntimeError(f"`01_topic_discovery.md` was not found for {paper_id}.")
        selected_topic = extract_first_recommended_topic(discovery_path.read_text(encoding="utf-8"))

        validation_state: PaperWorkflowState = await self.workflow.ainvoke(
            {
                "command": "paper_validate",
                "paper_id": paper_id,
                "selected_topic": selected_topic,
            }
        )
        self._raise_if_error(validation_state)
        final_state: PaperWorkflowState = await self.workflow.ainvoke(
            {"command": "paper_finalize", "paper_id": paper_id}
        )
        self._raise_if_error(final_state)
        self.active_paper_id = paper_id
        return (
            f"Auto-continued and finalized `{paper_id}`.\n"
            f"Auto-selected first topic: {selected_topic}\n"
            f"Title: {final_state.get('title', 'Untitled')}\n"
            f"Saved: `{final_state.get('final_file', '')}`"
        )

    def paper_status(self, paper_id: str) -> str:
        metadata = self.workspace.load_metadata(paper_id)
        files = ", ".join(metadata.get("files", [])) or "None yet"
        selected = metadata.get("selected_topic") or "Not selected"
        title = metadata.get("title") or "Not finalized"
        chat_name = metadata.get("chat_name") or "Not renamed"
        return (
            f"`{metadata['paper_id']}` status: `{metadata.get('status', 'unknown')}`\n"
            f"Selected topic: {selected}\n"
            f"Title: {title}\n"
            f"Abstract words: {metadata.get('abstract_word_count', 0)}\n"
            f"Files: {files}\n"
            f"Workspace: `{metadata.get('workspace_path', '')}`\n"
            f"Chat name: {chat_name}"
        )

    def paper_list(self) -> str:
        papers = self.workspace.list_papers()
        memory = self.memory.load().get("selected_topics", [])
        if not papers and not memory:
            return "No PaperDev workspaces or memory records found yet."
        lines = ["Paper workspaces:"]
        for item in papers:
            title_or_topic = item.get("title") or item.get("selected_topic") or item.get("topic_area", "")
            lines.append(
                f"- `{item.get('paper_id')}` | `{item.get('status', 'unknown')}` | "
                f"{title_or_topic} | `{item.get('workspace_path', '')}`"
            )
        if memory:
            lines.append("\nMemory records:")
            for item in memory:
                lines.append(
                    f"- `{item.get('paper_id', '')}` | {item.get('title') or item.get('selected_topic', '')}"
                )
        return "\n".join(lines)

    async def paper_resume(self, paper_id: str) -> str:
        metadata = self.workspace.load_metadata(paper_id)
        chat_url = metadata.get("chat_url")
        if not chat_url:
            raise RuntimeError(f"No saved ChatGPT chat URL for {paper_id}.")
        await self.chatgpt.open_chatgpt(chat_url)
        self.active_paper_id = paper_id
        metadata["status"] = metadata.get("status") or "resumed"
        self.workspace.save_metadata(metadata)
        return f"Resumed `{paper_id}` in the saved ChatGPT chat.\nWorkspace: `{metadata['workspace_path']}`"

    async def close(self) -> None:
        await self.chatgpt.close_browser()

    @staticmethod
    def _raise_if_error(state: PaperWorkflowState) -> None:
        if state.get("error"):
            raise RuntimeError(state["error"])
