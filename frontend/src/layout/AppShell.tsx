import type { ReactNode } from "react";

type Props = {
  sidebar: ReactNode;
  editor: ReactNode;
  tools: ReactNode;
  agent?: ReactNode;
  collapsed?: boolean;
};

export function AppShell({ sidebar, editor, tools, agent, collapsed }: Props) {
  return (
    <div className={collapsed ? "app-shell sidebar-collapsed" : "app-shell"}>
      {sidebar}
      {editor}
      {agent ?? tools}
    </div>
  );
}
