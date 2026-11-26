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
          colorInfo: "#1f4d3d",
          colorInfoBg: "#eef4f1",
          colorInfoBorder: "#bfd3c9",
          colorInfoText: "#1f4d3d",
          colorSuccess: "#1f4d3d",
          colorSuccessBg: "#e7f0ea",
          colorSuccessBorder: "#b7d1c0",
          colorSuccessText: "#1f4d3d",
          colorWarning: "#7a4e12",
          colorWarningBg: "#f8efe3",
          colorWarningBorder: "#e2ca9e",
          colorWarningText: "#7a4e12",
          colorError: "#6a3b2a",
          colorErrorBg: "#f8ece8",
          colorErrorBorder: "#dfb8ac",
          colorErrorText: "#6a3b2a",
          colorText: "#24362d",
          colorTextSecondary: "#3e5147",
          colorTextDescription: "#3e5147",
          colorTextDisabled: "#3e5147",
          colorBorder: "#d5ddd6",
          colorBorderSecondary: "#e6eae7",
          colorBgLayout: "#f5f6f8",
          borderRadius: 6,
          borderRadiusLG: 8,
          boxShadowTertiary: "none",
          fontSizeSM: 12,
          fontFamily:
            '-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif',
        },
        components: {
          Layout: { headerBg: "#fff" },
          Menu: { itemSelectedBg: "#eaf2ee", itemSelectedColor: "#245d4d" },
          Card: { borderRadiusLG: 8, boxShadowTertiary: "none" },
          Tag: {
            defaultBg: "#f2f5f3",
            defaultColor: "#24362d",
            borderRadiusSM: 4,
          },
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
