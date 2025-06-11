<script lang="ts">
  import * as Card from "$lib/components/ui/card";
  import { type Joystick } from "$lib/types";
  import { Skeleton } from "$lib/components/ui/skeleton";
  import { Button } from "$lib/components/ui/button";
  import { io as socket } from "$lib/api/socket";
  import { Gamepad2, Car, Fuel as Tank, Target, Gamepad } from "lucide-svelte";
  import { onMount } from "svelte";

  // Define available joystick modes
  type JoystickMode = "TWO_ARCADE" | "ONE_ARCADE" | "TANK" | "CAR";

  let {
    joystick,
    lastUpdateTime,
    class: className = "",
  }: { joystick: Joystick; lastUpdateTime: number; class?: string } = $props();

  // Mode and precision states
  let currentMode = $state<JoystickMode>("TWO_ARCADE");
  let precisionMode = $state<boolean>(false);

  // Display names for modes
  const modeNames: Record<JoystickMode, string> = {
    TWO_ARCADE: "Two Joystick Arcade",
    ONE_ARCADE: "Single Joystick Arcade",
    TANK: "Tank Drive",
    CAR: "Car Mode",
  };

  // Icons for each mode
  function getModeIcon(mode: JoystickMode) {
    switch (mode) {
      case "TWO_ARCADE":
        return Gamepad2;
      case "ONE_ARCADE":
        return Gamepad;
      case "TANK":
        return Tank;
      case "CAR":
        return Car;
      default:
        return Gamepad2;
    }
  }
  
  let CurrentModeIcon = $derived.by(() => getModeIcon(currentMode));
  
  

  // Handle mode change from UI
  function changeMode(mode: JoystickMode) {
    socket.emit("joystick_mode", { mode });
  }

  // Toggle precision mode
  function togglePrecisionMode() {
    const newPrecisionMode = !precisionMode;
    socket.emit("precision_mode", { enabled: newPrecisionMode });
  }

  // Socket event handlers
  function handleJoystickModeChange(data: { mode: JoystickMode }) {
    currentMode = data.mode;
  }

  function handlePrecisionModeChange(data: { enabled: boolean }) {
    precisionMode = data.enabled;
  }

  onMount(() => {
    // Listen for mode updates from backend
    socket.on("joystick_mode", handleJoystickModeChange);
    socket.on("precision_mode", handlePrecisionModeChange);

    return () => {
      // Clean up event listeners
      socket.off("joystick_mode", handleJoystickModeChange);
      socket.off("precision_mode", handlePrecisionModeChange);
    };
  });
</script>

{#if lastUpdateTime === 0 || !joystick}
  <Skeleton class="w-full h-48 rounded-sm " />
{:else}
  <Card.Root class="w-full h-full {className}">
    <Card.Header>
      <div class="flex items-center justify-between">
        <div>
          <Card.Title>Joystick Status</Card.Title>
          <Card.Description>Showing current joystick position</Card.Description>
        </div>
        <div class="flex items-center">
          <CurrentModeIcon
            class="w-5 h-5 text-blue-500 mr-1"
          />
          <span class="text-xs font-medium">{modeNames[currentMode]}</span>
        </div>
      </div>
    </Card.Header>
    <Card.Content class="flex flex-col items-center justify-center p-4">
      <div
        class="relative w-20 h-20 mx-auto bg-gray-100 rounded-full border border-gray-200"
      >
        <div
          class="absolute w-6 h-6 bg-blue-500 rounded-full border-2 border-white shadow-lg transition-all duration-200"
          style="left: calc(50% - 12px + {-30 *
            joystick.right_x}px); top: calc(50% - 12px + {-30 *
            joystick.left_y}px)"
        ></div>
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-2 h-2 bg-gray-300 rounded-full"></div>
        </div>
      </div>

      <!-- Display values for better understanding -->
      <div class="flex flex-row gap-4 mt-4 text-xs">
        <div class="flex flex-col items-center">
          <span class="font-semibold">Left-Y</span>
          <span>{joystick.left_y.toFixed(2)}</span>
        </div>
        <div class="flex flex-col items-center">
          <span class="font-semibold">Right-X</span>
          <span>{joystick.right_x.toFixed(2)}</span>
        </div>
      </div>

      <!-- Precision mode toggle -->
      <div class="mt-4 w-full">
        <Button
          variant={precisionMode ? "default" : "outline"}
          size="sm"
          class="w-full {precisionMode ? 'bg-blue-500 hover:bg-blue-600' : ''}"
          onclick={togglePrecisionMode}
        >
          <Target class="w-4 h-4 mr-1" />
          {precisionMode ? "Precision Mode On" : "Precision Mode Off"}
        </Button>
      </div>

      <!-- Mode selector -->
      <div class="mt-4 w-full">
        <h4 class="text-xs font-medium mb-2 text-gray-500">
          Change Drive Mode
        </h4>
        <div class="grid grid-cols-2 gap-2">
          {#each Object.keys(modeNames) as mode}
            <Button
              variant={currentMode === mode ? "default" : "outline"}
              size="sm"
              class={currentMode === mode
                ? "bg-blue-500 hover:bg-blue-600"
                : ""}
              onclick={() => changeMode(mode as JoystickMode)}
            >
              {#if getModeIcon(mode as JoystickMode) === Gamepad2}
                <Gamepad2 class="w-4 h-4 mr-1" />
              {:else if getModeIcon(mode as JoystickMode) === Gamepad}
                <Gamepad class="w-4 h-4 mr-1" />
              {:else if getModeIcon(mode as JoystickMode) === Tank}
                <Tank class="w-4 h-4 mr-1" />
              {:else if getModeIcon(mode as JoystickMode) === Car}
                <Car class="w-4 h-4 mr-1" />
              {/if}
              <span class="text-xs"
                >{mode
                  .split("_")
                  .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
                  .join(" ")}</span
              >
            </Button>
          {/each}
        </div>
      </div>
    </Card.Content>
  </Card.Root>
{/if}
