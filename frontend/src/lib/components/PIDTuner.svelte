<script lang="ts">
  import { io as socket } from "$lib/api/socket";
  import * as Card from "$lib/components/ui/card";
  import { SlidersHorizontal, RotateCcw, Send } from "lucide-svelte";

  const DEFAULT_PID = {
    kp_left: 1.0,
    ki_left: 0.0,
    kd_left: 0.25,
    kp_right: 1.0,
    ki_right: 0.5,
    kd_right: 0.25,
  } as const;

  type PidKey = keyof typeof DEFAULT_PID;

  const PID_FIELDS: {
    key: PidKey;
    label: string;
    step: string;
    min?: number;
  }[] = [
    { key: "kp_left", label: "KP LEFT", step: "0.01", min: 0 },
    { key: "ki_left", label: "KI LEFT", step: "0.01", min: 0 },
    { key: "kd_left", label: "KD LEFT", step: "0.01", min: 0 },
    { key: "kp_right", label: "KP RIGHT", step: "0.01", min: 0 },
    { key: "ki_right", label: "KI RIGHT", step: "0.01", min: 0 },
    { key: "kd_right", label: "KD RIGHT", step: "0.01", min: 0 },
  ];

  let { class: className = "" } = $props();

  let pidValues = $state<Record<PidKey, number>>({ ...DEFAULT_PID });
  let draftValues = $state<Record<PidKey, string>>(
    Object.fromEntries(
      Object.entries(DEFAULT_PID).map(([key, value]) => [key, String(value)]),
    ) as Record<PidKey, string>,
  );

  function emitPid() {
    socket.emit("update_pid", { ...pidValues });
  }

  function updateField(key: PidKey, rawValue: string) {
    draftValues[key] = rawValue;

    if (rawValue.trim() === "") return;

    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) return;

    pidValues[key] = parsed;
  }

  function normalizeField(key: PidKey) {
    if (draftValues[key].trim() === "") {
      draftValues[key] = String(pidValues[key]);
    }
  }

  function resetField(key: PidKey) {
    const value = DEFAULT_PID[key];
    pidValues[key] = value;
    draftValues[key] = String(value);
  }

  function resetAll() {
    pidValues = { ...DEFAULT_PID };
    draftValues = Object.fromEntries(
      Object.entries(DEFAULT_PID).map(([key, value]) => [key, String(value)]),
    ) as Record<PidKey, string>;
  }
</script>

<Card.Root
  class="w-full h-full border border-gray-100 bg-white flex flex-col {className}"
>
  <Card.Header class="space-y-2">
    <div class="flex items-start justify-between gap-3">
      <div class="space-y-1">
        <Card.Title class="flex items-center gap-2 text-lg">
          <SlidersHorizontal class="h-5 w-5" />
          PID Tuner
        </Card.Title>
        <Card.Description>
          Tune left/right PID gains and emit the upate_pid event.
        </Card.Description>
      </div>

      <button
        type="button"
        onclick={resetAll}
        class="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100 active:bg-gray-200"
      >
        <RotateCcw class="h-4 w-4" />
        Reset
      </button>
    </div>
  </Card.Header>

  <Card.Content class="min-h-0 flex flex-1 flex-col overflow-hidden">
    <div class="min-h-0 flex-1 overflow-y-auto pr-1">
      <div class="grid gap-3 sm:grid-cols-2">
        {#each PID_FIELDS as field}
          <label class="space-y-1">
            <div
              class="flex items-center justify-between gap-2 text-xs font-medium text-gray-700"
            >
              <span class="font-mono">{field.label}</span>
              <button
                type="button"
                class="text-[11px] font-semibold text-gray-500 hover:text-gray-900"
                onclick={() => resetField(field.key)}
                title={`Reset ${field.label} to default`}
              >
                default
              </button>
            </div>

            <input
              type="number"
              step={field.step}
              min={field.min}
              value={draftValues[field.key]}
              oninput={(event) =>
                updateField(
                  field.key,
                  (event.currentTarget as HTMLInputElement).value,
                )}
              onblur={() => normalizeField(field.key)}
              class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-gray-500 focus:ring-2 focus:ring-gray-200"
            />
          </label>
        {/each}
      </div>
    </div>

    <div class="shrink-0 pt-3">
      <div class="flex justify-end">
        <button
          type="button"
          onclick={emitPid}
          class="inline-flex max-w-full items-center gap-2 rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition-colors hover:bg-blue-100 active:bg-blue-200"
        >
          <Send class="h-4 w-4" />
          Send PID Gains
        </button>
      </div>
    </div>
  </Card.Content>
</Card.Root>
