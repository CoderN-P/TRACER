<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import * as THREE from "three";
  import type { GestureData } from "$lib/types";
  import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
  } from "$lib/components/ui/card";

  // Props
  export let gestureData: GestureData | null = null;

  // Three.js variables
  let container: HTMLElement;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let renderer: THREE.WebGLRenderer;
  let board: THREE.Mesh;
  let frameId: number;
  let clock: THREE.Clock;

  // Animation settings
  let targetRotation = { x: 0, y: 0, z: 0 };
  let currentRotation = { x: 0, y: 0, z: 0 };
  const ANIMATION_SPEED = 5.0; // Higher values = faster animation

  // View controls
  let manualViewEnabled = false;
  let orbitRadius = 5;
  let viewAngle = { x: 0, y: 0 };

  // Initial rendering setup
  function init() {
    // Create scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8f9fa);

    // Create camera
    const aspectRatio = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(75, aspectRatio, 0.1, 1000);
    // Position camera slightly above to see board at proper angle
    camera.position.set(0, 2, orbitRadius);
    camera.lookAt(0, 0, 0);

    // Initialize clock for animations
    clock = new THREE.Clock();

    // Create renderer
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 1);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 1, 1);
    directionalLight.castShadow = true;
    scene.add(directionalLight);

    // Create board geometry (rectangular board with thickness)
    const boardGeometry = new THREE.BoxGeometry(4, 2.5, 0.2);

    // Create materials for different sides of the board
    const frontMaterial = new THREE.MeshStandardMaterial({
      color: 0x16a34a, // Green color for PCB
      roughness: 0.8,
      metalness: 0.2,
    });

    // Add details to front side material using canvas texture
    const createBoardTexture = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 512;
      canvas.height = 320;
      const ctx = canvas.getContext("2d");

      if (ctx) {
        // Draw PCB background
        ctx.fillStyle = "#16a34a";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw some IC components
        ctx.fillStyle = "#333333";
        ctx.fillRect(200, 120, 100, 100); // Main IC
        ctx.fillRect(100, 150, 50, 50); // Secondary IC
        ctx.fillRect(350, 160, 40, 40); // Another component

        // Draw some traces
        ctx.strokeStyle = "#f0f0f0";
        ctx.lineWidth = 2;
        ctx.beginPath();
        // Horizontal traces
        for (let i = 0; i < 5; i++) {
          ctx.moveTo(50, 50 + i * 40);
          ctx.lineTo(450, 50 + i * 40);
        }
        // Vertical traces
        for (let i = 0; i < 3; i++) {
          ctx.moveTo(100 + i * 150, 20);
          ctx.lineTo(100 + i * 150, 300);
        }
        ctx.stroke();

        // Draw some LEDs
        ctx.fillStyle = "#ff0000"; // Red LED
        ctx.beginPath();
        ctx.arc(50, 50, 8, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#00ff00"; // Green LED
        ctx.beginPath();
        ctx.arc(50, 100, 8, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#0088ff"; // Blue LED
        ctx.beginPath();
        ctx.arc(50, 150, 8, 0, Math.PI * 2);
        ctx.fill();

        // Draw text label
        ctx.fillStyle = "#ffffff";
        ctx.font = "24px Arial";
        ctx.fillText("TRACER BOARD", 180, 40);

        // Draw component outlines for more detail
        ctx.strokeStyle = "#000000";
        ctx.lineWidth = 1;
        ctx.strokeRect(200, 120, 100, 100);
        ctx.strokeRect(100, 150, 50, 50);
        ctx.strokeRect(350, 160, 40, 40);

        // Draw some pins
        ctx.fillStyle = "#ddd";
        for (let i = 0; i < 8; i++) {
          ctx.fillRect(205 + i * 12, 230, 6, 15);
          ctx.fillRect(205 + i * 12, 95, 6, 15);
        }
      }

      return new THREE.CanvasTexture(canvas);
    };

    // Create the texture and assign it to front material
    const boardTexture = createBoardTexture();
    frontMaterial.map = boardTexture;

    const materials = [
      new THREE.MeshStandardMaterial({ color: 0x3498db }), // right side
      new THREE.MeshStandardMaterial({ color: 0x3498db }), // left side
      new THREE.MeshStandardMaterial({ color: 0x2c3e50 }), // top side
      new THREE.MeshStandardMaterial({ color: 0x2c3e50 }), // bottom side
      frontMaterial, // front side (with components)
      new THREE.MeshStandardMaterial({ color: 0xecf0f1 }), // back side
    ];

    // Create board mesh
    board = new THREE.Mesh(boardGeometry, materials);
    board.castShadow = true;
    board.receiveShadow = true;
    scene.add(board);

    // Add a ground plane to cast shadows on
    const groundGeometry = new THREE.PlaneGeometry(10, 10);
    const groundMaterial = new THREE.MeshStandardMaterial({
      color: 0xf0f0f0,
      roughness: 1.0,
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -1.5;
    ground.receiveShadow = true;
    scene.add(ground);

    // Add a grid for better spatial reference
    const gridHelper = new THREE.GridHelper(10, 10, 0x888888, 0xcccccc);
    gridHelper.position.y = -1.5;
    scene.add(gridHelper);

    // Add axis helper for orientation reference
    const axesHelper = new THREE.AxesHelper(5);
    scene.add(axesHelper);

    // Handle resize
    window.addEventListener("resize", onResize);

    // Add mouse event listeners for manual view control
    container.addEventListener("mousedown", onMouseDown);
    container.addEventListener("touchstart", onTouchStart, { passive: false });
  }

  // Mouse event handlers for manual view control
  function onMouseDown(event) {
    if (!manualViewEnabled) return;

    const startX = event.clientX;
    const startY = event.clientY;
    const startAngleX = viewAngle.x;
    const startAngleY = viewAngle.y;

    function onMouseMove(moveEvent) {
      const dx = moveEvent.clientX - startX;
      const dy = moveEvent.clientY - startY;

      viewAngle.y = startAngleY + dx * 0.01;
      viewAngle.x = startAngleX + dy * 0.01;

      updateCameraPosition();
    }

    function onMouseUp() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    }

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  // Touch event handlers for mobile devices
  function onTouchStart(event) {
    if (!manualViewEnabled) return;
    event.preventDefault();

    const touch = event.touches[0];
    const startX = touch.clientX;
    const startY = touch.clientY;
    const startAngleX = viewAngle.x;
    const startAngleY = viewAngle.y;

    function onTouchMove(moveEvent) {
      moveEvent.preventDefault();
      const touch = moveEvent.touches[0];
      const dx = touch.clientX - startX;
      const dy = touch.clientY - startY;

      viewAngle.y = startAngleY + dx * 0.01;
      viewAngle.x = startAngleX + dy * 0.01;

      updateCameraPosition();
    }

    function onTouchEnd() {
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("touchend", onTouchEnd);
    }

    container.addEventListener("touchmove", onTouchMove, { passive: false });
    container.addEventListener("touchend", onTouchEnd);
  }

  // Update camera position based on view angle
  function updateCameraPosition() {
    if (!manualViewEnabled) return;

    const x = orbitRadius * Math.sin(viewAngle.y) * Math.cos(viewAngle.x);
    // Add an offset to the y position to view from slightly above
    const y = orbitRadius * Math.sin(viewAngle.x) + 0.5;
    const z = orbitRadius * Math.cos(viewAngle.y) * Math.cos(viewAngle.x);

    camera.position.set(x, y, z);
    camera.lookAt(0, 0, 0);
  }

  // Animation loop with smooth transitions
  function animate() {
    const delta = clock.getDelta();

    // Smooth interpolation between current and target rotation
    currentRotation.x +=
      (targetRotation.x - currentRotation.x) * delta * ANIMATION_SPEED;
    currentRotation.y +=
      (targetRotation.y - currentRotation.y) * delta * ANIMATION_SPEED;
    currentRotation.z +=
      (targetRotation.z - currentRotation.z) * delta * ANIMATION_SPEED;

    // Only apply the board rotation if manual view is not enabled
    if (board && !manualViewEnabled) {
      // Apply rotation in the specific order
      board.rotation.set(0, 0, 0); // Reset rotation

      // At neutral position (0,0,0), the board should be parallel to the ground
      // Start with a -90 degree X rotation to make the board parallel to the ground
      board.rotateX(-Math.PI / 2);

      // Then apply the sensor rotations:
      // - Heading (Yaw): Rotation around the vertical axis
      board.rotateZ(currentRotation.y);

      // - Pitch: Tilt forward/backward
      // Negative pitch means tilting forward, positive means tilting backward
      board.rotateX(-currentRotation.x);

      // - Roll: Tilt left/right
      // Positive roll means tilting right, negative means tilting left
      board.rotateY(currentRotation.z);
    }

    renderer.render(scene, camera);
    frameId = requestAnimationFrame(animate);
  }

  // Handle window resize
  function onResize() {
    if (container && camera && renderer) {
      const width = container.clientWidth;
      const height = container.clientHeight;

      camera.aspect = width / height;
      camera.updateProjectionMatrix();

      renderer.setSize(width, height);
    }
  }

  // Toggle manual view control
  function toggleManualView() {
    manualViewEnabled = !manualViewEnabled;

    if (manualViewEnabled) {
      // Store current camera position for manual control
      viewAngle.x = 0;
      viewAngle.y = 0;
      updateCameraPosition();
    } else {
      // Reset camera position when disabling manual control
      camera.position.set(0, 2, orbitRadius);
      camera.lookAt(0, 0, 0);
    }
  }

  // Adjust camera zoom level
  function adjustZoom(amount: number) {
    orbitRadius = Math.max(2, Math.min(10, orbitRadius + amount));
    updateCameraPosition();
  }

  // Debug flag to log data
  let showDebug = false;

  // Update board orientation based on gesture data
  $: if (board && gestureData?.mag_angles && !manualViewEnabled) {
    // Convert degrees to radians
    const pitch = THREE.MathUtils.degToRad(gestureData.mag_angles.pitch);
    const heading = THREE.MathUtils.degToRad(gestureData.mag_angles.heading);
    const roll = THREE.MathUtils.degToRad(-gestureData.mag_angles.roll);

    if (showDebug) {
      console.log("Gesture data:", {
        pitch: gestureData.mag_angles.pitch,
        heading: gestureData.mag_angles.heading,
        roll: gestureData.mag_angles.roll,
      });
    }

    // Set target rotation for smooth animation
    targetRotation.x = pitch;
    // targetRotation.y = heading;
    targetRotation.z = roll;
  }

  // Function to calculate magnetometer field strength
  function getMagFieldStrength(
    mag: { x: number; y: number; z: number } | undefined,
  ): number {
    if (!mag) return 0;
    return Math.sqrt(mag.x * mag.x + mag.y * mag.y + mag.z * mag.z);
  }

  // Function to assess if magnetometer is calibrated
  function getMagCalibrationStatus(
    mag: { x: number; y: number; z: number } | undefined,
  ): { status: string; color: string } {
    if (!mag) return { status: "Unknown", color: "text-gray-500" };

    // Convert values from q8_7 16 bit int to float

    const strength = getMagFieldStrength(mag);

    // Earth's magnetic field is typically around 25-65 μT (0.25-0.65 Gauss)
    if (strength < 15) {
      return { status: "Too weak", color: "text-red-500" };
    } else if (strength > 70) {
      return { status: "Too strong", color: "text-red-500" };
    } else if (strength >= 25 && strength <= 65) {
      return { status: "Good", color: "text-green-500" };
    } else {
      return { status: "Marginal", color: "text-yellow-500" };
    }
  }

  // Lifecycle hooks
  onMount(() => {
    if (container) {
      init();
      animate();
    }
  });

  onDestroy(() => {
    if (frameId) {
      cancelAnimationFrame(frameId);
    }
    if (renderer) {
      renderer.dispose();
    }
    if (typeof window !== "undefined") {
      window.removeEventListener("resize", onResize);
      container.removeEventListener("mousedown", onMouseDown);
      container.removeEventListener("touchstart", onTouchStart);
    }
  });
</script>

<Card class="w-full h-full overflow-y-scroll">
  <CardHeader>
    <CardTitle>Board Orientation</CardTitle>
    <CardDescription>
      Real-time 3D visualization of the board's orientation
      <span class="block text-xs mt-1 text-muted-foreground">
        0° roll & pitch = parallel to ground | +pitch = up (back) | -pitch =
        down (front) | +roll = right | -roll = left
      </span>
    </CardDescription>

    <div class="flex items-center gap-2 mt-2">
      <button
        class="px-3 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
        on:click={toggleManualView}
      >
        {manualViewEnabled ? "Auto View" : "Manual View"}
      </button>

      {#if manualViewEnabled}
        <button
          class="px-3 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
          on:click={() => adjustZoom(-0.5)}
        >
          Zoom In
        </button>
        <button
          class="px-3 py-1 text-xs rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:hover:bg-slate-600 transition-colors"
          on:click={() => adjustZoom(0.5)}
        >
          Zoom Out
        </button>
        <span class="text-xs text-muted-foreground ml-1">(Drag to rotate)</span>
      {/if}
    </div>
  </CardHeader>
  <CardContent>
    <div
      bind:this={container}
      class="w-full h-[220px] rounded-md overflow-hidden {manualViewEnabled
        ? 'cursor-move'
        : ''}"
    ></div>
  </CardContent>
  <CardFooter class="flex flex-col items-start space-y-2 text-sm">
    {#if gestureData}
      <div class="grid grid-cols-3 gap-4 w-full">
        <div>
          <span class="font-semibold">Heading:</span>
          <span>{gestureData.mag_angles?.heading.toFixed(2) ?? "N/A"}°</span>
        </div>
        <div>
          <span class="font-semibold">Pitch:</span>
          <span>{gestureData.mag_angles?.pitch.toFixed(2) ?? "N/A"}°</span>
        </div>
        <div>
          <span class="font-semibold">Roll:</span>
          <span>{gestureData.mag_angles?.roll.toFixed(2) ?? "N/A"}°</span>
        </div>
      </div>

      <!-- Accelerometer data -->
      <div class="w-full mt-2 pt-2 border-t">
        <div class="font-semibold mb-1">Accelerometer (G):</div>
        <div class="grid grid-cols-3 gap-4 w-full">
          <div>X: {gestureData.accelerometer?.x.toFixed(2) ?? "N/A"}</div>
          <div>Y: {gestureData.accelerometer?.y.toFixed(2) ?? "N/A"}</div>
          <div>Z: {gestureData.accelerometer?.z.toFixed(2) ?? "N/A"}</div>
        </div>
      </div>

      <!-- Magnetometer data -->
      <div class="w-full mt-2 pt-2 border-t">
        <div class="font-semibold mb-1">Magnetometer (μT):</div>
        <div class="grid grid-cols-3 gap-4 w-full">
          <div>X: {gestureData.magnetometer?.x.toFixed(2) ?? "N/A"}</div>
          <div>Y: {gestureData.magnetometer?.y.toFixed(2) ?? "N/A"}</div>
          <div>Z: {gestureData.magnetometer?.z.toFixed(2) ?? "N/A"}</div>
        </div>
        <!-- Calibration status -->
        <div class="mt-2">
          <span class="font-semibold">Calibration status:</span>
          <span class={getMagCalibrationStatus(gestureData.magnetometer).color}>
            {getMagCalibrationStatus(gestureData.magnetometer).status}
          </span>
        </div>
      </div>
      <!-- Ambient Light data -->
      <div class="w-full mt-2 pt-2 border-t">
        <div class="font-semibold mb-1">Light:</div>
        <div class="grid grid-cols-3 gap-4 w-full">
          <div>Lux: {gestureData.light?.lux.toFixed(1) ?? "N/A"}</div>
          <div>CH0: {gestureData.light?.ch0 ?? "N/A"}</div>
          <div>CH1: {gestureData.light?.ch1 ?? "N/A"}</div>
        </div>
      </div>

      <!-- Temperature -->
      <div class="w-full mt-2 pt-2 border-t">
        <div>Temperature: {gestureData.temperature?.toFixed(1) ?? "N/A"}°C</div>
      </div>

      <!-- Debug toggle -->
      <div class="w-full mt-2 pt-2 border-t flex justify-end">
        <label class="flex items-center cursor-pointer">
          <input type="checkbox" bind:checked={showDebug} class="mr-2" />
          <span>Debug mode</span>
        </label>
      </div>
    {:else}
      <div class="text-muted-foreground">No sensor data available</div>
    {/if}
  </CardFooter>
</Card>
