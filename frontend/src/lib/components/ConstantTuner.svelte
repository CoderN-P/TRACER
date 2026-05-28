<script lang="ts">
  import { io as socket } from "$lib/api/socket";
  import * as Card from "$lib/components/ui/card";
  import { SlidersHorizontal, RotateCcw } from "lucide-svelte";

  const DEFAULT_CONSTANTS = {
    MEASURED_WHEEL_BASE: 0.278,
    WHEEL_BASE_CORRECTION: 1.0,
    P_THETA: 0.1,
    P_GYRO_BIAS: 1.0e-4,
    P_THETA_BIAS: 0.0,
    P_POSITION: 0.01,
    Q_THETA: 1.0e-4,
    Q_BIAS: 1.0e-6,
    Q_X: 0.01,
    Q_Y: 0.01,
    R_THETA_ENCODER: 0.01,
    R_THETA_MAGNETOMETER: 0.1,
    R_POSITION: 0.05,
    K_REPULSIVE_SOFT: 40,
    K_REPULSIVE_HARD: 100,
    K_ATTRACTIVE: 15,
    REPULSIVE_THRESHOLD: 100,
    REPULSIVE_WEIGHT: 0.5,
    LOOKAHEAD_DISTANCE: 0.3,
    COMPLETION_THRESHOLD: 0.03,
    END_LOOKAHEAD_MULTIPLIER: 1.5,
    BETA: 2.0,
    ZETA: 0.7,
    K_OMEGA: 0.8,
    K_V: 5.0,
    K_D: 4.0,
  } as const;

  type ConstantKey = keyof typeof DEFAULT_CONSTANTS;

  type ConstantField = {
    key: ConstantKey;
    label: string;
    step?: string;
    min?: number;
  };

  type ConstantSection = {
    title: string;
    subtitle: string;
    fields: ConstantField[];
  };

  const CONSTANT_SECTIONS: ConstantSection[] = [
    {
      title: "EKF (State Estimation)",
      subtitle:
        "Kalman covariance (P), process noise (Q), and measurement noise (R)",
      fields: [
        { key: "P_THETA", label: "P_THETA", step: "0.0001", min: 0 },
        { key: "P_GYRO_BIAS", label: "P_GYRO_BIAS", step: "1e-6", min: 0 },
        { key: "P_THETA_BIAS", label: "P_THETA_BIAS", step: "1e-6", min: 0 },
        { key: "P_POSITION", label: "P_POSITION", step: "0.001", min: 0 },
        { key: "Q_THETA", label: "Q_THETA", step: "1e-6", min: 0 },
        { key: "Q_BIAS", label: "Q_BIAS", step: "1e-6", min: 0 },
        { key: "Q_X", label: "Q_X", step: "0.0001", min: 0 },
        { key: "Q_Y", label: "Q_Y", step: "0.0001", min: 0 },
        {
          key: "R_THETA_ENCODER",
          label: "R_THETA_ENCODER",
          step: "0.0001",
          min: 0,
        },
        {
          key: "R_THETA_MAGNETOMETER",
          label: "R_THETA_MAGNETOMETER",
          step: "0.0001",
          min: 0,
        },
        { key: "R_POSITION", label: "R_POSITION", step: "0.001", min: 0 },
      ],
    },
    {
      title: "Physical Dimensions",
      subtitle: "Wheelbase and calibration corrections.",
      fields: [
        {
          key: "MEASURED_WHEEL_BASE",
          label: "MEASURED_WHEEL_BASE",
          step: "0.001",
          min: 0,
        },
        {
          key: "WHEEL_BASE_CORRECTION",
          label: "WHEEL_BASE_CORRECTION",
          step: "0.001",
          min: 0,
        },
      ],
    },
    {
      title: "Attractive Potential Field",
      subtitle: "Obstacle avoidance and path attraction tuning.",
      fields: [
        { key: "K_REPULSIVE_SOFT", label: "K_REPULSIVE_SOFT", min: 0 },
        { key: "K_REPULSIVE_HARD", label: "K_REPULSIVE_HARD", min: 0 },
        { key: "K_ATTRACTIVE", label: "K_ATTRACTIVE", min: 0 },
        { key: "REPULSIVE_THRESHOLD", label: "REPULSIVE_THRESHOLD", min: 0 },
        {
          key: "REPULSIVE_WEIGHT",
          label: "REPULSIVE_WEIGHT",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Pure Pursuit",
      subtitle: "Path following geometry and completion limits.",
      fields: [
        {
          key: "LOOKAHEAD_DISTANCE",
          label: "LOOKAHEAD_DISTANCE",
          step: "0.01",
          min: 0,
        },
        {
          key: "COMPLETION_THRESHOLD",
          label: "COMPLETION_THRESHOLD",
          step: "0.01",
          min: 0,
        },
        {
          key: "END_LOOKAHEAD_MULTIPLIER",
          label: "END_LOOKAHEAD_MULTIPLIER",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Ramsete",
      subtitle: "Trajectory tracking correction gains.",
      fields: [
        { key: "BETA", label: "BETA", step: "0.01", min: 0 },
        { key: "ZETA", label: "ZETA", step: "0.01", min: 0 },
      ],
    },
    {
      title: "Go to Goal",
      subtitle: "Heading and velocity control while targeting a point.",
      fields: [
        { key: "K_OMEGA", label: "K_OMEGA", step: "0.01", min: 0 },
        { key: "K_V", label: "K_V", step: "0.01", min: 0 },
        { key: "K_D", label: "K_D", step: "0.01", min: 0 },
      ],
    },
  ];

  let { class: className = "" } = $props();

  let constants = $state<Record<ConstantKey, number>>({ ...DEFAULT_CONSTANTS });
  let draftValues = $state<Record<ConstantKey, string>>(
    Object.fromEntries(
      Object.entries(DEFAULT_CONSTANTS).map(([key, value]) => [
        key,
        String(value),
      ]),
    ) as Record<ConstantKey, string>,
  );

  function emitConstants() {
    socket.emit("update_constants", { ...constants });
  }

  function syncConstant(key: ConstantKey, rawValue: string) {
    draftValues[key] = rawValue;

    if (rawValue.trim() === "") {
      return;
    }

    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) {
      return;
    }

    constants[key] = parsed;
    emitConstants();
  }

  function resetConstant(key: ConstantKey) {
    const defaultValue = DEFAULT_CONSTANTS[key];
    constants[key] = defaultValue;
    draftValues[key] = String(defaultValue);
    emitConstants();
  }

  function resetAllConstants() {
    constants = { ...DEFAULT_CONSTANTS };
    draftValues = Object.fromEntries(
      Object.entries(DEFAULT_CONSTANTS).map(([key, value]) => [
        key,
        String(value),
      ]),
    ) as Record<ConstantKey, string>;
    emitConstants();
  }

  function normalizeField(key: ConstantKey) {
    if (draftValues[key].trim() === "") {
      draftValues[key] = String(constants[key]);
    }
  }
</script>

<Card.Root class="w-full border border-gray-100 bg-white {className}">
  <Card.Header class="space-y-2">
    <div
      class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
    >
      <div class="space-y-1">
        <Card.Title class="flex items-center gap-2 text-lg">
          <SlidersHorizontal class="h-5 w-5" />
          Motion Constants
        </Card.Title>
        <Card.Description>
          Adjust these tuning values live. Every valid change emits the
          update_constants socket event.
        </Card.Description>
      </div>

      <button
        type="button"
        onclick={resetAllConstants}
        class="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100 active:bg-gray-200"
      >
        <RotateCcw class="h-4 w-4" />
        Reset all
      </button>
    </div>
  </Card.Header>

  <Card.Content class="space-y-4">
    <div class="grid gap-4 xl:grid-cols-2">
      {#each CONSTANT_SECTIONS as section}
        <section class="rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div class="mb-4 space-y-1">
            <h3 class="text-sm font-semibold text-gray-900">{section.title}</h3>
            <p class="text-xs text-gray-500">{section.subtitle}</p>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            {#each section.fields as field}
              <label class="space-y-1">
                <div
                  class="flex items-center justify-between gap-2 text-xs font-medium text-gray-700"
                >
                  <span class="font-mono">{field.label}</span>
                  <button
                    type="button"
                    class="text-[11px] font-semibold text-gray-500 hover:text-gray-900"
                    onclick={() => resetConstant(field.key)}
                    title={`Reset ${field.label} to its default value`}
                  >
                    default
                  </button>
                </div>

                <input
                  type="number"
                  step={field.step ?? "any"}
                  min={field.min}
                  value={draftValues[field.key]}
                  oninput={(event) =>
                    syncConstant(
                      field.key,
                      (event.currentTarget as HTMLInputElement).value,
                    )}
                  onblur={() => normalizeField(field.key)}
                  class="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm text-gray-900 outline-none transition-colors placeholder:text-gray-400 focus:border-gray-500 focus:ring-2 focus:ring-gray-200"
                />
              </label>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  </Card.Content>
</Card.Root>
