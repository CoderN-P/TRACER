<script lang="ts">
  import { browser } from "$app/environment";
  import { io as socket } from "$lib/api/socket";
  import * as Card from "$lib/components/ui/card";
  import DEFAULT_CONSTANTS from "$calibration/constants/constants.json";
  import { onMount } from "svelte";
  import { SlidersHorizontal, RotateCcw, Save } from "lucide-svelte";

  const STORAGE_KEY = "tracer.constant-tuner.constants.v1";

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

  function createDraftValues(source: Record<ConstantKey, number>) {
    return Object.fromEntries(
      Object.entries(source).map(([key, value]) => [key, String(value)]),
    ) as Record<ConstantKey, string>;
  }

  function loadStoredConstants(): Partial<Record<ConstantKey, number>> {
    if (!browser) {
      return {};
    }

    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return {};
      }

      const parsed = JSON.parse(raw) as Record<string, unknown>;
      return Object.fromEntries(
        Object.entries(parsed).filter(
          ([key, value]) =>
            key in DEFAULT_CONSTANTS && typeof value === "number",
        ),
      ) as Partial<Record<ConstantKey, number>>;
    } catch {
      return {};
    }
  }

  function createInitialConstants() {
    return {
      ...DEFAULT_CONSTANTS,
      ...loadStoredConstants(),
    } satisfies Record<ConstantKey, number>;
  }

  function persistConstants(nextConstants: Record<ConstantKey, number>) {
    if (!browser) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextConstants));
  }

  function publishConstants(nextConstants: Record<ConstantKey, number>) {
    if (!browser) {
      return;
    }

    window.dispatchEvent(
      new CustomEvent("tracer:constants-updated", {
        detail: { ...nextConstants },
      }),
    );
  }

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
        {
          key: "STATE_HISTORY_SIZE",
          label: "STATE_HISTORY_SIZE",
          step: "1",
          min: 5,
        },
      ],
    },
    {
      title: "Physical Dimensions",
      subtitle: "Wheelbase and calibration corrections.",
      fields: [
        {
          key: "WHEEL_BASE_MAX",
          label: "WHEEL_BASE_MAX",
          step: "0.001",
          min: 0,
        },
        {
          key: "WHEEL_BASE_MAX",
          label: "WHEEL_BASE_MIN",
          step: "0.001",
          min: 0,
        },   
        {
          key: "WHEEL_DIAMETER",
          label: "WHEEL_DIAMETER",
          step: "0.0001",
          min: 0,
        },
        {
          key: "ROBOT_WIDTH",
          label: "ROBOT_WIDTH",
          step: "0.001",
          min: 0,
        },
        {
          key: "ROBOT_HEIGHT",
          label: "ROBOT_HEIGHT",
          step: "0.001",
          min: 0,
        },
      ],
    },
    {
      title: "Hardware & Motors",
      subtitle: "Motor and encoder hardware parameters.",
      fields: [
        { key: "MAX_RPM", label: "MAX_RPM", step: "1", min: 0 },
        {
          key: "REDUCTION_RATIO",
          label: "REDUCTION_RATIO",
          step: "0.1",
          min: 0,
        },
        { key: "ENCODER_PPR", label: "ENCODER_PPR", step: "1", min: 1 },
        {
          key: "MAX_ENCODER_MARGIN",
          label: "MAX_ENCODER_MARGIN",
          step: "0.01",
          min: 0,
        },
        {
          key: "LEFT_CORRECTION_POS",
          label: "LEFT_CORRECTION_POS",
          step: "0.001",
          min: 0,
        },
        {
          key: "RIGHT_CORRECTION_POS",
          label: "RIGHT_CORRECTION_POS",
          step: "0.001",
          min: 0,
        },
        {
          key: "LEFT_CORRECTION_NEG",
          label: "LEFT_CORRECTION_NEG",
          step: "0.001",
          min: 0,
        },
        {
          key: "RIGHT_CORRECTION_NEG",
          label: "RIGHT_CORRECTION_NEG",
          step: "0.001",
          min: 0,
        },
        {
          key: "MAX_LINEAR_VEL_POS",
          label: "MAX_LINEAR_VEL_POS",
          step: "0.001",
          min: 0,
        },
        {
          key: "MAX_LINEAR_VEL_NEG",
          label: "MAX_LINEAR_VEL_NEG",
          step: "0.001",
          min: 0,
        },
      ],
    },
    {
      title: "Obstacle Settings",
      subtitle: "Additional obstacle detection and avoidance tuning.",
      fields: [
        {
          key: "CHECK_OBSTACLE_FREQ",
          label: "CHECK_OBSTACLE_FREQ",
          step: "0.1",
          min: 0,
        },
        {
          key: "MIN_GAP_WIDTH",
          label: "MIN_GAP_WIDTH",
          step: "0.01",
          min: 0,
        },
        {
          key: "OBSTACLE_DETECTED_THRESHOLD",
          label: "OBSTACLE_DETECTED_THRESHOLD",
          step: "1",
          min: 0,
        },
        {
          key: "OBSTACLE_AVOID_THRESHOLD",
          label: "OBSTACLE_AVOID_THRESHOLD",
          step: "1",
          min: 0,
        },
        {
          key: "LIDAR_OFFSET",
          label: "LIDAR_OFFSET",
          step: "0.01",
          min: -100,
        },
        {
          key: "GAP_UPDATE_THRESHOLD",
          label: "GAP_UPDATE_THRESHOLD",
          step: "0.01",
          min: 0,
        },
        {
          key: "CLEAR_FRAMES_THRESHOLD",
          label: "CLEAR_FRAMES_THRESHOLD",
          step: "1",
          min: 0,
        },
        {
          key: "LIDAR_HEIGHT",
          label: "LIDAR_HEIGHT",
          step: "0.01",
          min: 0,
        },
        {
          key: "CLEARANCE_HEIGHT",
          label: "CLEARANCE_HEIGHT",
          step: "0.01",
          min: 0,
        },
        {
          key: "GRID_COLS",
          label: "GRID_COLS",
          step: "1",
          min: 1,
        },
        {
          key: "K_WIDTH",
          label: "K_WIDTH",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Dynamic Window",
      subtitle: "DWA sampling, acceleration, and scoring weights.",
      fields: [
        {
          key: "V_SAMPLES",
          label: "V_SAMPLES",
          step: "1",
          min: 1,
        },
        {
          key: "OMEGA_SAMPLES",
          label: "OMEGA_SAMPLES",
          step: "1",
          min: 1,
        },
        {
          key: "DWA_STEPS",
          label: "DWA_STEPS",
          step: "1",
          min: 1,
        },
        {
          key: "MAX_ALPHA",
          label: "MAX_ALPHA",
          step: "0.01",
          min: 0,
        },
        {
          key: "DWA_SIGMA",
          label: "DWA_SIGMA",
          step: "0.01",
          min: 0,
        },
        {
          key: "DWA_ALPHA",
          label: "DWA_ALPHA",
          step: "0.01",
          min: 0,
        },
        {
          key: "DWA_BETA",
          label: "DWA_BETA",
          step: "0.01",
          min: 0,
        },
        {
          key: "DWA_Y",
          label: "DWA_Y",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Controls",
      subtitle: "Manual control deadzones and input settings.",
      fields: [
        {
          key: "JOYSTICK_DEADZONE",
          label: "JOYSTICK_DEADZONE",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Sensors & Timing",
      subtitle: "Sensor scaling and main loop timing.",
      fields: [
        {
          key: "EMIT_SENSOR_FREQ",
          label: "EMIT_SENSOR_FREQ",
          step: "0.1",
          min: 0,
        },
        {
          key: "DWA_FREQ",
          label: "DWA_FREQ",
          step: "1",
          min: 1,
        },
        {
          key: "SENSOR_TIMEOUT",
          label: "SENSOR_TIMEOUT",
          step: "0.001",
          min: 0,
        },
        { key: "MAIN_LOOP_FREQ", label: "MAIN_LOOP_FREQ", step: "1", min: 1 },
        {
          key: "PATH_FOLLOWING_FREQ",
          label: "PATH_FOLLOWING_FREQ",
          step: "1",
          min: 1,
        },
        { key: "MANUAL_FREQ", label: "MANUAL_FREQ", step: "1", min: 1 },
        { key: "G", label: "G", step: "0.01", min: 0 },
        { key: "LSB_G", label: "LSB_G", step: "1e-6", min: 0 },
        { key: "LSB_uT", label: "LSB_uT", step: "1e-6", min: 0 },
        { key: "LSB_C", label: "LSB_C", step: "1e-6", min: 0 },
        { key: "TEMP_OFFSET", label: "TEMP_OFFSET", step: "0.1", min: -100 },
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
        { key: "K_CURVE", label: "K_CURVE", step: "0.01", min: 0 },
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
        {
          key: "MAX_LATERAL_ACCEL",
          label: "MAX_LATERAL_ACCEL",
          step: "0.01",
          min: 0,
        },
        {
          key: "MAX_LONG_ACCEL",
          label: "MAX_LONG_ACCEL",
          step: "0.01",
          min: 0,
        },
      ],
    },
    {
      title: "Trajectory",
      subtitle: "Spline and search parameters for path planning.",
      fields: [
        {
          key: "MAX_SEARCH_POINTS",
          label: "MAX_SEARCH_POINTS",
          step: "1",
          min: 1,
        },
        { key: "SPLINE_SAMPLES", label: "SPLINE_SAMPLES", step: "1", min: 1 },
        { key: "TRAJECTORY_DT", label: "TRAJECTORY_DT", step: "0.001", min: 0 },
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
  let activeSection = $state<number>(0);

  let constants = $state<Record<ConstantKey, number>>(createInitialConstants());
  let draftValues = $state<Record<ConstantKey, string>>(
    createDraftValues(constants),
  );

  onMount(() => {
    emitConstants();
  });

  function emitConstants(options: { save?: boolean } = {}) {
    const payload = options.save
      ? { ...constants, save: true }
      : { ...constants };
    socket.emit("update_constants", payload);
    persistConstants(constants);
    publishConstants(constants);
  }

  function saveConstants() {
    emitConstants({ save: true });
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
    draftValues = createDraftValues(DEFAULT_CONSTANTS);
    persistConstants(constants);
    emitConstants();
  }

  function normalizeField(key: ConstantKey) {
    if (draftValues[key].trim() === "") {
      draftValues[key] = String(constants[key]);
    }
  }
</script>

<Card.Root
  class="w-full h-full border border-gray-100 bg-white flex flex-col {className}"
>
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

      <div class="inline-flex items-center gap-2">
        <button
          type="button"
          onclick={saveConstants}
          class="inline-flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-emerald-700 transition-colors hover:bg-emerald-100 active:bg-emerald-200"
          title="Persist current constants"
        >
          <Save class="h-4 w-4" />
          Save
        </button>

        <button
          type="button"
          onclick={resetAllConstants}
          class="inline-flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-100 active:bg-gray-200"
        >
          <RotateCcw class="h-4 w-4" />
          Reset all
        </button>
      </div>
    </div>
  </Card.Header>

  <Card.Content class="min-h-0 flex-1 space-y-3 overflow-hidden">
    <div class="flex flex-wrap gap-2">
      {#each CONSTANT_SECTIONS as section, index}
        <button
          type="button"
          onclick={() => (activeSection = index)}
          class="rounded-full border px-3 py-1 text-xs font-semibold transition-colors {activeSection ===
          index
            ? 'border-gray-300 bg-gray-200 text-gray-900'
            : 'border-gray-200 bg-gray-50 text-gray-600 hover:bg-gray-100'}"
        >
          {section.title}
        </button>
      {/each}
    </div>

    {@const section = CONSTANT_SECTIONS[activeSection]}
    <section
      class="h-[calc(100%-2.5rem)] rounded-lg border border-gray-200 bg-gray-50 p-4 overflow-hidden"
    >
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
  </Card.Content>
</Card.Root>
