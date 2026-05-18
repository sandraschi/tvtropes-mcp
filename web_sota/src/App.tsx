import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { Dashboard } from "@/pages/Dashboard";
import { TropeSearch } from "@/pages/TropeSearch";
import { WorkBrowser } from "@/pages/WorkBrowser";
import { TropeGraph } from "@/pages/TropeGraph";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="search" element={<TropeSearch />} />
          <Route path="works" element={<WorkBrowser />} />
          <Route path="graph" element={<TropeGraph />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
