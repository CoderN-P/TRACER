<script lang="ts">
  import { browser } from "$app/environment";
  import { io as socket } from "$lib/api/socket";
  import * as Card from "$lib/components/ui/card";
  import DEFAULT_CONSTANTS from "../../../../calibration_files/constants/constants.json";
  import { onMount } from "svelte";
  import { SlidersHorizontal, RotateCcw, Save, Cpu } from "lucide-svelte";

  const STORAGE_KEY = "tracer.constant-tuner.constants.v1";
  const EMBEDDED_CONFIG_KEYS = [
    "WHEEL_BASE_MAX",
    "WHEEL_BASE_MIN",
    "P_LEFT",
    "P_RIGHT",
    "I_LEFT",
    "I_RIGHT",
    "D_LEFT",
    "D_RIGHT",
    "I_ZONE",
    "NOMINAL_WHEEL_BASE",
    "ALPHA",
    "USE_GYRO_CORRECTION",
    "USE_ADAPTIVE_WHEEL_BASE",
    "LEFT_CORRECTION_POS",
    "RIGHT_CORRECTION_POS",
    "LEFT_CORRECTION_NEG",
    "RIGHT_CORRECTION_NEG",
    "OMEGA_P",
    "MAX_LINEAR_VEL_POS",
    "MAX_LINEAR_VEL_NEG"
  ] as const satisfies readonly ConstantKey[];

  type ConstantKey = keyof typeof DEFAULT_CONSTANTS;
  type ConstantValue = (typeof DEFAULT_CONSTANTS)[ConstantKey];
  type EditableConstantKey = {
    [K in ConstantKey]: (typeof DEFAULT_CONSTANTS)[K] extends number | boolean
      ? K
      : never;
  }[ConstantKey];
  type EditableConstantValue = number | boolean;

  type ConstantField = {
    key: EditableConstantKey;
    label: string;
    step?: string;
    min?: number;
  };

  type ConstantSection = {
    title: string;
    subtitle: string;
    fields: ConstantField[];
  };

  function isEditableConstantValue(
    value: ConstantValue,
  ): value is EditableConstantValue {
    return typeof value === "number" || typeof value === "boolean";
  }

  function isEmbeddedConstant(key: EditableConstantKey) {
    return EMBEDDED_CONFIG_KEYS.includes(
      key as (typeof EMBEDDED_CONFIG_KEYS)[number],
    );
  }

  function createDraftValues(source: Record<ConstantKey, ConstantValue>) {
    return Object.fromEntries(
      Object.entries(source)
        .filter(([, value]) => isEditableConstantValue(value as ConstantValue))
        .map(([key, value]) => [key, String(value)]),
    ) as Record<EditableConstantKey, string>;
  }

  function loadStoredConstants(): Partial<Record<ConstantKey, ConstantValue>> {
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
            key in DEFAULT_CONSTANTS &&
            (typeof value === "number" || typeof value === "boolean"),
        ),
      ) as Partial<Record<ConstantKey, ConstantValue>>;
    } catch {
      return {};
    }
  }

  function createInitialConstants() {
    return {
      ...DEFAULT_CONSTANTS,
      ...loadStoredConstants(),
    } satisfies Record<ConstantKey, ConstantValue>;
  }

  function persistConstants(nextConstants: Record<ConstantKey, ConstantValue>) {
    if (!browser) {
      return;
    }

    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextConstants));
  }

  function publishConstants(nextConstants: Record<ConstantKey, ConstantValue>) {
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
          key: "NOMINAL_WHEEL_BASE",
          label: "NOMINAL_WHEEL_BASE",
          step: "0.001",
          min: 0,
        },
        {
          key: "WHEEL_BASE_MAX",
          label: "WHEEL_BASE_MAX",
          step: "0.001",
          min: 0,
        },
        {
          key: "WHEEL_BASE_MIN",
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
        {
          key: "ALPHA",
          label: "ALPHA",
          step: "0.01",
          min: 0,
        },
        {
          key: "K_SCRUB",
          label: "K_SCRUB",
          step: "0.001",
          min: 0,
        },
      ],
    },
    {
      title: "Embedded PID",
      subtitle: "Motor PID gains sent through the embedded config channel.",
      fields: [
        { key: "P_LEFT", label: "P_LEFT", step: "0.01", min: 0 },
        { key: "I_LEFT", label: "I_LEFT", step: "0.01", min: 0 },
        { key: "D_LEFT", label: "D_LEFT", step: "0.01", min: 0 },
        { key: "P_RIGHT", label: "P_RIGHT", step: "0.01", min: 0 },
        { key: "I_RIGHT", label: "I_RIGHT", step: "0.01", min: 0 },
        { key: "D_RIGHT", label: "D_RIGHT", step: "0.01", min: 0 },
        { key: "I_ZONE", label: "I_ZONE", step: "0.001", min: 0 },
        { key: "OMEGA_P", label: "OMEGA_P", step: "0.001", min: 0 },      
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
          key: "LIDAR_FOV",
          label: "LIDAR_FOV",
          step: "0.1",
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
      subtitle: "Manual control, wheelbase mode, and correction toggles.",
      fields: [
        {
          key: "JOYSTICK_DEADZONE",
          label: "JOYSTICK_DEADZONE",
          step: "0.01",
          min: 0,
        },
        {
          key: "USE_ADAPTIVE_WHEEL_BASE",
          label: "USE_ADAPTIVE_WHEEL_BASE",
        },
        {
          key: "USE_GYRO_CORRECTION",
          label: "USE_GYRO_CORRECTION",
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
        { key: "USE_VIO", label: "USE_VIO" },
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
  ];

  let { class: className = "" } = $props();
  let activeSection = $state<number>(0);
  const initialConstants = createInitialConstants();

  let constants = $state<Record<ConstantKey, ConstantValue>>(initialConstants);
  let draftValues = $state<Record<EditableConstantKey, string>>(
    createDraftValues(initialConstants),
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

  function setConstantValue(
    key: EditableConstantKey,
    value: EditableConstantValue,
    options: { syncDraft?: boolean } = {},
  ) {
    constants = { ...constants, [key]: value };
    if (options.syncDraft ?? true) {
      draftValues[key] = String(value);
    }
    emitConstants();
  }

  function syncConstant(key: EditableConstantKey, rawValue: string) {
    draftValues[key] = rawValue;

    if (rawValue.trim() === "") {
      return;
    }

    const parsed = Number(rawValue);
    if (!Number.isFinite(parsed)) {
      return;
    }

    setConstantValue(key, parsed, { syncDraft: false });
  }

  function syncBooleanConstant(key: EditableConstantKey, checked: boolean) {
    setConstantValue(key, checked);
  }

  function resetConstant(key: EditableConstantKey) {
    const defaultValue = DEFAULT_CONSTANTS[key];
    if (isEditableConstantValue(defaultValue)) {
      setConstantValue(key, defaultValue);
    }
  }

  function resetAllConstants() {
    constants = { ...DEFAULT_CONSTANTS };
    draftValues = createDraftValues(DEFAULT_CONSTANTS);
    persistConstants(constants);
    emitConstants();
  }

  function normalizeField(key: EditableConstantKey) {
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
          update_constants socket event. Embedded constants are marked.
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
          <div class="space-y-1">
            <div
              class="flex items-center justify-between gap-2 text-xs font-medium text-gray-700"
            >
              <div class="flex min-w-0 items-center gap-1.5">
                <span class="truncate font-mono">{field.label}</span>
                {#if isEmbeddedConstant(field.key)}
                  <span
                    class="inline-flex shrink-0 items-center gap-1 rounded border border-amber-200 bg-amber-50 px-1.5 py-px text-[9px] font-bold uppercase leading-4 text-amber-700"
                    title="Also sent to the embedded controller config"
                  >
                    <Cpu class="h-2.5 w-2.5" />
                    emb
                  </span>
                {/if}
              </div>
              <button
                type="button"
                class="shrink-0 text-[11px] font-semibold text-gray-500 hover:text-gray-900"
                onclick={() => resetConstant(field.key)}
                title={`Reset ${field.label} to its default value`}
              >
                default
              </button>
            </div>

            {#if typeof constants[field.key] === "boolean"}
              <button
                type="button"
                role="switch"
                aria-checked={Boolean(constants[field.key])}
                onclick={() =>
                  syncBooleanConstant(field.key, constants[field.key] !== true)}
                class="flex h-10 w-full items-center justify-between rounded-md border px-3 text-sm font-semibold transition-colors {constants[
                  field.key
                ] === true
                  ? 'border-emerald-200 bg-emerald-50 text-emerald-800 hover:bg-emerald-100'
                  : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'}"
              >
                <span class="font-mono">
                  {constants[field.key] === true ? "true" : "false"}
                </span>
                <span
                  class="relative h-5 w-9 rounded-full transition-colors {constants[
                    field.key
                  ] === true
                    ? 'bg-emerald-500'
                    : 'bg-gray-300'}"
                >
                  <span
                    class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform {constants[
                      field.key
                    ] === true
                      ? ''
                      : '-translate-x-4'}"
                  ></span>
                </span>
              </button>
            {:else}
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
            {/if}
          </div>
        {/each}
      </div>
    </section>
  </Card.Content>
</Card.Root>
