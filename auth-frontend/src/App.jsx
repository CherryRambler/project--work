import { useAuth } from "./hooks/useAuth";
import AuthPage from "./pages/AuthPage";
import DashboardPage from "./pages/DashboardPage";
import "./styles/global.css";
import "./App.css";

export default function App() {
  const { user } = useAuth();
  return (
    <div className="app-wrap">
      {user ? <DashboardPage /> : <AuthPage />}
    </div>
  );
}