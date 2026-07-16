<script lang="ts">
  import { io as socket } from "$lib/api/socket";
  import { onMount } from "svelte";
  import {
    type Command,
    type DistanceEntry,
    DistanceEntrySchema,
    type GestureData,
    GestureDataSchema,
    type Joystick,
    JoystickSchema,
    type LogEntry,
    Mode,
    type SensorData,
    SensorDataSchema,
    type RobotState,
    RobotStateSchema,
  } from "$lib/types";
  import PathDrawer, {
    type MapUpdatePayload,
    type RunPathPayload,
  } from "$lib/components/PathDrawer.svelte";
  import Status from "$lib/components/Status.svelte";
  import Uptime from "$lib/components/Uptime.svelte";
  import Logs from "$lib/components/Logs.svelte";
  import ControlPad from "$lib/components/ControlPad.svelte";
  import JoystickStatus from "$lib/components/JoystickStatus.svelte";
  import UltrasonicGraph from "$lib/components/UltrasonicGraph.svelte";
  import SensorRate from "$lib/components/SensorRate.svelte";
  import LoopTimeDisplay from "$lib/components/LoopTimeDisplay.svelte";
  import KeyboardHandler from "$lib/components/KeyboardHandler.svelte";
  import TemperatureDisplay from "$lib/components/TemperatureDisplay.svelte";
  import BatteryPercentage from "$lib/components/BatteryPercentage.svelte";
  import ObstructionStatus, {
    type LidarPointCloud,
  } from "$lib/components/ObstructionStatus.svelte";
  import CommandList from "$lib/components/CommandList.svelte";
  import Recordings from "$lib/components/Recordings.svelte";
  import GestureController from "$lib/components/GestureController.svelte";
  import RobotControls from "$lib/components/RobotControls.svelte";
  import GyroMagDebug from "$lib/components/GyroMagDebug.svelte";
  import VelocityDebug from "$lib/components/VelocityDebug.svelte";
  import ConstantTuner from "$lib/components/ConstantTuner.svelte";
  import VelocityCommandWidget from "$lib/components/VelocityCommandWidget.svelte";
  import {
    Activity,
    Bot,
    Gauge,
    Route,
    Settings2,
    SlidersHorizontal,
  } from "lucide-svelte";

  type DashboardPage =
    | "overview"
    | "navigation"
    | "diagnostics"
    | "operations"
    | "settings"
    | "pid";

  const PAGE_CONFIG: {
    id: DashboardPage;
    label: string;
    short: string;
    icon: typeof Gauge;
  }[] = [
    { id: "overview", label: "Overview", short: "OVR", icon: Gauge },
    { id: "navigation", label: "Navigation", short: "NAV", icon: Route },
    {
      id: "diagnostics",
      label: "Diagnostics",
      short: "DBG",
      icon: Activity,
    },
    { id: "operations", label: "Operations", short: "OPS", icon: Bot },
    {
      id: "settings",
      label: "Settings",
      short: "SET",
      icon: Settings2,
    },
    {
      id: "pid",
      label: "PID",
      short: "PID",
      icon: SlidersHorizontal,
    },
  ];

  let sensorData = $state<SensorData | null>(null);
  let robotState = $state<RobotState | null>(null);
  let gestureData = $state<GestureData | null>(null);
  let previousSensorData = $state<SensorData | null>(null);
  let rayPoints = $state<(number | null)[][] | null>(null);
  let mode = $state<Mode>(Mode.MANUAL);
  let localizationMode = $state<string | null>(null);
  let logs = $state<LogEntry[]>([]);
  let joystickInput = $state<Joystick>({
    left_y: 0,
    right_x: 0,
  });
  let uiJoystick = $state<Joystick>({
    left_y: 0,
    right_x: 0,
  });
  let lastSensorUpdate = $state<number>(0);
  let velocityProfileT = $state<number | null>(null);
  let velocityCommand = $state<unknown | null>(null);
  let packetCount = $state<number>(0);
  let sensorRate = $state<number>(-1);
  let maxLoopTime = $state<number | null>(null);
  let lastRateUpdate = $state<number>(0);
  let distanceHistory = $state<DistanceEntry[]>([]);
  let input = $state<string>("");
  let inputFocus = $state<boolean>(false);
  let loadingAICommands = $state<boolean>(false);
  let aiCommands = $state<Command[]>([]);
  let activeCommand = $state<string | null>(null);
  let recordings = $state<
    {
      timestamp: string;
      isPlaying?: boolean;
      name?: string;
      duration: number;
    }[]
  >([]);
  let freehandPath = $state<{ x: number; y: number }[]>([]);
  let mapUpdate = $state<MapUpdatePayload>({ static: [], lidar: [] });
  let latestLidarScan = $state<LidarPointCloud | null>(null);
  let pathComplete = $state(false);
  let joystickSendInterval: ReturnType<typeof setInterval> | null = null;
  let wasJoystickActive = false;
  let activePage = $state<DashboardPage>("overview");

  function onSubmit(e: Event) {
    if (input.trim() === "") return;
    loadingAICommands = true;
    socket.emit("query", {
      query: input.trim(),
    });
    logs.push({
      timestamp: new Date().toISOString(),
      message: `Query sent: ${input}`,
      icon: "send",
    });
    input = "";
  }

  function normalizeMapLayer(layer: unknown): MapUpdatePayload["static"] {
    if (!Array.isArray(layer)) return [];

    return layer.flatMap((cell) => {
      if (!Array.isArray(cell) || cell.length < 3) return [];
      const [x, y, intensity] = cell;
      if (
        typeof x !== "number" ||
        typeof y !== "number" ||
        typeof intensity !== "number" ||
        !Number.isFinite(x) ||
        !Number.isFinite(y) ||
        !Number.isFinite(intensity)
      ) {
        return [];
      }

      return [
        [x, y, Math.max(0, Math.min(255, intensity))] as [
          number,
          number,
          number,
        ],
      ];
    });
  }

  function normalizeMapUpdate(data: unknown): MapUpdatePayload {
    const packet =
      data && typeof data === "object" ? (data as Record<string, unknown>) : {};

    return {
      static: normalizeMapLayer(packet.static),
      lidar: normalizeMapLayer(packet.lidar),
    };
  }

  function normalizeLatestLidarScan(data: unknown): LidarPointCloud | null {
    if (!data || typeof data !== "object") return null;

    const packet = data as Record<string, unknown>;
    const timestamp = packet.timestamp;
    const points = packet.points;

    if (typeof timestamp !== "number" || !Array.isArray(points)) return null;

    const normalizedPoints = points.flatMap((point) => {
      if (!point || typeof point !== "object") return [];
      const candidate = point as Record<string, unknown>;
      const { x, y, quality } = candidate;

      if (
        typeof x !== "number" ||
        typeof y !== "number" ||
        typeof quality !== "number" ||
        !Number.isFinite(x) ||
        !Number.isFinite(y) ||
        !Number.isFinite(quality)
      ) {
        return [];
      }

      return [
        {
          x,
          y,
          quality: Math.max(0, Math.min(63, quality)),
        },
      ];
    });

    return {
      timestamp,
      points: normalizedPoints,
    };
  }

  onMount(() => {
    socket.on("connect", () => {
      console.log("Connected to the server");
    });

    socket.on("disconnect", () => {
      console.log("Disconnected from the server");
    });

    socket.on("joystick_input", (data) => {
      joystickInput = JoystickSchema.parse(data);
    });

    socket.on("active_command", (data) => {
      if (!data.ID) {
        // Finished command sequence
        loadingAICommands = false;
        activeCommand = null;
      } else {
        aiCommands.push(data);
        activeCommand = data.ID;
      }
    });

    // Handle recording events
    socket.on("start_playback", (data) => {
      // If we don't already have this recording, add it
      if (!recordings.some((r) => r.timestamp === data.timestamp)) {
        recordings.push({
          timestamp: data.timestamp,
          duration: data.duration,
          isPlaying: true,
        });
      } else {
        // Update existing recording status
        recordings = recordings.map((r) =>
          r.timestamp === data.timestamp ? { ...r, isPlaying: true } : r,
        );
      }

      // Add a log entry
      logs.push({
        timestamp: new Date().toISOString(),
        message: "Started playback of recorded movements",
        icon: "info",
      });
    });

    socket.on("stop_playback", () => {
      // Update all recordings to not playing
      recordings = recordings.map((r) => ({ ...r, isPlaying: false }));

      // Add a log entry
      logs.push({
        timestamp: new Date().toISOString(),
        message: "Finished playback of recorded movements",
        icon: "info",
      });
    });

    socket.on("sensor_data", (data) => {
      previousSensorData = sensorData;
      mode = data.mode;
      localizationMode =
        typeof data.localization_mode === "string"
          ? data.localization_mode
          : null;
      try {
        sensorData = SensorDataSchema.parse(data.sensors);
        robotState = RobotStateSchema.parse(data.state);
        velocityProfileT = data.velocity_profile_t ?? null;
        velocityCommand = data.velocityCommand;
        maxLoopTime = data.max_loop_time ?? null;
        rayPoints = data.virtual_rays ?? null;
        latestLidarScan = normalizeLatestLidarScan(data.latest_lidar_scan);

        packetCount++;
        const now = new Date().getTime();
        if (now - lastRateUpdate >= 1000) {
          sensorRate = packetCount;
          packetCount = 0;
          lastRateUpdate = now;
        }
        lastSensorUpdate = now;

        if (distanceHistory.length > 50) {
          distanceHistory.shift(); // Keep the history to a maximum of 100 entries
        }

        distanceHistory.push(
          DistanceEntrySchema.parse({
            timestamp: new Date().toISOString(),
            distance_left: sensorData.ultrasonic.distance_left,
            distance_right: sensorData.ultrasonic.distance_right,
            distance_front: sensorData.tof.distance_front,
            distance: sensorData.ultrasonic.distance,
          }),
        );

        updateLogs();
      } catch (error) {
        console.log(error);
      }
    });

    socket.on("gesture_data", (data) => {
      gestureData = GestureDataSchema.parse(data); // Assuming gestureData is already in the correct format
    });

    socket.on("path_complete", () => {
      pathComplete = true;
    });

    socket.on("map_update", (data) => {
      mapUpdate = normalizeMapUpdate(data);
    });

    joystickSendInterval = setInterval(() => {
      const snapshot = $state.snapshot(uiJoystick);
      const isActive = snapshot.left_y !== 0 || snapshot.right_x !== 0;

      if (isActive) {
        socket.emit("joystick_input", snapshot);
      } else if (wasJoystickActive) {
        // Send exactly one neutral command when returning to center.
        socket.emit("joystick_input", snapshot);
      }

      wasJoystickActive = isActive;
    }, 100);

    return () => {
      if (joystickSendInterval) {
        clearInterval(joystickSendInterval);
        joystickSendInterval = null;
      }
      socket.disconnect();
    };
  });

  function runPath(payload: RunPathPayload) {
    pathComplete = false;
    socket.emit("set_state", {
      state: "PATH_FOLLOWING",
      path_type: payload.type,
      path: payload.path,
    });

    let message = "Sent path command";
    if (payload.type === "freehand") {
      message = `Sent freehand path with ${payload.path.length} points`;
    } else if (payload.type === "spline") {
      message = `Sent spline path with ${payload.path.splines.length} segment(s)`;
    } else if (payload.type === "point") {
      message = `Sent point target (${payload.path.x.toFixed(2)}, ${payload.path.y.toFixed(2)})`;
    } else if (payload.type === "point_dwa") {
      message = `Sent DWA point target (${payload.path.x.toFixed(2)}, ${payload.path.y.toFixed(2)})`;
    }

    logs.push({
      timestamp: new Date().toISOString(),
      message,
      icon: "send",
    });
  }

  function stopPathRun() {
    socket.emit("stop", {});
    socket.emit("set_state", { state: "MANUAL" });
    logs.push({
      timestamp: new Date().toISOString(),
      message: "Stopped path run and returned to MANUAL mode",
      icon: "warning",
    });
  }

  function obstacleDetected(data: SensorData): boolean {
    return data.ultrasonic.distance < 10;
  }

  function updateLogs() {
    if (!sensorData) return;

    let newLog = {
      timestamp: new Date().toISOString(),
      message: "",
      icon: "",
    };
    if (!previousSensorData) {
      newLog.message = "Starting";
      newLog.icon = "info";
      logs.push(newLog);
      return;
    }

    if (obstacleDetected(sensorData) !== obstacleDetected(previousSensorData)) {
      if (obstacleDetected(sensorData)) {
        newLog.message = "Obstacle detected!";
        newLog.icon = "warning";
      } else {
        newLog.message = "Path clear!";
        newLog.icon = "check";
      }
    }

    // Constrain to 50 entries
    if (logs.length >= 50) {
      logs.shift(); // Remove the oldest log entry
    }

    if (newLog.message) {
      logs.push(newLog);
    }
  }
