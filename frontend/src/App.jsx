import { useEffect, useState } from "react";
import ChatBox from "./components/ChatBox.jsx";
import LoginForm from "./components/LoginForm.jsx";
import { getStoredUser, getToken, logout } from "./services/api.js";

export default function App() {
  const [user, setUser] = useState(() => (getToken() ? getStoredUser() : null));

  useEffect(() => {
    // Dipancarkan oleh interceptor saat server menolak token (401).
    const handler = () => setUser(null);
    window.addEventListener("sva-unauthorized", handler);
    return () => window.removeEventListener("sva-unauthorized", handler);
  }, []);

  if (!user) return <LoginForm onLoggedIn={setUser} />;

  return (
    <ChatBox
      user={user}
      onLogout={() => {
        logout();
        setUser(null);
      }}
    />
  );
}
