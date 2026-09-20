import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import type { ChatRecord, DocumentRecord } from "../../lib/api";

type Props = {
  collapsed: boolean;
  onToggle: () => void;
  search: string;
  onSearch: (v: string) => void;
  chats: ChatRecord[];
  documents: DocumentRecord[];
  activeChatId: number | null;
  activeDocId: number | null;
  onNewChat: () => void;
  onSelectChat: (id: number) => void;
  onSelectDoc: (id: number) => void;
  onRenameChat: (id: number, title: string) => void;
  onPinChat: (id: number, pinned: boolean) => void;
  onDeleteChat: (id: number) => void;
  onSettings: () => void;
};

type ChatMenu = { x: number; y: number; chatId: number };

function dayGroup(iso: string): "today" | "yesterday" | "earlier" {
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const y = new Date(start);
  y.setDate(y.getDate() - 1);
  if (d >= start) return "today";
  if (d >= y) return "yesterday";
  return "earlier";
}

function ChatNavItem({
  chat,
  active,
  onSelect,
  onContextMenu,
}: {
  chat: ChatRecord;
  active: boolean;
  onSelect: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
}) {
  return (
    <li>
      <button
        type="button"
        className={active ? "nav-item active" : "nav-item"}
        onClick={onSelect}
        onContextMenu={onContextMenu}
      >
        {chat.pinned ? <span className="pin-mark" aria-hidden>📌</span> : <span className="pin-mark empty" />}
        {chat.title}
      </button>
    </li>
  );
}

export function Sidebar({
  collapsed,
  onToggle,
  search,
  onSearch,
  chats,
  documents,
  activeChatId,
  activeDocId,
  onNewChat,
  onSelectChat,
  onSelectDoc,
  onRenameChat,
  onPinChat,
  onDeleteChat,
  onSettings,
}: Props) {
  const { t } = useTranslation();
  const [chatMenu, setChatMenu] = useState<ChatMenu | null>(null);
  const q = search.toLowerCase();
  const filteredChats = chats.filter((c) => c.title.toLowerCase().includes(q));
  const filteredDocs = documents.filter((d) => d.title.toLowerCase().includes(q));

  const pinnedChats = useMemo(() => filteredChats.filter((c) => c.pinned), [filteredChats]);

  const grouped = useMemo(() => {
    const g: Record<string, ChatRecord[]> = { today: [], yesterday: [], earlier: [] };
    for (const c of filteredChats.filter((x) => !x.pinned)) {
      g[dayGroup(c.updated_at || "")].push(c);
    }
    return g;
  }, [filteredChats]);

  const menuChat = chatMenu ? chats.find((c) => c.id === chatMenu.chatId) : null;

  useEffect(() => {
    if (!chatMenu) return;
    const close = () => setChatMenu(null);
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [chatMenu]);

  const openChatMenu = (e: React.MouseEvent, chatId: number) => {
    e.preventDefault();
    e.stopPropagation();
    setChatMenu({ x: e.clientX, y: e.clientY, chatId });
  };

  const renameChat = (chatId: number, currentTitle: string) => {
    setChatMenu(null);
    const next = window.prompt(t("sidebar.renameChatPrompt"), currentTitle);
    if (next === null) return;
    const title = next.trim();
    if (title) onRenameChat(chatId, title);
  };

  const confirmDelete = (chatId: number) => {
    setChatMenu(null);
    if (window.confirm(t("sidebar.deleteChatConfirm"))) onDeleteChat(chatId);
  };

  return (
    <aside className={collapsed ? "sidebar collapsed" : "sidebar"}>
      <div className="sidebar-top">
        {!collapsed && <h1 className="brand">{t("app.title")}</h1>}
        <button type="button" className="icon-btn" onClick={onToggle} title={t("sidebar.collapse")}>
          {collapsed ? "»" : "«"}
        </button>
      </div>
      <button type="button" className="btn primary new-chat" onClick={onNewChat}>
        {collapsed ? "+" : `+ ${t("sidebar.newChat")}`}
      </button>
      {!collapsed && (
        <input
          className="search-input"
          placeholder={t("sidebar.search")}
          value={search}
          onChange={(e) => onSearch(e.target.value)}
        />
      )}
      {collapsed ? (
        <nav className="icon-nav">
          <button type="button" className="icon-btn" title={t("sidebar.chats")}>
            💬
          </button>
          <button type="button" className="icon-btn" title={t("sidebar.documents")}>
            📄
          </button>
          <button type="button" className="icon-btn" title={t("app.settings")} onClick={onSettings}>
            ⚙
          </button>
        </nav>
      ) : (
        <>
          <section>
            <h3>{t("sidebar.chats")}</h3>
            {pinnedChats.length > 0 && (
              <div>
                <div className="muted small">{t("sidebar.pinned")}</div>
                <ul className="nav-list">
                  {pinnedChats.map((c) => (
                    <ChatNavItem
                      key={c.id}
                      chat={c}
                      active={c.id === activeChatId}
                      onSelect={() => onSelectChat(c.id)}
                      onContextMenu={(e) => openChatMenu(e, c.id)}
                    />
                  ))}
                </ul>
              </div>
            )}
            {(["today", "yesterday", "earlier"] as const).map((key) =>
              grouped[key].length ? (
                <div key={key}>
                  <div className="muted small">{t(`sidebar.${key}`)}</div>
                  <ul className="nav-list">
                    {grouped[key].map((c) => (
                      <ChatNavItem
                        key={c.id}
                        chat={c}
                        active={c.id === activeChatId}
                        onSelect={() => onSelectChat(c.id)}
                        onContextMenu={(e) => openChatMenu(e, c.id)}
                      />
                    ))}
                  </ul>
                </div>
              ) : null,
            )}
          </section>
          <section>
            <h3>{t("sidebar.documents")}</h3>
            <ul className="nav-list">
              {filteredDocs.map((d) => (
                <li key={d.id}>
                  <button
                    type="button"
                    className={d.id === activeDocId ? "nav-item active" : "nav-item"}
                    onClick={() => onSelectDoc(d.id)}
                  >
                    📄 {d.title}
                  </button>
                </li>
              ))}
            </ul>
          </section>
          <button type="button" className="btn ghost settings-btn" onClick={onSettings}>
            ⚙ {t("app.settings")}
          </button>
        </>
      )}
      {chatMenu && menuChat && (
        <div
          className="context-menu"
          style={{ top: chatMenu.y, left: chatMenu.x }}
          role="menu"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            type="button"
            className="context-menu-item"
            onClick={() => renameChat(menuChat.id, menuChat.title)}
          >
            {t("sidebar.renameChat")}
          </button>
          <button
            type="button"
            className="context-menu-item"
            onClick={() => {
              setChatMenu(null);
              onPinChat(menuChat.id, !menuChat.pinned);
            }}
          >
            {menuChat.pinned ? t("sidebar.unpinChat") : t("sidebar.pinChat")}
          </button>
          <button type="button" className="context-menu-item danger" onClick={() => confirmDelete(menuChat.id)}>
            {t("sidebar.deleteChat")}
          </button>
        </div>
      )}
    </aside>
  );
}
