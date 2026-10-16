import React, { FormEvent, useState } from "react";
import { CheckCircle2, Github, Key, Lock, Mail, UserRound, AlertCircle } from "lucide-react";
import { User } from "../types";
import { useAuth } from "../hooks/useAuth";
import { authApi } from "../services/authApi";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";

interface SettingsPageProps {
  user: User;
}

export function SettingsPage({ user }: SettingsPageProps) {
  const { updateUser } = useAuth();

  // Profile Form State
  const [displayName, setDisplayName] = useState(user.displayName);
  const [githubUsername, setGithubUsername] = useState(user.githubUsername ?? "");
  const [githubToken, setGithubToken] = useState(user.githubToken ?? "");
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileError, setProfileError] = useState("");

  // Password Form State
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");

  async function handleProfileSubmit(e: FormEvent) {
    e.preventDefault();
    setProfileSuccess("");
    setProfileError("");
    setIsUpdatingProfile(true);

    try {
      const updated = await authApi.updateProfile({
        displayName: displayName.trim(),
        githubUsername: githubUsername.trim() || undefined,
        githubToken: githubToken.trim() || undefined,
      });
      updateUser(updated);
      setProfileSuccess("Profile settings updated successfully!");
    } catch (err) {
      setProfileError(err instanceof Error ? err.message : "Failed to update profile.");
    } finally {
      setIsUpdatingProfile(false);
    }
  }

  async function handlePasswordSubmit(e: FormEvent) {
    e.preventDefault();
    setPasswordSuccess("");
    setPasswordError("");

    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New password and confirmation do not match.");
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await authApi.updatePassword({ oldPassword, newPassword });
      setPasswordSuccess("Password changed successfully!");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : "Failed to update password.");
    } finally {
      setIsUpdatingPassword(false);
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Profile Card */}
      <Card title="Profile & Integration Settings" subtitle="Configure your name and GitHub credentials">
        {profileSuccess && (
          <div className="mb-4 flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-800">
            <CheckCircle2 size={15} />
            <span>{profileSuccess}</span>
          </div>
        )}

        {profileError && (
          <div className="mb-4 flex items-center gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            <AlertCircle size={15} />
            <span>{profileError}</span>
          </div>
        )}

        <form onSubmit={handleProfileSubmit} className="space-y-4">
          <Input
            label="Email Address (Account ID)"
            type="email"
            value={user.email}
            readOnly
            icon={<Mail size={15} />}
          />

          <Input
            label="Display Name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            icon={<UserRound size={15} />}
            required
          />

          <Input
            label="Linked GitHub Username"
            type="text"
            placeholder="e.g. torvalds"
            value={githubUsername}
            onChange={(e) => setGithubUsername(e.target.value)}
            icon={<Github size={15} />}
          />

          <div>
            <Input
              label="GitHub Personal Access Token (PAT)"
              type="password"
              placeholder="ghp_••••••••••••••••••••••••••••••••••••"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              icon={<Key size={15} />}
            />
            <p className="mt-1 text-[11px] text-slate-400">
              Required for private repo access.{" "}
              <a
                href="https://github.com/settings/tokens"
                target="_blank"
                rel="noreferrer"
                className="text-teal-700 hover:underline"
              >
                Generate token on GitHub &rarr;
              </a>
            </p>
          </div>

          <Button type="submit" variant="primary" size="sm" isLoading={isUpdatingProfile}>
            Save Profile Settings
          </Button>
        </form>
      </Card>

      {/* Password & Security Card */}
      <Card title="Security & Password" subtitle="Change your account authentication credentials">
        {passwordSuccess && (
          <div className="mb-4 flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 p-3 text-xs font-medium text-emerald-800">
            <CheckCircle2 size={15} />
            <span>{passwordSuccess}</span>
          </div>
        )}

        {passwordError && (
          <div className="mb-4 flex items-center gap-2 rounded border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
            <AlertCircle size={15} />
            <span>{passwordError}</span>
          </div>
        )}

        <form onSubmit={handlePasswordSubmit} className="space-y-4">
          <Input
            label="Current Password"
            type="password"
            placeholder="••••••••"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            icon={<Lock size={15} />}
            required
          />

          <Input
            label="New Password"
            type="password"
            placeholder="••••••••"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            icon={<Lock size={15} />}
            required
          />

          <Input
            label="Confirm New Password"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            icon={<Lock size={15} />}
            required
          />

          <Button type="submit" variant="primary" size="sm" isLoading={isUpdatingPassword}>
            Update Password
          </Button>
        </form>
      </Card>
    </div>
  );
}
