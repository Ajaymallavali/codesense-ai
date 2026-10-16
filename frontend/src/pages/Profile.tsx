import React from "react";
import { useAuth } from "../hooks/useAuth";
import { SettingsPage } from "./Settings";

export function ProfilePage() {
  const { user } = useAuth();
  if (!user) return null;
  return <SettingsPage user={user} />;
}
