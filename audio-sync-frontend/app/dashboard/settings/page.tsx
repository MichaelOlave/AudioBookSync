"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { useAuth } from "@/hooks/use-auth";
import { useFamilies } from "@/hooks/use-families";
import { apiClient } from "@/lib/api/client";
import type { StorageConfig, AudibleStatusResponse, AudibleAuthStartResponse, StorageTestResponse } from "@/lib/api/types";
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
  Trash2,
  Crown,
} from "lucide-react";
import { useState, useEffect } from "react";
import { logger } from "@/lib/logger";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SettingsPage() {
  const { user } = useAuth();
  const {
    family,
    members,
    loading: familyLoading,
    actionLoading: familyActionLoading,
    fetchMyFamily,
    createFamily,
    updateFamily,
    addMember,
    removeMember,
    deleteFamily,
    transferOwnership,
    updateLibrarySharing,
  } = useFamilies();

  const [editEmailOpen, setEditEmailOpen] = useState(false);
  const [editPasswordOpen, setEditPasswordOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Family settings state
  const [createFamilyOpen, setCreateFamilyOpen] = useState(false);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [editFamilyOpen, setEditFamilyOpen] = useState(false);
  const [familyName, setFamilyName] = useState("");
  const [memberInput, setMemberInput] = useState("");
  const [memberInputType, setMemberInputType] = useState<"email" | "username">(
    "email"
  );
  const [removeMemberConfirm, setRemoveMemberConfirm] = useState<string | null>(
    null
  );
  const [deleteFamilyConfirm, setDeleteFamilyConfirm] = useState(false);
  const [transferOwnerOpen, setTransferOwnerOpen] = useState(false);
  const [selectedNewOwner, setSelectedNewOwner] = useState<string>("");

  // Storage configuration state
  const [storageConfig, setStorageConfig] = useState({
    provider_type: "minio",
    endpoint: "http://localhost:9000",
    bucket_name: "audiobooks",
    use_ssl: false,
    access_key: "",
    secret_key: "",
    region: null as string | null,
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
  const [audibleWaitingForCallback, setAudibleWaitingForCallback] =
    useState(false);
  const [audibleCallbackUrl, setAudibleCallbackUrl] = useState("");

  // Fetch storage config and family on mount
  useEffect(() => {
    const loadConfigs = async () => {
      await fetchStorageConfig();
      await fetchAudibleStatus();
    };
    loadConfigs();
    fetchMyFamily();
  }, [fetchMyFamily]);

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

      if (!data) {
        return;
      }

      const config = {
        provider_type: data.provider_type || "minio",
        endpoint: data.endpoint || "",
        bucket_name: data.bucket_name || "",
        use_ssl: typeof data.use_ssl === "boolean" ? data.use_ssl : false,
        access_key: data.access_key || "",
        secret_key: data.secret_key || "",
        region: data.region || null,
      };

      setStorageConfig(config);
      setStorageConnected(data.is_connected === true);
      setStorageMessage(data.message || "");
    } catch (err) {
      logger.error("Failed to fetch storage config:", err);
    }
  };

  const fetchAudibleStatus = async () => {
    try {
      const data = await apiClient.request<AudibleStatusResponse>(
        "GET",
        "/settings/audible-credentials",
      );
      setAudibleConnected(data.auth_configured === true);
      setAudibleEmail(data.audible_email || "");
      setAudibleDeviceName(data.device_name || "");
    } catch (err) {
      logger.warn("Audible status check failed:", err);
      setAudibleConnected(false);
      setAudibleEmail("");
      setAudibleDeviceName("");
    }
  };

  const handleAudibleLink = async () => {
    setAudibleLoading(true);
    setError("");
    try {
      const data = await apiClient.request<AudibleAuthStartResponse>("POST", "/auth/start", {
        body: {
          country_code: "us",
        },
      });
      setAudibleAuthUrl(data.login_url);
      setAudibleLinkDialogOpen(true);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to initiate Audible linking",
      );
    } finally {
      setAudibleLoading(false);
    }
  };

  const handleAudibleUnlink = async () => {
    if (
      !window.confirm(
        "Are you sure you want to unlink your Audible account? This will remove your Audible library access.",
      )
    ) {
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
      setError(
        err instanceof Error ? err.message : "Failed to unlink Audible account",
      );
    } finally {
      setAudibleLoading(false);
    }
  };

  const handleAudibleCallbackSubmit = async () => {
    if (!audibleCallbackUrl) {
      setError("Please paste the Audible redirect URL");
      return;
    }

    setAudibleLoading(true);
    setError("");
    try {
      const data = await apiClient.request<{ message?: string }>(
        "POST",
        "/auth/complete",
        {
          body: {
            redirect_url: audibleCallbackUrl,
          },
        },
      );

      setSuccess(data.message || "Audible account linked successfully");
      setAudibleConnected(true);
      setAudibleLinkDialogOpen(false);
      setAudibleWaitingForCallback(false);
      setAudibleCallbackUrl("");
      await fetchAudibleStatus();
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to complete Audible linking",
      );
    } finally {
      setAudibleLoading(false);
    }
  };

  const handleStorageUpdate = async () => {
    if (!storageConfig.bucket_name || !storageConfig.access_key || !storageConfig.secret_key) {
      setError("Bucket name, access key, and secret key are required");
      return;
    }
    if (storageConfig.provider_type !== "aws_s3" && !storageConfig.endpoint) {
      setError("Endpoint is required for this provider");
      return;
    }
    if (storageConfig.provider_type === "aws_s3" && !storageConfig.region) {
      setError("Region is required for AWS S3");
      return;
    }

    setStorageLoading(true);
    setError("");
    try {
      const data = await apiClient.request<StorageConfig>("PUT", "/settings/storage", {
        body: storageConfig,
      });
      setStorageConnected(data.is_connected);
      setStorageMessage(data.message || "");
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
      const data = await apiClient.request<StorageTestResponse>(
        "POST",
        "/settings/storage/test",
        {
          body: storageConfig,
        },
      );
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

  // Family handlers
  const handleCreateFamily = async () => {
    setError("");
    try {
      await createFamily({ name: familyName || undefined });
      setSuccess("Family created successfully!");
      setCreateFamilyOpen(false);
      setFamilyName("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create family"
      );
    }
  };

  const handleUpdateFamily = async () => {
    if (!family) return;
    setError("");
    try {
      await updateFamily(family.family_id, { name: familyName });
      setSuccess("Family name updated successfully!");
      setEditFamilyOpen(false);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update family"
      );
    }
  };

  const handleAddMember = async () => {
    if (!family || !memberInput) {
      setError("Please enter an email or username");
      return;
    }
    setError("");
    try {
      const data =
        memberInputType === "email"
          ? { email: memberInput }
          : { username: memberInput };
      await addMember(family.family_id, data);
      setSuccess("Member added successfully!");
      setAddMemberOpen(false);
      setMemberInput("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member");
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!family) return;
    setError("");
    try {
      await removeMember(family.family_id, memberId);
      setSuccess("Member removed successfully!");
      setRemoveMemberConfirm(null);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  const handleDeleteFamily = async () => {
    if (!family) return;
    setError("");
    try {
      await deleteFamily(family.family_id);
      setSuccess("Family deleted successfully!");
      setDeleteFamilyConfirm(false);
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete family");
    }
  };

  const handleTransferOwnership = async () => {
    if (!family || !selectedNewOwner) {
      setError("Please select a member");
      return;
    }
    setError("");
    try {
      await transferOwnership(family.family_id, {
        new_owner_id: selectedNewOwner,
      });
      setSuccess("Ownership transferred successfully!");
      setTransferOwnerOpen(false);
      setSelectedNewOwner("");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to transfer ownership"
      );
    }
  };

  const handleToggleLibrarySharing = async (currentSharing: boolean) => {
    setError("");
    try {
      await updateLibrarySharing(!currentSharing);
      setSuccess(
        !currentSharing
          ? "Library sharing enabled!"
          : "Library sharing disabled!"
      );
      setTimeout(() => setSuccess(""), 3000);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update library sharing"
      );
    }
  };

  const handleProviderChange = (newProvider: string) => {
    setStorageConfig({
      ...storageConfig,
      provider_type: newProvider,
      access_key: "",
      secret_key: "",
      endpoint: "",
      bucket_name: "",
      region: null,
    });
    setStorageMessage("");
    setStorageConnected(false);
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
              <div
                className={`p-3 rounded-lg text-sm ${
                  storageConnected
                    ? "bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-400"
                    : "bg-yellow-50 text-yellow-700 dark:bg-yellow-950/20 dark:text-yellow-400"
                }`}
              >
                {storageMessage}
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-muted-foreground mb-2 block">
                Storage Provider
              </label>
              <select
                value={storageConfig.provider_type}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background"
                disabled={storageLoading}
              >
                <option value="minio">MinIO (Self-Hosted)</option>
                <option value="aws_s3">AWS S3</option>
                <option value="gcs">Google Cloud Storage</option>
              </select>
            </div>

            {storageConfig.provider_type !== "aws_s3" && (
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Storage Endpoint
                </label>
                <Input
                  value={storageConfig.endpoint}
                  onChange={(e) =>
                    setStorageConfig({
                      ...storageConfig,
                      endpoint: e.target.value,
                    })
                  }
                  placeholder={
                    storageConfig.provider_type === "minio"
                      ? "http://localhost:9000"
                      : "storage.googleapis.com"
                  }
                  disabled={storageLoading}
                />
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-muted-foreground mb-2 block">
                Bucket Name
              </label>
              <Input
                value={storageConfig.bucket_name}
                onChange={(e) =>
                  setStorageConfig({
                    ...storageConfig,
                    bucket_name: e.target.value,
                  })
                }
                placeholder="audiobooks"
                disabled={storageLoading}
              />
            </div>

            {storageConfig.provider_type === "aws_s3" && (
              <div>
                <label className="text-sm font-medium text-muted-foreground mb-2 block">
                  Region
                </label>
                <Input
                  value={storageConfig.region || ""}
                  onChange={(e) =>
                    setStorageConfig({
                      ...storageConfig,
                      region: e.target.value || null,
                    })
                  }
                  placeholder="us-east-1"
                  disabled={storageLoading}
                />
              </div>
            )}

            <div>
              <label className="text-sm font-medium text-muted-foreground mb-2 block">
                Access Key
              </label>
              <Input
                value={storageConfig.access_key}
                onChange={(e) =>
                  setStorageConfig({
                    ...storageConfig,
                    access_key: e.target.value,
                  })
                }
                placeholder="minioadmin"
                disabled={storageLoading}
                type="password"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-muted-foreground mb-2 block">
                Secret Key
              </label>
              <Input
                value={storageConfig.secret_key}
                onChange={(e) =>
                  setStorageConfig({
                    ...storageConfig,
                    secret_key: e.target.value,
                  })
                }
                placeholder="minioadmin"
                disabled={storageLoading}
                type="password"
              />
            </div>

            {storageConfig.provider_type !== "aws_s3" && (
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="use_ssl"
                  checked={storageConfig.use_ssl}
                  onChange={(e) =>
                    setStorageConfig({
                      ...storageConfig,
                      use_ssl: e.target.checked,
                    })
                  }
                  disabled={storageLoading}
                  className="rounded"
                />
                <label
                  htmlFor="use_ssl"
                  className="text-sm font-medium text-muted-foreground cursor-pointer"
                >
                  Use SSL/TLS
                </label>
              </div>
            )}

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
            <h2 className="text-xl font-semibold">Family Settings</h2>
          </div>

          {familyLoading ? (
            <div className="text-center text-muted-foreground py-8">
              Loading family settings...
            </div>
          ) : !family ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                You haven&apos;t created a family yet. Create one to share your
                library with family members.
              </p>
              <Button
                onClick={() => setCreateFamilyOpen(true)}
                className="w-full"
              >
                Create Family
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-muted rounded-lg">
                <label className="text-xs font-medium text-muted-foreground block mb-1">
                  Family Name
                </label>
                <p className="text-sm font-medium">{family.name || "Unnamed"}</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-medium text-sm">Members ({members.length})</h3>
                  <div className="flex gap-2">
                    {members.length > 1 && members.some(m => m.user_id !== family?.owner_user_id) && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setTransferOwnerOpen(true)}
                        disabled={familyActionLoading}
                      >
                        Transfer Owner
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditFamilyOpen(true)}
                      disabled={familyActionLoading}
                    >
                      <Edit2 className="w-4 h-4 mr-1" />
                      Edit Name
                    </Button>
                  </div>
                </div>

                {members.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-2">
                    No members yet
                  </p>
                ) : (
                  <div className="space-y-2">
                    {members.map((member) => (
                      <div
                        key={member.user_id}
                        className="flex items-center justify-between p-3 bg-muted rounded-lg"
                      >
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-sm">
                              {member.username}
                            </p>
                            {member.user_id === family?.owner_user_id && (
                              <span className="inline-flex items-center gap-1 text-xs bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-200 px-2 py-1 rounded">
                                <Crown className="w-3 h-3" />
                                Owner
                              </span>
                            )}
                            {member.user_id === user?.id && member.user_id !== family?.owner_user_id && (
                              <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 px-2 py-1 rounded">
                                You
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {member.email}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          {member.user_id === user?.id ? (
                            <div className="flex items-center gap-2">
                              <Checkbox
                                id={`share-${member.user_id}`}
                                checked={member.share_library_with_family}
                                onCheckedChange={() =>
                                  handleToggleLibrarySharing(
                                    member.share_library_with_family
                                  )
                                }
                                disabled={familyActionLoading}
                              />
                              <label
                                htmlFor={`share-${member.user_id}`}
                                className="text-xs font-medium text-muted-foreground cursor-pointer"
                              >
                                Share Library
                              </label>
                            </div>
                          ) : member.share_library_with_family ? (
                            <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-200 px-2 py-1 rounded">
                              Library Shared
                            </span>
                          ) : (
                            <span className="text-xs bg-gray-100 text-gray-600 dark:bg-gray-900 dark:text-gray-400 px-2 py-1 rounded">
                              Library Not Shared
                            </span>
                          )}
                          {member.user_id !== user?.id && member.user_id !== family?.owner_user_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                              onClick={() =>
                                setRemoveMemberConfirm(member.user_id)
                              }
                              disabled={familyActionLoading}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => setAddMemberOpen(true)}
                disabled={familyActionLoading}
              >
                Add Family Member
              </Button>

              <Button
                variant="destructive"
                className="w-full"
                onClick={() => setDeleteFamilyConfirm(true)}
                disabled={familyActionLoading}
              >
                Delete Family
              </Button>
            </div>
          )}
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
                    Connect your Audible account to access your audiobook
                    library
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
            {
              label: "New Books Available",
              desc: "Notify me when new books are added to the library",
            },
            {
              label: "Sync Completed",
              desc: "Notify me when a library sync is complete",
            },
            {
              label: "Download Updates",
              desc: "Notify me about download progress",
            },
            {
              label: "Family Activity",
              desc: "Notify me about family member activity",
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-3 hover:bg-muted rounded-lg transition-colors"
            >
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
          <Button
            variant="outline"
            className="w-full text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
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
              Enter your new email address. We&apos;ll send a verification link to
              confirm the change.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                New Email
              </label>
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
              <label className="text-sm font-medium mb-2 block">
                Current Password
              </label>
              <Input
                type="password"
                placeholder="Enter your current password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">
                New Password
              </label>
              <Input
                type="password"
                placeholder="Enter your new password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">
                Confirm Password
              </label>
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

      {/* Create Family Dialog */}
      <Dialog open={createFamilyOpen} onOpenChange={setCreateFamilyOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Family</DialogTitle>
            <DialogDescription>
              Create a family to share your audiobook library with family
              members.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Family Name (Optional)
              </label>
              <Input
                placeholder="e.g., The Smiths"
                value={familyName}
                onChange={(e) => setFamilyName(e.target.value)}
                disabled={familyActionLoading}
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setCreateFamilyOpen(false);
                  setFamilyName("");
                }}
                disabled={familyActionLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateFamily}
                disabled={familyActionLoading}
              >
                {familyActionLoading ? "Creating..." : "Create Family"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Family Dialog */}
      <Dialog open={editFamilyOpen} onOpenChange={setEditFamilyOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Family Name</DialogTitle>
            <DialogDescription>
              Update your family&apos;s name.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Family Name
              </label>
              <Input
                placeholder="e.g., The Smiths"
                value={familyName}
                onChange={(e) => setFamilyName(e.target.value)}
                disabled={familyActionLoading}
                onFocus={() => !familyName && setFamilyName(family?.name || "")}
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setEditFamilyOpen(false);
                  setFamilyName("");
                }}
                disabled={familyActionLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleUpdateFamily}
                disabled={familyActionLoading}
              >
                {familyActionLoading ? "Updating..." : "Update Name"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Add Family Member Dialog */}
      <Dialog open={addMemberOpen} onOpenChange={setAddMemberOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Family Member</DialogTitle>
            <DialogDescription>
              Add a family member by their email or username.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Member Type
              </label>
              <div className="flex gap-2">
                <Button
                  variant={
                    memberInputType === "email" ? "default" : "outline"
                  }
                  onClick={() => {
                    setMemberInputType("email");
                    setMemberInput("");
                  }}
                  className="flex-1"
                  disabled={familyActionLoading}
                >
                  By Email
                </Button>
                <Button
                  variant={
                    memberInputType === "username" ? "default" : "outline"
                  }
                  onClick={() => {
                    setMemberInputType("username");
                    setMemberInput("");
                  }}
                  className="flex-1"
                  disabled={familyActionLoading}
                >
                  By Username
                </Button>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">
                {memberInputType === "email" ? "Email Address" : "Username"}
              </label>
              <Input
                placeholder={
                  memberInputType === "email"
                    ? "john@example.com"
                    : "johndoe"
                }
                value={memberInput}
                onChange={(e) => setMemberInput(e.target.value)}
                disabled={familyActionLoading}
                type={memberInputType === "email" ? "email" : "text"}
              />
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setAddMemberOpen(false);
                  setMemberInput("");
                }}
                disabled={familyActionLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddMember}
                disabled={familyActionLoading || !memberInput}
              >
                {familyActionLoading ? "Adding..." : "Add Member"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Remove Member Confirmation Dialog */}
      {removeMemberConfirm && (
        <Dialog
          open={!!removeMemberConfirm}
          onOpenChange={(open) => !open && setRemoveMemberConfirm(null)}
        >
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Remove Family Member</DialogTitle>
              <DialogDescription>
                Are you sure you want to remove this member from your family?
                They will no longer have access to shared libraries.
              </DialogDescription>
            </DialogHeader>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => setRemoveMemberConfirm(null)}
                disabled={familyActionLoading}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => handleRemoveMember(removeMemberConfirm)}
                disabled={familyActionLoading}
              >
                {familyActionLoading ? "Removing..." : "Remove Member"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Family Confirmation Dialog */}
      <Dialog
        open={deleteFamilyConfirm}
        onOpenChange={setDeleteFamilyConfirm}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Family</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete your family? This action cannot be
              undone. All family members will lose access to shared libraries.
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-3 justify-end">
            <Button
              variant="outline"
              onClick={() => setDeleteFamilyConfirm(false)}
              disabled={familyActionLoading}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteFamily}
              disabled={familyActionLoading}
            >
              {familyActionLoading ? "Deleting..." : "Delete Family"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Transfer Ownership Dialog */}
      <Dialog open={transferOwnerOpen} onOpenChange={setTransferOwnerOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Transfer Family Ownership</DialogTitle>
            <DialogDescription>
              Select a family member to transfer ownership to. You will become a
              regular member after the transfer.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-3 block">
                Select New Owner
              </label>
              <div className="space-y-2">
                {(members || [])
                  .filter((m) => m.user_id !== family?.owner_user_id)
                  .map((member) => (
                    <div
                      key={member.user_id}
                      className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-muted transition-colors"
                      onClick={() => setSelectedNewOwner(member.user_id)}
                    >
                      <input
                        type="radio"
                        name="owner"
                        value={member.user_id}
                        checked={selectedNewOwner === member.user_id}
                        onChange={(e) => setSelectedNewOwner(e.target.value)}
                        disabled={familyActionLoading}
                        className="rounded-full"
                      />
                      <div className="flex-1">
                        <p className="font-medium text-sm">{member.username}</p>
                        <p className="text-xs text-muted-foreground">
                          {member.email}
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
            <div className="flex gap-3 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setTransferOwnerOpen(false);
                  setSelectedNewOwner("");
                }}
                disabled={familyActionLoading}
              >
                Cancel
              </Button>
              <Button
                onClick={handleTransferOwnership}
                disabled={familyActionLoading || !selectedNewOwner}
              >
                {familyActionLoading ? "Transferring..." : "Transfer Ownership"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Audible Linking Dialog */}
      <Dialog
        open={audibleLinkDialogOpen}
        onOpenChange={setAudibleLinkDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Link Audible Account</DialogTitle>
            <DialogDescription>
              {audibleWaitingForCallback
                ? "Paste the URL from your Audible login redirect to complete linking"
                : "You&apos;ll be redirected to Audible to authorize access to your account. After authorizing, return here to complete the linking process."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {audibleWaitingForCallback ? (
              <>
                <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
                  <p className="text-sm text-blue-700 dark:text-blue-400">
                    After logging in with Audible, you&apos;ll be redirected to a
                    URL. Copy and paste that entire URL below.
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    Audible Callback URL
                  </label>
                  <Input
                    placeholder="Paste the URL you were redirected to here"
                    value={audibleCallbackUrl}
                    onChange={(e) => setAudibleCallbackUrl(e.target.value)}
                    disabled={audibleLoading}
                  />
                </div>
                <div className="flex gap-3 justify-end">
                  <Button
                    variant="outline"
                    onClick={() => {
                      setAudibleWaitingForCallback(false);
                      setAudibleCallbackUrl("");
                    }}
                    disabled={audibleLoading}
                  >
                    Back
                  </Button>
                  <Button
                    onClick={handleAudibleCallbackSubmit}
                    disabled={audibleLoading || !audibleCallbackUrl}
                  >
                    {audibleLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Completing...
                      </>
                    ) : (
                      "Complete Linking"
                    )}
                  </Button>
                </div>
              </>
            ) : (
              <>
                <div className="p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg border border-blue-200 dark:border-blue-900">
                  <p className="text-sm text-blue-700 dark:text-blue-400">
                    Click the button below to proceed with Audible
                    authentication.
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
                      logger.debug(
                        "Redirecting to Audible auth URL:",
                        audibleAuthUrl,
                      );
                      if (audibleAuthUrl) {
                        window.open(audibleAuthUrl, "_blank");
                        setAudibleWaitingForCallback(true);
                      }
                    }}
                  >
                    <LinkIcon className="w-4 h-4 mr-2" />
                    Proceed to Audible
                  </Button>
                </div>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
