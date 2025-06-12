<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { Skeleton } from "$lib/components/ui/skeleton";
  import { Button } from "$lib/components/ui/button";
  import { io as socket } from "$lib/api/socket";
  import {
    Play,
    Pause,
    RotateCw,
    Trash2,
    Mic,
    Clock,
    Check,
    Edit,
    Calendar,
    Loader2,
    StopCircle,
    AlertCircle,
  } from "lucide-svelte";
  import { onMount } from "svelte";
  import { fade, slide, scale } from "svelte/transition";
  import { quintOut, cubicOut } from "svelte/easing";
  import { toast } from "svelte-sonner";

  // Define Recording interface
  interface Recording {
    timestamp: string;
    isPlaying?: boolean;
    name?: string;
    duration?: number; // Duration in seconds
    progress?: number; // Progress percentage (0-100)
  }

  let {
    recordings = $bindable(),
    lastSensorUpdateTime,
    class: className = "",
  }: {
    recordings?: Recording[];
    lastSensorUpdateTime: number;
    class?: string;
  } = $props();

  let activePlayback = $state<string | null>(null);
  let renaming = $state<string | null>(null);
  let newName = $state("");
  let showConfirmDelete = $state<string | null>(null);
  let progressIntervals = $state<Record<string, number>>({});
  let editingDuration = $state<string | null>(null);
  let newDuration = $state<number>(0);
  let hoverProgress = $state<Record<string, number | null>>({});

  // New recording state
  let isRecording = $state(false);
  let recordingStartTime = $state<Date | null>(null);
  let recordingDuration = $state(0);
  let recordingInterval = $state<number | null>(null);

  // Format timestamp for display
  function formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch (e) {
      return timestamp; // Fallback to original if parsing fails
    }
  }

  // Format duration for display
  function getRelativeTime(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

      if (diffInSeconds < 60) {
        return "just now";
      } else if (diffInSeconds < 3600) {
        return Math.floor(diffInSeconds / 60) + " min ago";
      } else if (diffInSeconds < 86400) {
        return Math.floor(diffInSeconds / 3600) + " hr ago";
      } else {
        return Math.floor(diffInSeconds / 86400) + " days ago";
      }
    } catch (e) {
      return ""; // Fallback if parsing fails
    }
  }

  // ----------------------
  // Recording Management
  // ----------------------

  // Start a new recording
  function startRecording(): void {
    socket.emit("start_recording");
  }

  // Stop the current recording
  function stopRecording(): void {
    socket.emit("stop_recording");
  }

  // Handle server start recording event
  function handleStartRecording(): void {
    isRecording = true;
    recordingStartTime = new Date();
    recordingDuration = 0;

    // Start a timer to track recording duration
    if (recordingInterval) clearInterval(recordingInterval);
    recordingInterval = setInterval(() => {
      recordingDuration += 1;
    }, 1000);

    // Show toast notification
    toast.success("Recording started", {
      description: "Joystick movements are being recorded.",
    });
  }

  // Handle server stop recording event
  function handleStopRecording(data: {
    timestamp: string;
    duration: number;
  }): void {
    isRecording = false;

    // Clear interval
    if (recordingInterval) {
      clearInterval(recordingInterval);
      recordingInterval = null;
    }

    // Add the new recording to the list (at the top)
    if (data && data.timestamp) {
      recordings = [
        {
          timestamp: data.timestamp,
          name: `Recording ${data.duration || recordingDuration}s`,
          duration: data.duration || recordingDuration,
          isPlaying: false,
          progress: 0,
        },
        ...recordings,
      ];
    }

    // Reset recording state
    recordingStartTime = null;
    recordingDuration = 0;

    // Show toast notification
    toast.success("Recording saved", {
      description: "Your joystick recording has been saved.",
    });
  }

  // Handle playback error
  function handlePlaybackError(data: { message: string }): void {
    toast.error("Playback error", {
      description: data.message,
    });
  }

  // ----------------------
  // Playback Management
  // ----------------------

  // Play a recording
  function playRecording(timestamp: string): void {
    socket.emit("play_recording", { timestamp });
  }

  // Stop a recording playback
  function stopPlayback(timestamp: string): void {
    socket.emit("stop_playback", { timestamp });
  }

  // Handle start playback event from backend
  function handleStartPlayback(data: {
    timestamp: string;
    duration: number;
  }): void {
    const { timestamp } = data;
    activePlayback = timestamp;

    // If we don't have this recording yet, add it at the top of the list
    if (!recordings.some((r) => r.timestamp === timestamp)) {
      recordings = [
        {
          timestamp,
          isPlaying: true,
          progress: 0,
          duration: data.duration || 10,
        },
        ...recordings,
      ];
    } else {
      // Update the existing recording
      recordings = recordings.map((r) =>
        r.timestamp === timestamp ? { ...r, isPlaying: true, progress: 0 } : r
      );
    }

    // Start progress tracking
    startProgressTracking(timestamp);
  }
  
  // Handle stop playback event
  function handleStopPlayback(): void {
    if (activePlayback) {
      // Stop progress tracking
      clearProgressTracking(activePlayback);

      // Reset recording state
      recordings = recordings.map((r) =>
        r.timestamp === activePlayback
          ? { ...r, isPlaying: false, progress: 0 }
          : r
      );
      activePlayback = null;
    }
  }

  // Start tracking progress for a playing recording
  function startProgressTracking(timestamp: string): void {
    // Clear any existing interval first
    clearProgressTracking(timestamp);

    // Find the recording and its duration
    const recording = recordings.find((r) => r.timestamp === timestamp);
    if (!recording) return;

    // Use a default duration of 10 seconds if none is set
    const duration = recording.duration || 10;

    // Calculate update interval - we want 100 steps for smooth progress
    const updateInterval = duration * 10; // Update every 10ms per second of duration

    // Start the progress interval
    progressIntervals[timestamp] = setInterval(() => {
      // Find the recording and update its progress
      const recordingIndex = recordings.findIndex(
        (r) => r.timestamp === timestamp
      );
      if (recordingIndex === -1) {
        clearProgressTracking(timestamp);
        return;
      }

      // Get the current progress
      let progress = recordings[recordingIndex].progress || 0;

      // Increment the progress
      progress += 1;

      // If progress reaches 100, we'll let the stop event handle reset
      if (progress >= 100) {
        progress = 100;
        // Auto-stop after completion if the backend doesn't send a stop event
        setTimeout(() => {
          if (activePlayback === timestamp) {
            handleStopPlayback();
          }
        }, 500);
      }

      // Update the recording
      recordings = [
        ...recordings.slice(0, recordingIndex),
        { ...recordings[recordingIndex], progress },
        ...recordings.slice(recordingIndex + 1),
      ];
    }, updateInterval);
  }

  // Clear progress tracking interval
  function clearProgressTracking(timestamp: string): void {
    if (progressIntervals[timestamp]) {
      clearInterval(progressIntervals[timestamp]);
      delete progressIntervals[timestamp];
    }
  }

  // Delete a recording
  function deleteRecording(timestamp: string): void {
    socket.emit("delete_recording", { timestamp });
    recordings = recordings.filter((r) => r.timestamp !== timestamp);
    if (activePlayback === timestamp) {
      activePlayback = null;
    }
    showConfirmDelete = null;
  }

  // Start renaming a recording
  function startRename(timestamp: string): void {
    const recording = recordings.find((r) => r.timestamp === timestamp);
    if (recording) {
      newName = recording.name || "";
      renaming = timestamp;
    }
  }

  // Complete renaming a recording
  function completeRename(): void {
    if (renaming) {
      const finalName = newName.trim() || undefined;
      socket.emit("rename_recording", { timestamp: renaming, name: finalName });

      recordings = recordings.map((r) =>
        r.timestamp === renaming ? { ...r, name: finalName } : r
      );
      renaming = null;
      newName = "";
    }
  }

  // Start editing duration of a recording
  function startEditDuration(timestamp: string): void {
    const recording = recordings.find((r) => r.timestamp === timestamp);
    if (recording) {
      newDuration = recording.duration || 10;
      editingDuration = timestamp;
    }
  }

  // Complete editing duration
  function completeEditDuration(): void {
    if (editingDuration) {
      // Ensure duration is at least 1 second
      const validDuration = Math.max(1, newDuration);

      socket.emit("update_recording_duration", {
        timestamp: editingDuration,
        duration: validDuration,
      });

      recordings = recordings.map((r) =>
        r.timestamp === editingDuration ? { ...r, duration: validDuration } : r
      );
      editingDuration = null;
      newDuration = 0;
    }
  }

  // Format duration for display
  function formatDuration(seconds: number): string {
    if (!seconds) return "10s"; // Default
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m${remainingSeconds > 0 ? ` ${remainingSeconds}s` : ""}`;
  }

  // Format time display for progress
  function formatTimeDisplay(
    currentSeconds: number,
    totalSeconds: number
  ): string {
    const formatTime = (time: number): string => {
      const minutes = Math.floor(time / 60);
      const seconds = Math.floor(time % 60);
      return `${minutes > 0 ? `${minutes}:` : ""}${seconds.toString().padStart(minutes > 0 ? 2 : 1, "0")}`;
    };

    return `${formatTime(currentSeconds)} / ${formatTime(totalSeconds)}`;
  }

  // Handle progress bar hover
  function handleProgressHover(
    event: MouseEvent,
    timestamp: string,
    duration: number
  ): void {
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    const position = (event.clientX - rect.left) / rect.width;
    const hoverTimePercent = Math.max(0, Math.min(100, position * 100));
    hoverProgress[timestamp] = hoverTimePercent;
  }

  // Clear progress hover
  function clearProgressHover(timestamp: string): void {
    hoverProgress[timestamp] = null;
  }

  // Check if recording exists
  function hasRecording(timestamp: string): boolean {
    return recordings.some((r) => r.timestamp === timestamp);
  }

  // Calculate time markers for progress bar
  function getTimeMarkers(duration: number): number[] {
    // For durations less than 10 seconds, show markers at each second
    if (duration <= 10) {
      return Array.from(
        { length: duration },
        (_, i) => ((i + 1) * 100) / duration
      );
    }

    // For longer durations, show fewer markers
    const interval = Math.ceil(duration / 5);
    return Array.from(
      { length: Math.floor(duration / interval) },
      (_, i) => ((i + 1) * interval * 100) / duration
    );
  }

  onMount(() => {
    // Listen for playback events
    socket.on("start_playback", handleStartPlayback);
    socket.on("stop_playback", handleStopPlayback);
    socket.on("start_recording", handleStartRecording);
    socket.on("stop_recording", handleStopRecording);
    socket.on("playback_error", handlePlaybackError);

    return () => {
      // Clean up event listeners
      socket.off("start_playback", handleStartPlayback);
      socket.off("stop_playback", handleStopPlayback);
      socket.off("start_recording", handleStartRecording);
      socket.off("stop_recording", handleStopRecording);
      socket.off("playback_error", handlePlaybackError);

      // Clear all progress tracking intervals
      Object.keys(progressIntervals).forEach(clearProgressTracking);
    };
  });
</script>

{#if lastSensorUpdateTime === 0 }
  <Skeleton class="w-fulll h-48"/>
{:else}
  <Card.Root class="w-full h-full {className}">
    <Card.Header class="pb-2">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <Mic class="w-5 h-5 text-purple-500" />
          <Card.Title>Joystick Macros</Card.Title>
        </div>
  
        {#if recordings.length > 0}
          <span class="text-xs text-gray-500"
            >{recordings.length}
            {recordings.length === 1 ? "recording" : "recordings"}</span
          >
        {/if}
      </div>
      <Card.Description>Saved joystick movement patterns</Card.Description>
    </Card.Header>
  
    <Card.Content class="overflow-hidden h-full">
      {#if recordings.length === 0}
        <div class="flex flex-col items-center justify-center py-8 text-gray-400">
          <Clock class="w-12 h-12 mb-3 opacity-25" />
          <p class="text-center text-sm">No recordings yet</p>
          <p class="text-center text-xs mt-1">
            Use the controller to record joystick movements
          </p>
        </div>
      {:else}
        <div class="flex flex-col gap-2">
          {#each recordings as recording (recording.timestamp)}
            <div
              class="relative group border border-gray-100 hover:border-gray-200 rounded-md p-3 bg-white transition-all"
              transition:slide={{ duration: 200, easing: quintOut }}
              class:border-purple-200={recording.isPlaying}
              class:bg-purple-50={recording.isPlaying}
            >
              {#if showConfirmDelete === recording.timestamp}
                <div
                  class="absolute inset-0 bg-gray-800/75 backdrop-blur-sm rounded-md flex items-center justify-center z-10"
                  transition:fade={{ duration: 150 }}
                >
                  <div class="bg-white p-3 rounded-md shadow-lg">
                    <p class="text-sm mb-2">Delete this recording?</p>
                    <div class="flex gap-2 justify-end">
                      <Button
                        variant="outline"
                        size="sm"
                        class="h-8"
                        onclick={() => (showConfirmDelete = null)}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        class="h-8"
                        onclick={() => deleteRecording(recording.timestamp)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>
                </div>
              {/if}
  
              <div class="flex flex-col gap-2">
                <!-- First row: name and controls -->
                <div class="flex items-center justify-between">
                  <div class="flex-grow min-w-0">
                    {#if renaming === recording.timestamp}
                      <div
                        class="flex items-center gap-2"
                        transition:fade={{ duration: 150 }}
                      >
                        <input
                          type="text"
                          class="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-1 focus:ring-purple-400"
                          placeholder="Enter recording name"
                          bind:value={newName}
                          onkeydown={(e) => {
                            if (e.key === "Enter") {
                              completeRename();
                            } else if (e.key === "Escape") {
                              renaming = null;
                              newName = "";
                            }
                          }}
                          autofocus
                        />
                        <Button
                          variant="outline"
                          size="sm"
                          class="h-7 px-2"
                          onclick={completeRename}
                        >
                          Save
                        </Button>
                      </div>
                    {:else}
                      <div class="flex flex-col">
                        <div class="flex items-center gap-2">
                          {#if recording.isPlaying}
                            <span
                              class="w-2 h-2 rounded-full bg-purple-500 animate-pulse"
                            ></span>
                          {/if}
                          <span class="font-medium text-sm truncate">
                            {recording.name ||
                              formatTimestamp(recording.timestamp)}
                          </span>
                        </div>
                        <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span
                            class="text-xs text-gray-500 flex items-center gap-0.5"
                          >
                            <Calendar class="w-3 h-3" />
                            {getRelativeTime(recording.timestamp)}
                          </span>
  
                          {#if editingDuration === recording.timestamp}
                            <div
                              class="flex items-center gap-1"
                              transition:fade={{ duration: 150 }}
                            >
                              <input
                                type="number"
                                class="w-16 text-xs border border-gray-200 rounded-sm px-1 py-0.5"
                                min="1"
                                bind:value={newDuration}
                                onkeydown={(e) => {
                                  if (e.key === "Enter") {
                                    completeEditDuration();
                                  } else if (e.key === "Escape") {
                                    editingDuration = null;
                                  }
                                }}
                              />
                              <span class="text-xs">sec</span>
                              <Button
                                variant="ghost"
                                size="sm"
                                class="h-5 w-5 p-0"
                                onclick={completeEditDuration}
                                title="Save duration"
                              >
                                <Check class="h-3 w-3" />
                              </Button>
                            </div>
                          {:else}
                            <button
                              class="text-xs text-gray-500 hover:text-purple-500 flex items-center gap-1"
                              onclick={() =>
                                !recording.isPlaying &&
                                startEditDuration(recording.timestamp)}
                              disabled={recording.isPlaying}
                            >
                              <Clock class="h-3 w-3" />
                              <span>{formatDuration(recording.duration)}</span>
                            </button>
                          {/if}
                        </div>
                      </div>
                    {/if}
                  </div>
  
                  <div class="flex items-center gap-1 shrink-0">
                    {#if !recording.isPlaying}
                      <Button
                        size="icon"
                        variant="ghost"
                        class="h-7 w-7"
                        onclick={() => playRecording(recording.timestamp)}
                        title="Play recording"
                      >
                        <Play class="h-3.5 w-3.5" />
                      </Button>
                    {:else}
                      <Button
                        size="icon"
                        variant="ghost"
                        class="h-7 w-7 text-purple-500"
                        onclick={() => stopPlayback(recording.timestamp)}
                        title="Stop playback"
                      >
                        <Pause class="h-3.5 w-3.5" />
                      </Button>
                    {/if}
  
                    {#if !recording.isPlaying}
                      <div
                        class="opacity-0 group-hover:opacity-100 transition-opacity flex"
                      >
                        <Button
                          size="icon"
                          variant="ghost"
                          class="h-7 w-7"
                          onclick={() => startRename(recording.timestamp)}
                          title="Rename recording"
                        >
                          <Edit class="h-3 w-3" />
                        </Button>
  
                        <Button
                          size="icon"
                          variant="ghost"
                          class="h-7 w-7 hover:text-red-500"
                          onclick={() =>
                            (showConfirmDelete = recording.timestamp)}
                          title="Delete recording"
                        >
                          <Trash2 class="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    {/if}
                  </div>
                </div>
  
                <!-- Progress bar -->
                <div
                  class="w-full mt-1 {recording.isPlaying
                    ? ''
                    : 'opacity-50 group-hover:opacity-100'} transition-opacity"
                  onmousemove={(e) =>
                    handleProgressHover(
                      e,
                      recording.timestamp,
                      recording.duration || 10
                    )}
                  onmouseleave={() => clearProgressHover(recording.timestamp)}
                >
                  <div
                    class="h-2 bg-gray-100 rounded-full overflow-hidden relative"
                  >
                    <!-- Time markers -->
                    {#each getTimeMarkers(recording.duration || 10) as marker}
                      <div
                        class="absolute top-0 bottom-0 w-px bg-gray-300/50"
                        style="left: {marker}%;"
                      ></div>
                    {/each}
  
                    <!-- Hover indicator -->
                    {#if hoverProgress[recording.timestamp] !== null && hoverProgress[recording.timestamp] !== undefined}
                      <div
                        class="absolute top-0 h-full w-px bg-gray-500 z-10"
                        style="left: {hoverProgress[recording.timestamp]}%;"
                        transition:fade={{ duration: 100 }}
                      ></div>
                    {/if}
  
                    <!-- Progress bar -->
                    <div
                      class="h-full bg-purple-500 transition-all {recording.isPlaying
                        ? 'duration-300 ease-linear'
                        : ''} rounded-full"
                      style="width: {recording.progress || 0}%"
                    ></div>
                  </div>
  
                  <!-- Time display -->
                  <div class="flex justify-between mt-1">
                    {#if hoverProgress[recording.timestamp] !== null && hoverProgress[recording.timestamp] !== undefined && !recording.isPlaying}
                      <span
                        class="text-[10px] text-purple-500 font-medium"
                        transition:fade={{ duration: 100 }}
                      >
                        {Math.floor(
                          ((hoverProgress[recording.timestamp] || 0) / 100) *
                            (recording.duration || 10)
                        )}s
                      </span>
                    {:else if recording.isPlaying}
                      <span class="text-[10px] text-purple-700">
                        {formatTimeDisplay(
                          Math.floor(
                            ((recording.progress || 0) / 100) *
                              (recording.duration || 10)
                          ),
                          recording.duration || 10
                        )}
                      </span>
                    {:else}
                      <span class="text-[10px] text-gray-400">
                        {formatTimeDisplay(0, recording.duration || 10)}
                      </span>
                    {/if}
  
                    {#if recording.isPlaying}
                      <span
                        class="text-[10px] flex items-center gap-0.5 text-purple-500"
                      >
                        <Loader2 class="w-2 h-2 animate-spin" />
                        Playing
                      </span>
                    {/if}
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </Card.Content>
  
    <!-- Recording controls -->
    <div class="p-4 border-t border-gray-200 bg-gray-50 grow">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-gray-700">Recording Controls</h3>
  
        {#if isRecording}
          <Button
            variant="destructive"
            size="sm"
            class="h-8"
            onclick={stopRecording}
            title="Stop recording"
          >
            <StopCircle class="h-4 w-4 mr-1" />
            Stop Recording
          </Button>
        {:else}
          <Button
            variant="outline"
            size="sm"
            class="h-8"
            onclick={startRecording}
            title="Start recording"
          >
            <Mic class="h-4 w-4 mr-1" />
            Start Recording
          </Button>
        {/if}
      </div>
  
      <!-- Recording status -->
      <div class="mt-2 text-xs text-gray-500">
        {#if isRecording}
          <p>Recording in progress...</p>
          <p>Duration: {formatDuration(recordingDuration)}</p>
        {:else}
          <p>No recording in progress</p>
        {/if}
      </div>
    </div>
  </Card.Root>
{/if}