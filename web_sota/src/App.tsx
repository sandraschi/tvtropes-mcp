import { useEffect } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useSearchParams,
} from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoggerProvider } from "@/context/LoggerContext";
import { useZoom } from "@/lib/use-zoom";
import { BritProcedurals } from "@/pages/BritProcedurals";
import { ChatPage } from "@/pages/ChatPage";
import { CurrentSeason } from "@/pages/CurrentSeason";
import { Dashboard } from "@/pages/Dashboard";
import { DetectiveConan } from "@/pages/DetectiveConan";
import { HelpPage } from "@/pages/HelpPage";
import { LogPage } from "@/pages/LogPage";
import { OllamaPage } from "@/pages/OllamaPage";
import { PagesPage } from "@/pages/PagesPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { TropeGraph } from "@/pages/TropeGraph";
import { TropeSearch } from "@/pages/TropeSearch";
import { WorkBrowser } from "@/pages/WorkBrowser";

/** Reads ?lookup=Namespace/PageName and redirects to /search?trope=... */
function LookupRedirect() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const lookup = params.get("lookup");

  useEffect(() => {
    if (lookup) {
      navigate(`/search?trope=${encodeURIComponent(lookup)}`, { replace: true });
    } else {
      navigate("/dashboard", { replace: true });
    }
  }, [lookup, navigate]);

  return null;
}

export default function App() {
  useZoom();
  return (
    <LoggerProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<LookupRedirect />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="search" element={<TropeSearch />} />
            <Route path="works" element={<WorkBrowser />} />
            <Route path="conan" element={<DetectiveConan />} />
            <Route path="britprocedurals" element={<BritProcedurals />} />
            <Route path="season" element={<CurrentSeason />} />
            <Route path="graph" element={<TropeGraph />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="ollama" element={<OllamaPage />} />
            <Route path="pages" element={<PagesPage />} />
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
