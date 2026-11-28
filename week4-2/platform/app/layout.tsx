import type { ReactNode } from "react";

export const metadata = { title: "第四周 RSI-Flow 复现" };

export default function Layout({ children }: { children: ReactNode }) {
  return <html lang="zh-CN"><body style={{ margin: 0 }}>{children}</body></html>;
}
