"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/use-auth";
import { apiClient } from "@/lib/api/client";
import {
  Bell,
  Lock,
  Database,
  Users,
  CheckCircle2,
  Edit2,
  BookOpen,
  LinkIcon,
  Loader2,
} from "lucide-react";
import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SettingsPage() {
  const { user } = useAuth();
  const [editEmailOpen, setEditEmailOpen] = useState(false);
  const [editPasswordOpen, setEditPasswordOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Storage configuration state
  const [storageConfig, setStorageConfig] = useState({
    provider_type: "minio",
    endpoint: "http://localhost:9000",
    bucket_name: "audiobooks",
    use_ssl: false,
  });
  const [storageLoading, setStorageLoading] = useState(false);
  const [storageConnected, setStorageConnected] = useState(false);
  const [storageMessage, setStorageMessage] = useState("");

  // Audible account linking state
  const [audibleConnected, setAudibleConnected] = useState(false);
  const [audibleEmail, setAudibleEmail] = useState("");
  const [audibleDeviceName, setAudibleDeviceName] = useState("");
  const [audibleLoading, setAudibleLoading] = useState(false);
  const [audibleLinkDialogOpen, setAudibleLinkDialogOpen] = useState(false);
  const [audibleAuthUrl, setAudibleAuthUrl] = useState("");

  // Fetch storage config on mount
  useEffect(() => {
    fetchStorageConfig();
    fetchAudibleStatus();
  }, []);

  const handleEmailChange = async () => {
    if (!newEmail) {
      setError("Email is required");
      return;
    }
    if (newEmail === user?.email) {
      setError("New email must be different from current email");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/users/me/email", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: newEmail }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update email");
      }

      setSuccess("Email updated successfully");
      setEditEmailOpen(false);
      setNewEmail("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      setError("All fields are required");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/v1/users/me/password", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update password");
      }

      setSuccess("Password updated successfully");
      setEditPasswordOpen(false);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const fetchStorageConfig = async () => {
    try {
      const data = await apiClient.request<any>("GET", "/settings/storage");
      setStorageConfig({
        provider_type: data.provider_type,
        endpoint: data.endpoint,
        bucket_name: data.bucket_name,
        use_ssl: data.use_ssl,
      });
      setStorageConnected(data.is_connected);
      setStorageMessage(data.message || "");
    } catch (err) {
      console.error("Failed to fetch storage config:", err);
    }
  };

  const fetchAudibleStatus = async () => {
    try {
      const data = await apiClient.request<any>("GET", "/settings/audible-credentials");
      setAudibleConnected(data.auth_configured === true);
      setAudibleEmail(data.audible_email || "");
      setAudibleDeviceName(data.device_name || "");
    } catch (err) {
      console.warn("Audible status check failed:", err);
      setAudibleConnected(false);
      setAudibleEmail("");
      setAudibleDeviceName("");
    }
  };

  const handleAudibleLink = async () => {
    setAudibleLoading(true);
    setError("");
    try {
      const data = await apiClient.request<any>("POST", "/auth/start");
      setAudibleAuthUrl(data.auth_url);
      setAudibleLinkDialogOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to initiate Audible linking");
    } finally {
      setAudibleLoading(false);
    }
  };

  const handleAudibleUnlink = async () => {
    if (!window.confirm("Are you sure you want to unlink your Audible account? This will remove your Audible library access.")) {
      return;
    }

    setAudibleLoading(true);
    setError("");
    try {
      await apiClient.request("DELETE", "/settings/audible-credentials");
      setAudibleConnected(false);
      setAudibleEmail("");
      setAudibleDeviceName("");
      setSuccess("Audible account unlinked successfully");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to unlink Audible account");
    } finally {
      setAudibleLoading(false);
    }
  };

  const handleStorageUpdate = async () => {
    if (!storageConfig.endpoint || !storageConfig.bucket_name) {
      setError("Endpoint and bucket name are required");
      return;
    }

    setStorageLoading(true);
    setError("");
    try {
      const data = await apiClient.request<any>("PUT", "/settings/storage", {
        body: storageConfig,
      });
      setStorageConnected(data.is_connected);
      setStorageMessage(data.message);
      setSuccess("Storage configuration updated successfully");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setStorageLoading(false);
    }
  };

  const handleTestConnection = async () => {
    setStorageLoading(true);
    setError("");
    try {
      const data = await apiClient.request<any>("POST", "/settings/storage/test", {
        body: storageConfig,
      });
      if (data.success) {
        setStorageConnected(true);
        setSuccess("Storage connection successful!");
        setStorageMessage(data.message || "Connection successful");
        setTimeout(() => setSuccess(""), 3000);
      } else {
        setStorageConnected(false);
        setError(data.error || "Connection test failed");
        setStorageMessage(data.message || "Connection failed");
      }
    } catch (err) {
      setStorageConnected(false);
      setError(err instanceof Error ? err.message : "Connection test failed");
      setStorageMessage("Connection failed");
    } finally {
      setStorageLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Status Messages */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 dark:bg-red-950/20 dark:border-red-900">
          {error}
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-green-600 dark:bg-green-950/20 dark:border-green-900">
          {success}
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage your account and preferences
        </p>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {/* Account Section */}
        <Card className="p-6 border border-border">
            <div className="flex items-center gap-3 mb-6">
              <Lock className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-semibold">Account Settings</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Email Address
                </label>
                <div className="flex items-center gap-2">
                  <Input
                    value={user?.email || ""}
                    readOnly
                    className="bg-muted"
                  />
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEditEmailOpen(true)}
                  >
                    <Edit2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Password
                </label>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  onClick={() => setEditPasswordOpen(true)}
                >
                  Change Password
                </Button>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Two-Factor Authentication
                </label>
                <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-600" />
                    <span className="text-sm">Enabled</span>
                  </div>
                  <Button variant="outline" size="sm">
                    Manage
                  </Button>
                </div>
              </div>
            </div>
          </Card>

        {/* Storage Settings */}
        <Card className="p-6 border border-border">
            <div className="flex items-center gap-3 mb-6">
              <Database className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-semibold">Storage Configuration</h2>
            </div>

            <div className="space-y-4">
              {storageMessage && (
                <div className={`p-3 rounded-lg text-sm ${
                  storageConnected
                    ? "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-400"
                    : "bg-yellow-50 text-yellow-700 dark:bg-yellow-950/20 dark:text-yellow-400"
                }`}>
                  {storageMessage}
                </div>
              )}

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Storage Provider
                </label>
                <select
                  value={storageConfig.provider_type}
                  onChange={(e) => setStorageConfig({...storageConfig, provider_type: e.target.value as any})}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                  disabled={storageLoading}
                >
                  <option value="minio">MinIO (Self-Hosted)</option>
                  <option value="aws_s3">AWS S3</option>
                  <option value="gcs">Google Cloud Storage</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Storage Endpoint
                </label>
                <Input
                  value={storageConfig.endpoint}
                  onChange={(e) => setStorageConfig({...storageConfig, endpoint: e.target.value})}
                  placeholder="http://localhost:9000"
                  disabled={storageLoading}
                />
              </div>

              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Bucket Name
                </label>
                <Input
                  value={storageConfig.bucket_name}
                  onChange={(e) => setStorageConfig({...storageConfig, bucket_name: e.target.value})}
                  placeholder="audiobooks"
                  disabled={storageLoading}
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="use_ssl"
                  checked={storageConfig.use_ssl}
                  onChange={(e) => setStorageConfig({...storageConfig, use_ssl: e.target.checked})}
                  disabled={storageLoading}
                  className="rounded"
                />
                <label htmlFor="use_ssl" className="text-sm font-medium text-muted-foreground cursor-pointer">
                  Use SSL/TLS
                </label>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleStorageUpdate}
                  disabled={storageLoading}
                  className="flex-1"
                >
                  {storageLoading ? "Saving..." : "Save Configuration"}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={storageLoading}
                  className="flex-1"
                >
                  {storageLoading ? "Testing..." : "Test Connection"}
                </Button>
              </div>
            </div>
          </Card>

          {/* Family Members */}
          <Card className="p-6 border border-border">
            <div className="flex items-center gap-3 mb-6">
              <Users className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-semibold">Family Members</h2>
            </div>

            <div className="space-y-3 mb-4">
              {[
                { name: "You", email: user?.email || "user@example.com", role: "Owner" },
                { name: "Sarah", email: "sarah@example.com", role: "Member" },
                { name: "John", email: "john@example.com", role: "Member" },
              ].map((member, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-3 bg-muted rounded-lg"
                >
                  <div>
                    <p className="font-medium text-sm">{member.name}</p>
                    <p className="text-xs text-muted-foreground">{member.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground">
                      {member.role}
                    </span>
                    {idx !== 0 && (
                      <Button variant="ghost" size="sm" className="text-red-600">
                        Remove
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <Button variant="outline" className="w-full">
              Add Family Member
            </Button>
          </Card>

          {/* Audible Account Linking */}
          <Card className="p-6 border border-border">
            <div className="flex items-center gap-3 mb-6">
              <BookOpen className="w-5 h-5 text-primary" />
              <h2 className="text-xl font-semibold">Audible Account</h2>
            </div>

            <div className="space-y-4">
              {audibleConnected ? (
                <>
                  <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-950/20 rounded-lg border border-green-200 dark:border-green-900">
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                      <span className="text-sm font-medium text-green-700 dark:text-green-400">
                        Connected
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 p-3 bg-muted rounded-lg">
                    {audibleEmail && (
                      <div>
                        <label className="text-xs font-medium text-muted-foreground block">
                          Email
                        </label>
                        <p className="text-sm font-medium">{audibleEmail}</p>
                      </div>
                    )}
                    {audibleDeviceName && (
                      <div>
                        <label className="text-xs font-medium text-muted-foreground block">
                          Device Name
                        </label>
                        <p className="text-sm font-medium">{audibleDeviceName}</p>
                      </div>
                    )}
                  </div>

                  <Button
                    variant="destructive"
                    className="w-full"
                    onClick={handleAudibleUnlink}
                    disabled={audibleLoading}
                  >
                    {audibleLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Unlinking...
                      </>
                    ) : (
                      "Unlink Audible Account"
                    )}
                  </Button>
                </>
              ) : (
                <>
                  <div className="p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded-lg border border-yellow-200 dark:border-yellow-900">
                    <p className="text-sm text-yellow-700 dark:text-yellow-400">
                      Connect your Audible account to access your audiobook library
                    </p>
                  </div>

                  <Button
                    className="w-full"
                    onClick={handleAudibleLink}
                    disabled={audibleLoading}
                  >
                    {audibleLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Linking...
                      </>
                    ) : (
                      <>
                        <LinkIcon className="w-4 h-4 mr-2" />
                        Link Audible Account
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>
          </Card>
      </div>

      {/* Notification Settings */}
      <Card className="p-6 border border-border">
        <div className="flex items-center gap-3 mb-6">
          <Bell className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Notifications</h2>
        </div>

        <div className="space-y-3">
          {[
            { label: "New Books Available", desc: "Notify me when new books are added to the library" },
            { label: "Sync Completed", desc: "Notify me when a library sync is complete" },
            { label: "Download Updates", desc: "Notify me about download progress" },
            { label: "Family Activity", desc: "Notify me about family member activity" },
          ].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-3 hover:bg-muted rounded-lg transition-colors">
              <div>
                <p className="font-medium text-sm">{item.label}</p>
                <p className="text-xs text-muted-foreground">{item.desc}</p>
              </div>
              <input type="checkbox" defaultChecked className="rounded" />
            </div>
          ))}
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="p-6 border border-red-200 bg-red-50 dark:bg-red-950/20 dark:border-red-900">
        <h2 className="text-xl font-semibold text-red-600 mb-4">Danger Zone</h2>
        <div className="space-y-3">
          <Button variant="outline" className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950">
            Clear All Data
          </Button>
          <Button
            variant="outline"
            className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            Delete Account
          </Button>
        </div>
      </Card>

      {/* Email Change Dialog */}
      <Dialog open={editEmailOpen} onOpenChange={setEditEmailOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Email Address</DialogTitle>
            <DialogDescription>
              Enter your new email address. We'll send a verification link to confirm the change.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">New Email</label>
              <Input
                type="email"
                placeholder="your-new-email@example.com"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setEditEmailOpen(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button onClick={handleEmailChange} disabled={loading}>
                {loading ? "Updating..." : "Update Email"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Password Change Dialog */}
      <Dialog open={editPasswordOpen} onOpenChange={setEditPasswordOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Change Password</DialogTitle>
            <DialogDescription>
              Enter your current password and your new password to proceed.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Current Password</label>
              <Input
                type="password"
                placeholder="Enter your current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">New Password</label>
              <Input
                type="password"
                placeholder="Enter your new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Confirm Password</label>
              <Input
                type="password"
                placeholder="Confirm your new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setEditPasswordOpen(false)}
                disabled={loading}
              >
                Cancel
              </Button>
              <Button onClick={handlePasswordChange} disabled={loading}>
                {loading ? "Updating..." : "Update Password"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Audible Linking Dialog */}
      <Dialog open={audibleLinkDialogOpen} onOpenChange={setAudibleLinkDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Audible Account</DialogTitle>
            <DialogDescription>
              You'll be redirected to Audible to authorize access to your account. After authorizing, you'll be redirected back to complete the linking process.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
              <p className="text-sm text-blue-700 dark:text-blue-400">
                Click the button below to proceed with Audible authentication.
              </p>
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setAudibleLinkDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (audibleAuthUrl) {
                    window.location.href = audibleAuthUrl;
                  }
                }}
              >
                <LinkIcon className="w-4 h-4 mr-2" />
                Proceed to Audible
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
