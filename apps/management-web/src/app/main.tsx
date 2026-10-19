import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { App as AntApp, ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "../styles/base.css";
import { Shell } from "./Shell";
const client = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error: any) =>
        error?.status !== 401 && error?.status !== 403 && count < 1,
      staleTime: 1500,
    },
    mutations: { retry: false },
  },
});

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: "#245d4d",
          colorInfo: "#245d4d",
          colorBgLayout: "#f5f6f8",
          borderRadius: 8,
          fontFamily:
            '-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif',
        },
        components: {
          Layout: { headerBg: "#fff" },
          Menu: { itemSelectedBg: "#eaf2ee", itemSelectedColor: "#245d4d" },
        },
      }}
    >
      <AntApp>
        <QueryClientProvider client={client}>
          <BrowserRouter>
            <Shell />
          </BrowserRouter>
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);
