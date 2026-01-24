"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog";
import {
  Plus,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Calendar,
  Edit2,
  Trash2,
} from "lucide-react";
import { useSchedules, CreateScheduleData, UpdateScheduleData, Schedule } from "@/hooks/use-schedules";

export default function SchedulesPage() {
  const { schedules, loading, error, total, getSchedules, createSchedule, updateSchedule, deleteSchedule } =
    useSchedules();

  // Dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Selected schedule for edit/delete
  const [selectedSchedule, setSelectedSchedule] = useState<Schedule | null>(null);

  // Form state
  const [formData, setFormData] = useState<CreateScheduleData>({
    interval_minutes: 60,
    action: "metadata_only",
    enabled: true,
  });

  // Load schedules on mount
  useEffect(() => {
    getSchedules();
  }, [getSchedules]);

  // Auto-dismiss success message
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const formatInterval = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes} minutes`;
    } else if (minutes < 1440) {
      const hours = minutes / 60;
      return `${hours}${hours === Math.floor(hours) ? "" : ".5"} hours`;
    } else {
      const days = minutes / 1440;
      return `${days}${days === Math.floor(days) ? "" : ".5"} days`;
    }
  };

  const openCreateDialog = () => {
    setSelectedSchedule(null);
    setFormData({
      interval_minutes: 60,
      action: "metadata_only",
      enabled: true,
    });
    setFormError(null);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (schedule: Schedule) => {
    setSelectedSchedule(schedule);
    setFormData({
      interval_minutes: schedule.interval_minutes,
      action: schedule.action,
      enabled: schedule.enabled,
    });
    setFormError(null);
    setEditDialogOpen(true);
  };

  const openDeleteDialog = (schedule: Schedule) => {
    setSelectedSchedule(schedule);
    setDeleteDialogOpen(true);
  };

  const handleCreateSchedule = async () => {
    setFormError(null);

    // Validation
    if (formData.interval_minutes <= 0) {
      setFormError("Interval must be greater than 0");
      return;
    }

    setFormSubmitting(true);
    try {
      await createSchedule(formData);
      setSuccessMessage("Schedule created successfully");
      setCreateDialogOpen(false);
      setFormData({
        interval_minutes: 60,
        action: "metadata_only",
        enabled: true,
      });
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to create schedule"
      );
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleUpdateSchedule = async () => {
    if (!selectedSchedule) return;
    setFormError(null);

    // Validation
    if (formData.interval_minutes <= 0) {
      setFormError("Interval must be greater than 0");
      return;
    }

    setFormSubmitting(true);
    try {
      const updateData: UpdateScheduleData = {
        interval_minutes: formData.interval_minutes,
        action: formData.action,
        enabled: formData.enabled,
      };
      await updateSchedule(selectedSchedule.schedule_id, updateData);
      setSuccessMessage("Schedule updated successfully");
      setEditDialogOpen(false);
      setSelectedSchedule(null);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to update schedule"
      );
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteSchedule = async () => {
    if (!selectedSchedule) return;

    setFormSubmitting(true);
    try {
      await deleteSchedule(selectedSchedule.schedule_id);
      setSuccessMessage("Schedule deleted successfully");
      setDeleteDialogOpen(false);
      setSelectedSchedule(null);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to delete schedule"
      );
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col w-full">
      {/* Header Section */}
      <div className="space-y-6 border-b pb-6 -mx-8 px-8">
        {/* Title and Button */}
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Schedules</h1>
            <p className="text-muted-foreground mt-2">
              Manage automated sync schedules for your library
            </p>
          </div>
          <Button onClick={openCreateDialog} className="gap-2">
            <Plus className="w-4 h-4" />
            Create Schedule
          </Button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Error loading schedules</p>
              <p className="text-red-700 text-sm mt-1">{error}</p>
            </div>
          </div>
        )}

        {/* Success Banner */}
        {successMessage && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-green-800 font-medium">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Results Count */}
        <div className="text-sm text-muted-foreground">
          {loading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading schedules...
            </div>
          ) : (
            `${total} schedule${total !== 1 ? "s" : ""} configured`
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-auto flex flex-col">
        {!loading && schedules.length > 0 ? (
          <div className="flex-1 overflow-auto">
            <div className="border-b">
              <table className="w-full">
                <thead className="sticky top-0 bg-muted/50">
                  <tr className="border-b">
                    <th className="px-6 py-3 text-left text-sm font-semibold">
                      Interval
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">
                      Action
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">
                      Last Run
                    </th>
                    <th className="px-6 py-3 text-left text-sm font-semibold">
                      Next Run
                    </th>
                    <th className="px-6 py-3 text-center text-sm font-semibold">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {schedules.map((schedule) => (
                    <tr
                      key={schedule.schedule_id}
                      className="border-b hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-6 py-4 text-sm font-medium">
                        {formatInterval(schedule.interval_minutes)}
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          variant={
                            schedule.action === "download"
                              ? "default"
                              : "secondary"
                          }
                        >
                          {schedule.action === "download"
                            ? "Download"
                            : "Metadata Only"}
                        </Badge>
                      </td>
                      <td className="px-6 py-4">
                        <Badge
                          className={
                            schedule.enabled
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-gray-100 text-gray-800 hover:bg-gray-200"
                          }
                        >
                          {schedule.enabled ? "Enabled" : "Disabled"}
                        </Badge>
                      </td>
                      <td className="px-6 py-4 text-sm text-muted-foreground">
                        {formatDateTime(schedule.last_run_at)}
                      </td>
                      <td className="px-6 py-4 text-sm text-muted-foreground">
                        {formatDateTime(schedule.next_run_at)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEditDialog(schedule)}
                            className="gap-2"
                          >
                            <Edit2 className="w-4 h-4" />
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openDeleteDialog(schedule)}
                            className="gap-2 text-red-600 hover:bg-red-50"
                          >
                            <Trash2 className="w-4 h-4" />
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : !loading ? (
          <div className="flex-1 flex flex-col items-center justify-center">
            <Calendar className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
            <p className="text-muted-foreground mb-4">
              No schedules configured yet. Click "Create Schedule" to add one.
            </p>
            <Button onClick={openCreateDialog} className="gap-2">
              <Plus className="w-4 h-4" />
              Create Schedule
            </Button>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* Create Schedule Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Create Schedule</DialogTitle>
            <DialogClose />
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Interval Input */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Interval (minutes)
              </label>
              <Input
                type="number"
                min="1"
                value={formData.interval_minutes}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    interval_minutes: parseInt(e.target.value) || 60,
                  })
                }
                placeholder="60"
                disabled={formSubmitting}
              />
              <p className="text-xs text-muted-foreground">
                {formatInterval(formData.interval_minutes)}
              </p>
            </div>

            {/* Action Select */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Action</label>
              <Select
                value={formData.action}
                onValueChange={(value) =>
                  setFormData({
                    ...formData,
                    action: value as "metadata_only" | "download",
                  })
                }
              >
                <SelectTrigger disabled={formSubmitting}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="metadata_only">Metadata Only</SelectItem>
                  <SelectItem value="download">Download</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Enabled Checkbox */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled-create"
                checked={formData.enabled}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    enabled: e.target.checked,
                  })
                }
                disabled={formSubmitting}
                className="rounded"
              />
              <label
                htmlFor="enabled-create"
                className="text-sm font-medium cursor-pointer"
              >
                Enable schedule immediately
              </label>
            </div>

            {/* Form Error */}
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {formError}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 justify-end pt-4">
              <Button
                variant="outline"
                onClick={() => setCreateDialogOpen(false)}
                disabled={formSubmitting}
              >
                Cancel
              </Button>
              <Button onClick={handleCreateSchedule} disabled={formSubmitting}>
                {formSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  "Create Schedule"
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edit Schedule Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit Schedule</DialogTitle>
            <DialogClose />
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Interval Input */}
            <div className="space-y-2">
              <label className="text-sm font-medium">
                Interval (minutes)
              </label>
              <Input
                type="number"
                min="1"
                value={formData.interval_minutes}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    interval_minutes: parseInt(e.target.value) || 60,
                  })
                }
                placeholder="60"
                disabled={formSubmitting}
              />
              <p className="text-xs text-muted-foreground">
                {formatInterval(formData.interval_minutes)}
              </p>
            </div>

            {/* Action Select */}
            <div className="space-y-2">
              <label className="text-sm font-medium">Action</label>
              <Select
                value={formData.action}
                onValueChange={(value) =>
                  setFormData({
                    ...formData,
                    action: value as "metadata_only" | "download",
                  })
                }
              >
                <SelectTrigger disabled={formSubmitting}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="metadata_only">Metadata Only</SelectItem>
                  <SelectItem value="download">Download</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Enabled Checkbox */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="enabled-edit"
                checked={formData.enabled}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    enabled: e.target.checked,
                  })
                }
                disabled={formSubmitting}
                className="rounded"
              />
              <label
                htmlFor="enabled-edit"
                className="text-sm font-medium cursor-pointer"
              >
                Enabled
              </label>
            </div>

            {/* Form Error */}
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {formError}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 justify-end pt-4">
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={formSubmitting}
              >
                Cancel
              </Button>
              <Button onClick={handleUpdateSchedule} disabled={formSubmitting}>
                {formSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Delete Schedule</DialogTitle>
            <DialogClose />
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-700 font-medium">
                Are you sure you want to delete this schedule?
              </p>
              <p className="text-red-600 text-sm mt-2">
                {selectedSchedule && (
                  <>
                    This will delete the schedule that runs every{" "}
                    {formatInterval(selectedSchedule.interval_minutes)} and
                    performs {selectedSchedule.action === "download" ? "downloads" : "metadata syncs"}.
                    This action cannot be undone.
                  </>
                )}
              </p>
            </div>

            {/* Form Error */}
            {formError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {formError}
              </div>
            )}

            {/* Buttons */}
            <div className="flex gap-3 justify-end pt-4">
              <Button
                variant="outline"
                onClick={() => setDeleteDialogOpen(false)}
                disabled={formSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteSchedule}
                disabled={formSubmitting}
              >
                {formSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  "Delete Schedule"
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
