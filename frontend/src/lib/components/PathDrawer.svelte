<script>
    import { browser } from "$app/environment";
    import { PlusIcon, Trash } from "lucide-svelte";
    import { Stage, Layer, Line, Circle, Text } from "svelte-konva";
    import {QuinticHermiteSplineSvelte, SplinePathSvelte} from "$lib/types/index.js";

    let path = new SplinePathSvelte();
    

    const WIDTH = 800;           // canvas width in pixels
    const HEIGHT = 400;          // canvas height in pixels
    const GRID_SPACING = 100;    // pixels between grid lines
    const TICK_LENGTH = 10;      // length of axis ticks
    const PATH_RENDER_INTERVAL = 0.01; // seconds (dt)
    const SCALE = 100; // pixels per meter

    function getGridLines(width, height, spacing) {
        let lines = [];
        // vertical lines every `spacing` across the width
        for (let x = 0; x <= width; x += spacing) {
            lines.push({ points: [x, 0, x, height], orientation: 'v', pos: x });
        }
        // horizontal lines every `spacing` across the height
        for (let y = 0; y <= height; y += spacing) {
            lines.push({ points: [0, y, width, y], orientation: 'h', pos: y });
        }
        return lines;
    }

    function getAxisTicks(width, height, spacing, tickLength) {
        let ticks = [];
        // X axis ticks (bottom) along width
        for (let x = 0; x <= width; x += spacing) {
            ticks.push({ x1: x, y1: height, x2: x, y2: height - tickLength, label: (x / SCALE).toString() });
        }
        // Y axis ticks (left) along height
        for (let y = 0; y <= height; y += spacing) {
            ticks.push({ x1: 0, y1: y, x2: tickLength, y2: y, label: (y / SCALE).toString() });
        }
        return ticks;
    }

    $: gridLines = getGridLines(WIDTH, HEIGHT, GRID_SPACING);
    $: axisTicks = getAxisTicks(WIDTH, HEIGHT, GRID_SPACING, TICK_LENGTH);

</script>

{#if !browser}
    <p>Loading...</p>
{:else}
    <div class="rounded-lg border border-gray-200 p-4 flex flex-col">
        <div class="flex flex-row items-center gap-2">
            <button on:click={() => path.QuinticHermiteSplines.pop()} class="mb-4 p-2 bg-gray-50 w-min flex items-center text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors">
                <Trash class="w-4 h-4 inline-block" />
            </button>
            <button on:click={() => path.addSpline(new QuinticHermiteSplineSvelte(
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length - 1].x1 : 0), // Start at the end of the last spline
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].y1 : 0),
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].dx1 : 1),
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].dy1 : 1),
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].ddx1 : 1),
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].ddy1 : 1),
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].x1 : 0) + 1, // Extend
                (path.QuinticHermiteSplines.length > 0 ? path.QuinticHermiteSplines[path.QuinticHermiteSplines.length -1].y1 : 0) + 1,
                0.5, // dx2
                0.5, // dy2
                0.5, // ddx2
                0.5  // ddy2
            ))} class="mb-4 p-2 bg-gray-50 w-min flex items-center text-black border border-gray-200 rounded-md hover:bg-gray-100 transition-colors">
                <PlusIcon class="w-4 h-4 inline-block" />
            </button>
        </div>

    <Stage width={WIDTH} height={HEIGHT}>
        <!-- Render the path as a blue line -->
        <Layer>
            {#each gridLines as line}
                <Line points={line.points} stroke="#eee" strokeWidth={1} />
            {/each}
            {#each axisTicks as tick}
                <Line points={[tick.x1, tick.y1, tick.x2, tick.y2]} stroke="#888" strokeWidth={2} />
                <Text x={tick.x2 + 2} y={tick.y2 + 2} text={tick.label} fontSize={10} fill="#888" />
            {/each}
        </Layer>
        <Layer>
            <Line points={path.render(PATH_RENDER_INTERVAL, SCALE, WIDTH, HEIGHT)} stroke="blue" strokeWidth={2} closed={false} />
        </Layer>
        <!-- Render control points as red circles -->
        {#each path.getControlPoints(SCALE, WIDTH, HEIGHT) as cp, idx}
            <Layer>
                <Circle x={cp.x} y={cp.y} radius={5} fill="red" draggable ondragmove={(e) => path.updateControlPoint(idx, e.target.position().x, e.target.position().y, SCALE, WIDTH, HEIGHT)}/>
            </Layer>
        {/each}
        <!-- Render lines from control points to the path as dashed gray lines -->
        {#each path.getControlLines(SCALE, WIDTH, HEIGHT) as cl}
            <Layer>
                <Line points={[cl.x1, cl.y1, cl.x2, cl.y2]} stroke="gray" strokeWidth={1} dash={[4, 4]} />
                <Text x={(cl.x1 + cl.x2) / 2} y={(cl.y1 + cl.y2) / 2} text={cl.label} fontSize={12} fill="gray" />
            </Layer>
        {/each}
    </Stage>
    </div>
{/if}