import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CustomAgentPanel } from "./components/agent/CustomAgentPanel";
import { EditorWorkspace } from "./components/editor/EditorWorkspace";
import { ProposalPanel } from "./components/ProposalPanel";
import { SettingsModal } from "./components/SettingsModal";
import { Sidebar } from "./components/sidebar/Sidebar";
import { AIToolsPanel } from "./components/tools/AIToolsPanel";
import { AppShell } from "./layout/AppShell";
import type { SelectionInfo } from "./components/RichEditor";
import {
  api,
  formatApiError,
  htmlToPlain,
  type AppSettings,
  type ChatMessage,
  type ChatRecord,
  type CommandPreset,
  type DocumentRecord,
  type EditProposal,
  type ExportFormat,
  type IntentResult,
  type VersionMeta,
} from "./lib/api";
import "./styles/tokens.css";
import "./App.css";

function App() {
  const { i18n, t } = useTranslation();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [commands, setCommands] = useState<CommandPreset[]>([]);
  const [chats, setChats] = useState<ChatRecord[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [doc, setDoc] = useState<DocumentRecord | null>(null);
  const [content, setContent] = useState("<p></p>");
  const [selection, setSelection] = useState<SelectionInfo | null>(null);
  const [applyWhole, setApplyWhole] = useState(true);
  const [proposal, setProposal] = useState<EditProposal | null>(null);
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [agentOpen, setAgentOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [intent, setIntent] = useState<IntentResult | null>(null);
  const [lastUserMessage, setLastUserMessage] = useState("");

  const refreshLists = useCallback(async (projectId?: number | null) => {
    const [c, d] = await Promise.all([
      api.listChats(projectId ?? undefined),
      api.listDocuments(projectId ?? undefined),
    ]);
    setChats(c);
    setDocuments(d);
  }, []);

  const loadDoc = useCallback(async (id: number) => {
    const d = await api.getDocument(id);
    setDoc(d);
    setContent(d.content);
    setProposal(null);
    setVersions(await api.listVersions(id));
  }, []);

  const loadMessages = useCallback(async (chatId: number) => {
    setMessages(await api.listMessages(chatId));
  }, []);

  const ensureWorkspace = useCallback(async (): Promise<{
    doc: DocumentRecord;
    chatId: number;
  }> => {
    if (activeChatId && doc) return { doc, chatId: activeChatId };
    if (activeChatId && !doc) {
      const chat = await api.getChat(activeChatId);
      const docId = chat.document_ids?.[0] ?? chat.document_id;
      if (docId) {
        const d = await api.getDocument(docId);
        setDoc(d);
        setContent(d.content);
        setVersions(await api.listVersions(docId));
        return { doc: d, chatId: activeChatId };
      }
    }
    const chat = await api.createChat(activeProjectId ?? undefined);
    setActiveChatId(chat.id);
    setActiveProjectId(chat.project_id);
    if (!chat.document_id) throw new Error("No document for new chat");
    const d = await api.getDocument(chat.document_id);
    setDoc(d);
    setContent(d.content);
    setVersions(await api.listVersions(d.id));
    await refreshLists(chat.project_id);
    return { doc: d, chatId: chat.id };
  }, [activeChatId, activeProjectId, doc, refreshLists]);

  const toolActionType = (cmd: CommandPreset) =>
    cmd.actionType ??
    (cmd.category === "analyze"
      ? "chat_only"
      : cmd.category === "create"
        ? "new_document"
        : "inline_edit");

  useEffect(() => {
    void (async () => {
      try {
        const [s, cmds, boot] = await Promise.all([
          api.getSettings(),
          api.listCommands(),
          api.bootstrap(),
        ]);
        setSettings(s);
        setCommands(cmds);
        void i18n.changeLanguage(s.ui_locale);
        setActiveChatId(boot.id);
        setActiveProjectId(boot.project_id);
        await refreshLists(boot.project_id);
        if (boot.document_id) await loadDoc(boot.document_id);
        await loadMessages(boot.id);
      } catch (e) {
        setError(formatApiError(String(e)));
      }
    })();
  }, [i18n, loadDoc, loadMessages, refreshLists]);

  const showError = (e: unknown) => setError(formatApiError(String(e)));

  const rangeForEdit = () => {
    if (applyWhole || !selection) return { start: undefined as number | undefined, end: undefined as number | undefined };
    return { start: selection.start, end: selection.end };
  };

  const runTool = async (cmd: CommandPreset) => {
    setLoading(true);
    setError(null);
    try {
      const { doc: currentDoc, chatId } = await ensureWorkspace();
      const { start, end } = rangeForEdit();
      const plain = htmlToPlain(content);
      const action = toolActionType(cmd);
      if (action === "new_document") {
        const res = await api.generateDocument({
          chat_id: chatId,
          document_id: currentDoc.id,
          message: cmd.id,
          command_id: cmd.id,
          action_type: "create",
          interpreted_scope: "document",
          content: plain,
        });
        if (res.document_id) {
          await refreshLists(activeProjectId);
          await loadDoc(res.document_id);
        }
        await loadMessages(chatId);
      } else if (action === "chat_only") {
        setAgentOpen(true);
        await api.agentConfirm({
          chat_id: chatId,
          document_id: currentDoc.id,
          message: cmd.id,
          command_id: cmd.id,
          action_type: "analyze",
          interpreted_scope: "document",
          content: plain,
        });
        await loadMessages(chatId);
      } else {
        const result = await api.proposeEdit(currentDoc.id, {
          command_id: cmd.id,
          content: plain,
          selection_start: start,
          selection_end: end,
        });
        setProposal(result);
      }
    } catch (e) {
      showError(e);
    } finally {
      setLoading(false);
    }
  };

  const sendAgent = async (text: string) => {
    setLastUserMessage(text);
    setLoading(true);
    setError(null);
    try {
      const { doc: currentDoc, chatId } = await ensureWorkspace();
      const { start, end } = rangeForEdit();
      const result = await api.agentIntent({
        chat_id: chatId,
        document_id: currentDoc.id,
        message: text,
        content: htmlToPlain(content),
        selection_start: start,
        selection_end: end,
      });
      setIntent(result);
      await loadMessages(chatId);
      if (!result.needs_clarification) {
        await confirmAgent(result, text, currentDoc, chatId);
      }
    } catch (e) {
      showError(e);
    } finally {
      setLoading(false);
    }
  };

  const confirmAgent = async (
    intentOverride?: IntentResult,
    message?: string,
    docOverride?: DocumentRecord,
    chatIdOverride?: number,
  ) => {
    const i = intentOverride ?? intent;
    if (!i) return;
    setLoading(true);
    setError(null);
    try {
      const ws =
        docOverride && chatIdOverride
          ? { doc: docOverride, chatId: chatIdOverride }
          : await ensureWorkspace();
      const { doc: currentDoc, chatId } = ws;
      const { start, end } = rangeForEdit();
      const res = await api.agentConfirm({
        chat_id: chatId,
        document_id: currentDoc.id,
        message: message ?? lastUserMessage,
        command_id: i.command_hint,
        action_type: i.action_type,
        interpreted_scope: i.interpreted_scope,
        create_action: i.create_action,
        content: htmlToPlain(content),
        selection_start: start,
        selection_end: end,
      });
      setIntent(null);
      await loadMessages(chatId);
      if (res.kind === "edit" && res.proposal) setProposal(res.proposal);
      if (res.kind === "create" && res.document_id) {
        await refreshLists(activeProjectId);
        await loadDoc(res.document_id);
      }
    } catch (e) {
      showError(e);
    } finally {
      setLoading(false);
    }
  };

  const acceptProposal = async () => {
    if (!doc || !proposal) return;
    try {
      const res = await api.acceptEdit(doc.id, {
        proposed_full_text: proposal.proposed_full_text,
        command_id: proposal.command_id,
        label: proposal.command_id,
      });
      setContent(res.content);
      setProposal(null);
      setVersions(await api.listVersions(doc.id));
      await refreshLists(activeProjectId);
    } catch (e) {
      showError(e);
    }
  };

  const onNewChat = async () => {
    const chat = await api.createChat(activeProjectId ?? undefined);
    setActiveChatId(chat.id);
    await refreshLists(activeProjectId);
    if (chat.document_id) await loadDoc(chat.document_id);
    await loadMessages(chat.id);
    setProposal(null);
  };

  const onSelectChat = async (id: number) => {
    setActiveChatId(id);
    setProposal(null);
    try {
      const chat = await api.getChat(id);
      const docId = chat.document_ids?.[0] ?? chat.document_id;
      if (docId) await loadDoc(docId);
      else {
        const linked = documents.find((d) => d.chat_id === id);
        if (linked) await loadDoc(linked.id);
      }
      await loadMessages(id);
    } catch (e) {
      showError(e);
    }
  };

  const onRenameChat = async (id: number, title: string) => {
    try {
      await api.patchChat(id, { title });
      await refreshLists(activeProjectId);
    } catch (e) {
      showError(e);
    }
  };

  const onPinChat = async (id: number, pinned: boolean) => {
    try {
      await api.patchChat(id, { pinned });
      await refreshLists(activeProjectId);
    } catch (e) {
      showError(e);
    }
  };

  const onExportDocument = async (format: ExportFormat) => {
    if (!doc) return;
    try {
      await api.downloadDocument(doc.id, format);
    } catch (e) {
      showError(e);
    }
  };

  const onDeleteChat = async (id: number) => {
    try {
      await api.deleteChat(id);
      const nextChats = await api.listChats(activeProjectId ?? undefined);
      setChats(nextChats);
      if (activeChatId === id) {
        if (nextChats.length) await onSelectChat(nextChats[0].id);
        else await onNewChat();
      } else {
        await refreshLists(activeProjectId);
      }
    } catch (e) {
      showError(e);
    }
  };

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveContent = useCallback(
    (html: string) => {
      if (!doc) return;
      const docId = doc.id;
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => {
        void api.updateDocument(docId, { content: html }).catch(showError);
      }, 450);
    },
    [doc],
  );

  const patchSettings = async (patch: Partial<AppSettings>) => {
    const s = await api.patchSettings(patch);
    setSettings(s);
    if (patch.ui_locale) void i18n.changeLanguage(patch.ui_locale);
  };

  return (
    <div className="app">
      {error && <div className="error-banner">{error}</div>}
      <AppShell
        collapsed={collapsed}
        sidebar={
          <Sidebar
            collapsed={collapsed}
            onToggle={() => setCollapsed((v) => !v)}
            search={search}
            onSearch={setSearch}
            chats={chats}
            documents={documents}
            activeChatId={activeChatId}
            activeDocId={doc?.id ?? null}
            onNewChat={() => void onNewChat()}
            onSelectChat={(id) => void onSelectChat(id)}
            onSelectDoc={(id) => void loadDoc(id)}
            onRenameChat={(id, title) => void onRenameChat(id, title)}
            onPinChat={(id, pinned) => void onPinChat(id, pinned)}
            onDeleteChat={(id) => void onDeleteChat(id)}
            onSettings={() => setSettingsOpen(true)}
          />
        }
        editor={
          <div className="center-column">
            {settings && (
              <div className={settings.ollama_connected ? "status-pill ok" : "status-pill warn"}>
                {settings.ollama_connected ? "Polza" : "Polza off"}
              </div>
            )}
            {loading && <div className="ai-busy" role="status">{t("tools.working")}</div>}
            <EditorWorkspace
              content={content}
              onChange={(html) => {
                setContent(html);
                void saveContent(html);
              }}
              selection={selection}
              onSelection={setSelection}
              commands={commands}
              onTool={(id) => {
                const cmd = commands.find((c) => c.id === id);
                if (cmd) void runTool(cmd);
              }}
              onCustom={() => setAgentOpen(true)}
              onUpload={async (file) => {
                try {
                  let current = doc;
                  if (!current) {
                    const chat = await api.createChat(activeProjectId ?? undefined);
                    setActiveChatId(chat.id);
                    if (!chat.document_id) throw new Error("No document after new chat");
                    current = await api.getDocument(chat.document_id);
                    setDoc(current);
                  }
                  const res = await api.importFile(current.id, file);
                  setContent(res.content);
                  setVersions(await api.listVersions(current.id));
                  await refreshLists(activeProjectId);
                } catch (e) {
                  showError(e);
                }
              }}
              versions={versions}
              onRestore={async (id) => {
                if (!doc) return;
                const res = await api.restoreVersion(doc.id, id);
                setContent(res.content);
              }}
              applyWhole={applyWhole}
              onApplyWhole={setApplyWhole}
              showEmpty
              canExport={Boolean(doc)}
              onExport={(format) => void onExportDocument(format)}
            />
            {proposal && (
              <div className="preview-strip">
                <ProposalPanel
                  proposal={proposal}
                  loading={loading}
                  onAccept={() => void acceptProposal()}
                  onReject={() => setProposal(null)}
                />
              </div>
            )}
          </div>
        }
        tools={
          agentOpen ? (
            <CustomAgentPanel
              open
              onClose={() => setAgentOpen(false)}
              messages={messages}
              loading={loading}
              awaitingConfirm={Boolean(intent?.needs_clarification)}
              onSend={(t) => void sendAgent(t)}
              onConfirm={() => void confirmAgent()}
              onRevise={() => setIntent(null)}
            />
          ) : (
            <AIToolsPanel
              commands={commands}
              loading={loading}
              onTool={(c) => void runTool(c)}
              onCustom={() => setAgentOpen(true)}
            />
          )
        }
      />
      <SettingsModal
        open={settingsOpen}
        settings={settings}
        onClose={() => setSettingsOpen(false)}
        onSave={(p) => void patchSettings(p)}
      />
    </div>
  );
}

export default App;
