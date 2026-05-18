import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoggerProvider } from "@/context/LoggerContext";
import { AppLayout } from "@/components/layout/AppLayout";
import { Dashboard } from "@/pages/Dashboard";
import { TropeSearch } from "@/pages/TropeSearch";
import { WorkBrowser } from "@/pages/WorkBrowser";
import { TropeGraph } from "@/pages/TropeGraph";
import { SettingsPage } from "@/pages/SettingsPage";
import { HelpPage } from "@/pages/HelpPage";
import { LogPage } from "@/pages/LogPage";
import { ChatPage } from "@/pages/ChatPage";
import { OllamaPage } from "@/pages/OllamaPage";

export default function App() {
  return (
    <LoggerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="search" element={<TropeSearch />} />
            <Route path="works" element={<WorkBrowser />} />
            <Route path="graph" element={<TropeGraph />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="ollama" element={<OllamaPage />} />
            <Route path="log" element={<LogPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="help" element={<HelpPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </LoggerProvider>
  );
}
