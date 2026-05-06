from __future__ import annotations

import logging
from pathlib import Path

from langgraph.graph import END, StateGraph

from browser.chatgpt_controller import ChatGPTController
from core.memory_manager import MemoryManager
from core.paper_workspace import PaperWorkspaceManager
from core.prompt_builder import PromptBuilder
from core.title_extractor import build_clean_final_file, generate_chat_name
from core.workflow_state import PaperWorkflowState


logger = logging.getLogger(__name__)


class PaperWorkflowGraph:
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
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(PaperWorkflowState)
        graph.add_node("command_received", self.command_received_node)
        graph.add_node("create_workspace_node", self.create_workspace_node)
        graph.add_node("build_topic_discovery_prompt_node", self.build_topic_discovery_prompt_node)
        graph.add_node("validate_topic_node", self.validate_topic_node)
        graph.add_node("finalize_title_abstract_node", self.finalize_title_abstract_node)
        graph.add_node("browser_ready", self.browser_ready_node)
        graph.add_node("send_prompt_node", self.send_prompt_node)
        graph.add_node("capture_response_node", self.capture_response_node)
        graph.add_node("metadata_updated", self.metadata_updated_node)
        graph.add_node("rename_chat_node", self.rename_chat_node)
        graph.add_node("rename_folder_node", self.rename_folder_node)
        graph.add_node("update_memory_node", self.update_memory_node)
        graph.add_node("finalized", self.finalized_node)
        graph.add_node("error_handler_node", self.error_handler_node)

        graph.set_entry_point("command_received")
        graph.add_conditional_edges(
            "command_received",
            self.route_command,
            {
                "create": "create_workspace_node",
                "validate": "validate_topic_node",
                "finalize": "finalize_title_abstract_node",
                "error": "error_handler_node",
            },
        )
        graph.add_edge("create_workspace_node", "build_topic_discovery_prompt_node")
        graph.add_edge("build_topic_discovery_prompt_node", "browser_ready")
        graph.add_edge("validate_topic_node", "browser_ready")
        graph.add_edge("finalize_title_abstract_node", "browser_ready")
        graph.add_edge("browser_ready", "send_prompt_node")
        graph.add_edge("send_prompt_node", "capture_response_node")
        graph.add_conditional_edges(
            "capture_response_node",
            self.route_after_capture,
            {
                "metadata": "metadata_updated",
                "rename_chat": "rename_chat_node",
                "error": "error_handler_node",
            },
        )
        graph.add_edge("metadata_updated", END)
        graph.add_edge("rename_chat_node", "rename_folder_node")
        graph.add_edge("rename_folder_node", "update_memory_node")
        graph.add_edge("update_memory_node", "finalized")
        graph.add_edge("finalized", END)
        graph.add_edge("error_handler_node", END)
        return graph.compile()

    async def ainvoke(self, state: PaperWorkflowState) -> PaperWorkflowState:
        return await self.graph.ainvoke(state)

    async def command_received_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        state.setdefault("command", "")
        return state

    def route_command(self, state: PaperWorkflowState) -> str:
        command = state.get("command", "")
        if command == "paper_create":
            return "create"
        if command == "paper_validate":
            return "validate"
        if command == "paper_finalize":
            return "finalize"
        state["error"] = f"Unsupported workflow command: {command}"
        return "error"

    async def create_workspace_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        month_name, year = self.workspace.current_month_parts()
        memory_highest = self.memory.highest_paper_number_for_month(month_name, year)
        metadata = self.workspace.create_workspace(
            state["topic_area"], state["keywords_or_focus"], memory_highest=memory_highest
        )
        state.update(
            {
                "metadata": metadata,
                "paper_id": metadata["paper_id"],
                "paper_number": metadata["paper_number"],
                "month_name": metadata["month_name"],
                "year": metadata["year"],
                "output_root": str(self.workspace.output_root),
                "month_folder": metadata["month_folder"],
                "workspace_path": metadata["workspace_path"],
            }
        )
        return state

    async def build_topic_discovery_prompt_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        state["prompt_text"] = self.prompts.build_topic_discovery(
            state["topic_area"], state["keywords_or_focus"], self.memory.previous_topics_text()
        )
        return state

    async def validate_topic_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        metadata = self.workspace.load_metadata(state["paper_id"])
        metadata["selected_topic"] = state["selected_topic"]
        metadata["status"] = "validating"
        self.workspace.save_metadata(metadata)
        state.update(
            {
                "metadata": metadata,
                "paper_number": metadata["paper_number"],
                "month_name": metadata["month_name"],
                "year": metadata["year"],
                "topic_area": metadata.get("topic_area", ""),
                "keywords_or_focus": metadata.get("keywords_or_focus", ""),
                "workspace_path": metadata["workspace_path"],
                "month_folder": metadata["month_folder"],
                "chat_url": metadata.get("chat_url", ""),
                "prompt_text": self.prompts.build_topic_validation(state["selected_topic"]),
            }
        )
        return state

    async def finalize_title_abstract_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        metadata = self.workspace.load_metadata(state["paper_id"])
        metadata["status"] = "finalizing"
        self.workspace.save_metadata(metadata)
        state.update(
            {
                "metadata": metadata,
                "paper_number": metadata["paper_number"],
                "month_name": metadata["month_name"],
                "year": metadata["year"],
                "selected_topic": metadata.get("selected_topic", ""),
                "workspace_path": metadata["workspace_path"],
                "month_folder": metadata["month_folder"],
                "chat_url": metadata.get("chat_url", ""),
                "prompt_text": self.prompts.build_title_abstract(),
            }
        )
        return state

    async def browser_ready_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        chat_url = state.get("chat_url") or state.get("metadata", {}).get("chat_url") or None
        await self.chatgpt.open_chatgpt(chat_url)
        if state.get("command") == "paper_create":
            await self.chatgpt.create_new_chat()
        return state

    async def send_prompt_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        await self.chatgpt.send_prompt(state["prompt_text"])
        await self.chatgpt.wait_for_response_complete()
        return state

    async def capture_response_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        response = await self.chatgpt.read_latest_response()
        if not response:
            raise RuntimeError("ChatGPT response was empty or could not be read.")
        metadata = state["metadata"]
        metadata["chat_url"] = await self.chatgpt.get_current_chat_url()
        state["chat_url"] = metadata["chat_url"]
        state["latest_response"] = response

        if state["command"] == "paper_create":
            path = self.workspace.save_output_file(metadata, "01_topic_discovery.md", response)
            metadata["status"] = "topic_discovered"
        elif state["command"] == "paper_validate":
            path = self.workspace.save_output_file(metadata, "02_topic_validation.md", response)
            metadata["selected_topic"] = state.get("selected_topic", metadata.get("selected_topic", ""))
            metadata["status"] = "validated"
        else:
            path = self.workspace.save_output_file(metadata, "03_title_abstract_raw.md", response)
            clean, title, abstract, word_count = build_clean_final_file(response)
            final_path = self.workspace.save_output_file(metadata, "final_title_abstract.txt", clean)
            metadata["title"] = title
            metadata["abstract"] = abstract
            metadata["abstract_word_count"] = word_count
            if word_count and not 120 <= word_count <= 130:
                warnings = metadata.setdefault("warnings", [])
                warning = f"Abstract word count is {word_count}; expected 120-130."
                if warning not in warnings:
                    warnings.append(warning)
            state.update(
                {
                    "title": title,
                    "abstract": abstract,
                    "abstract_word_count": word_count,
                    "final_file": str(final_path),
                    "chat_name": generate_chat_name(metadata["paper_number"], metadata["month_name"], title),
                }
            )
            metadata["chat_name"] = state["chat_name"]
            metadata["status"] = "final_response_saved"
        self.workspace.save_metadata(metadata)
        state["response_file"] = str(path)
        state["metadata"] = metadata
        return state

    def route_after_capture(self, state: PaperWorkflowState) -> str:
        if state.get("error"):
            return "error"
        if state.get("command") == "paper_finalize":
            return "rename_chat"
        return "metadata"

    async def metadata_updated_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        self.workspace.save_metadata(state["metadata"])
        return state

    async def rename_chat_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        metadata = state["metadata"]
        chat_name = state.get("chat_name") or metadata.get("chat_name")
        if not chat_name:
            return state
        try:
            await self.chatgpt.rename_current_chat(chat_name)
        except Exception as exc:
            logger.warning("ChatGPT chat rename failed: %s", exc)
            state["rename_error"] = str(exc)
            metadata["chat_rename_error"] = str(exc)
        metadata["chat_name"] = chat_name
        self.workspace.save_metadata(metadata)
        return state

    async def rename_folder_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        metadata = state["metadata"]
        chat_name = state.get("chat_name") or metadata.get("chat_name")
        if not chat_name:
            return state
        try:
            metadata = self.workspace.rename_workspace(metadata, chat_name)
        except Exception as exc:
            logger.warning("Workspace folder rename failed: %s", exc)
            state["folder_rename_error"] = str(exc)
            metadata.setdefault("warnings", []).append(f"Folder rename failed: {exc}")
            self.workspace.save_metadata(metadata)
        state["metadata"] = metadata
        state["workspace_path"] = metadata["workspace_path"]
        return state

    async def update_memory_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        metadata = state["metadata"]
        metadata["status"] = "finalized"
        self.workspace.save_metadata(metadata)
        self.memory.record_selected_topic(metadata)
        return state

    async def finalized_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        return state

    async def error_handler_node(self, state: PaperWorkflowState) -> PaperWorkflowState:
        logger.error("Workflow error: %s", state.get("error"))
        return state