</script>

<KeyboardHandler bind:joystick={uiJoystick} {inputFocus} />
<div class="h-screen w-full overflow-hidden bg-gray-50">
  <div class="flex h-full">
    <aside
      class="flex w-20 flex-col items-center border-r border-gray-200 bg-white py-3"
    >
      <div class="mb-4 text-[10px] font-black tracking-[0.2em] text-gray-500">
        TRACER
      </div>
      <nav class="flex w-full flex-1 flex-col items-center gap-2 px-2">
        {#each PAGE_CONFIG as page}
          <button
            type="button"
            title={page.label}
            onclick={() => (activePage = page.id)}
            class="flex w-full flex-col items-center gap-1 rounded-lg border px-2 py-2 text-[10px] font-bold tracking-wide transition-colors {activePage ===
            page.id
              ? 'border-gray-300 bg-gray-100 text-gray-900'
              : 'border-transparent bg-white text-gray-500 hover:bg-gray-50 hover:text-gray-800'}"
          >
            <svelte:component this={page.icon} class="h-4 w-4" />
            <span>{page.short}</span>
          </button>
        {/each}
      </nav>
    </aside>

    <main class="min-w-0 flex-1 p-3">
      <div class="flex h-full min-h-0 flex-col gap-2">
        <div class="grid w-full grid-cols-1 gap-2 lg:grid-cols-[1fr_auto_auto]">
          <Status {lastSensorUpdate} {mode} {localizationMode} bind:logs />
          <div class="flex flex-row gap-2 justify-between lg:justify-end">
            <RobotControls lastSensorUpdateTime={lastSensorUpdate} />
            <BatteryPercentage
              percent={sensorData?.battery ?? 0}
              lastSensorUpdateTime={lastSensorUpdate}
            />
          </div>
          <div class="flex flex-row justify-between gap-2 lg:justify-end">
            <Uptime {lastSensorUpdate} />
            <SensorRate rate={sensorRate} />
            <LoopTimeDisplay value={maxLoopTime} />
          </div>
        </div>

        <div class="min-h-0 flex-1 overflow-hidden">
          <div
            class="grid h-full grid-cols-12 grid-rows-12 gap-2"
            class:hidden={activePage !== "navigation"}
          >
            <div class="col-span-7 row-span-12 min-h-0">
              <PathDrawer
                robotPos={robotState
                  ? {
                      x: robotState.x,
                      y: robotState.y,
                      theta: robotState.yaw,
                    }
                  : null}
                {pathComplete}
                bind:freehandPath
                onRunPath={runPath}
                onStopRun={stopPathRun}
                {mapUpdate}
              />
            </div>
            <div class="col-span-5 row-span-6 min-h-0">
              <VelocityDebug
                {robotState}
                lastSensorUpdateTime={lastSensorUpdate}
              />
            </div>
            <div class="col-span-5 row-span-6 min-h-0">
              <ObstructionStatus
                {sensorData}
                {latestLidarScan}
                {robotState}
                {lastSensorUpdate}
                class="h-full"
              />
            </div>
          </div>

          {#if activePage === "overview"}
            <div class="grid h-full grid-cols-12 grid-rows-12 gap-2">
              <div class="col-span-7 row-span-8 min-h-0 overflow-hidden">
                <UltrasonicGraph {distanceHistory} />
              </div>

              <div class="col-span-5 row-span-8 min-h-0 flex flex-col gap-2">
                <div class="grid shrink-0 grid-cols-1 gap-2 md:grid-cols-2">
                  <TemperatureDisplay
                    temperature={sensorData?.imu.temperature ?? null}
                    class="h-full"
                  />
                  <ControlPad
                    bind:joystick={uiJoystick}
                    lastUpdateTime={lastSensorUpdate}
                  />
                </div>
                <div class="min-h-0 flex-1">
                  <ObstructionStatus
                    {sensorData}
                    {latestLidarScan}
                    {robotState}
                    {lastSensorUpdate}
                    class="h-full"
                  />
                </div>
              </div>

              <div class="col-span-5 row-span-4 min-h-0">
                <JoystickStatus
                  lastUpdateTime={lastSensorUpdate}
                  joystick={joystickInput}
                  class="h-full"
                />
              </div>

              <div class="col-span-7 row-span-4 min-h-0">
                <Logs {logs} class="h-full" />
              </div>
            </div>
          {:else if activePage === "diagnostics"}
            <div class="grid h-full grid-cols-12 grid-rows-12 gap-2">
              <div class="col-span-6 row-span-6 min-h-0 overflow-y-auto">
                <GyroMagDebug
                  {sensorData}
                  lastSensorUpdateTime={lastSensorUpdate}
                />
              </div>
              <div class="col-span-6 row-span-6 min-h-0 overflow-y-hidden">
                <GestureController {gestureData} />
              </div>
              <div class="col-span-12 row-span-6 min-h-0 overflow-hidden">
                <VelocityDebug
                  {robotState}
                  lastSensorUpdateTime={lastSensorUpdate}
                />
              </div>
            </div>
          {:else if activePage === "operations"}
            <div class="grid h-full grid-cols-12 grid-rows-12 gap-2">
              <div class="col-span-8 row-span-12 min-h-0">
                <CommandList
                  commands={aiCommands}
                  {activeCommand}
                  lastSensorUpdateTime={lastSensorUpdate}
                  loading={loadingAICommands}
                  bind:query={input}
                  {onSubmit}
                  bind:inputFocus
                  class="h-full overscroll-contain touch-manipulation hide-scrollbar"
                />
              </div>
              <div class="col-span-4 row-span-7 min-h-0">
                <Recordings
                  lastSensorUpdateTime={lastSensorUpdate}
                  bind:recordings
                  class="h-full"
                />
              </div>
              <div class="col-span-4 row-span-5 min-h-0">
                <Logs {logs} class="h-full" />
              </div>
            </div>
          {:else if activePage === "settings"}
            <div class="grid h-full min-h-0 grid-cols-12 grid-rows-12 gap-2">
              <div class="col-span-12 row-span-12 min-h-0">
                <ConstantTuner class="h-full" />
              </div>
            </div>
          {:else}
            <div class="grid h-full min-h-0 grid-cols-12 grid-rows-12 gap-2">
              <div class="col-span-12 row-span-7 min-h-0">
                <VelocityCommandWidget
                  class="h-full"
                  {robotState}
                  lastSensorUpdateTime={lastSensorUpdate}
                  {velocityProfileT}
                />
              </div>
              <div class="col-span-12 row-span-5 min-h-0">
                <VelocityDebug
                  {robotState}
                  lastSensorUpdateTime={lastSensorUpdate}
                />
              </div>
            </div>
          {/if}
        </div>
      </div>
    </main>
  </div>
</div>
