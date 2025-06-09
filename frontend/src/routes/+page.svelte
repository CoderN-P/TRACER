<script lang="ts">
    import { io as socket } from '$lib/api/socket';
    import { onMount } from 'svelte';
    import {
        type SensorData,
        type Joystick,
        SensorDataSchema,
        JoystickSchema,
        type DistanceEntry,
        DistanceEntrySchema,
        type LogEntry
    } from "$lib/types";
    import Status from '$lib/components/Status.svelte';
    import Uptime from '$lib/components/Uptime.svelte';
    import Logs from '$lib/components/Logs.svelte';
    import ControlPad from '$lib/components/ControlPad.svelte';
    import JoystickStatus from "$lib/components/JoystickStatus.svelte";
    import UltrasonicGraph from "$lib/components/UltrasonicGraph.svelte";
    import SensorRate from "$lib/components/SensorRate.svelte";
    import KeyboardHandler from "$lib/components/KeyboardHandler.svelte";
    import TemperatureDisplay from "$lib/components/TemperatureDisplay.svelte";
    import QueryInput from "$lib/components/QueryInput.svelte";
    import ObstructionStatus from "$lib/components/ObstructionStatus.svelte";
    
    let sensorData = $state<SensorData | null>(null);
    let previousSensorData = $state<SensorData | null>(null);
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
    let packetCount = $state<number>(0);
    let sensorRate = $state<number>(-1);
    let lastRateUpdate = $state<number>(0);
    let distanceHistory = $state<DistanceEntry[]>([]);
    let input = $state<string>('');
    let inputFocus = $state<boolean>(false);
   
    
    function onSubmit(e) {
        if (input.trim() === '') return;
        socket.emit('query', {
            "query": input.trim(),
        });
        logs.push({
            timestamp: new Date().toISOString(),
            message: `Query sent: ${input}`,
            icon: 'send',
        });
        input = '';
    }
    
    onMount(() => {
        socket.on('connect', () => {
            console.log('Connected to the server');
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from the server');
        });

        socket.on('joystick_input', (data) => {
            joystickInput = JoystickSchema.parse(data);
        });
        
        socket.on('sensor_data', (data) => {
            previousSensorData = sensorData;
            sensorData = SensorDataSchema.parse(data);

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
            
            distanceHistory.push(DistanceEntrySchema.parse({
                timestamp: new Date().toISOString(),
                distance: sensorData.ultrasonic.distance
            }));
            
            updateLogs();
        });

        return () => {
            socket.disconnect();
        };
    });
    
    $effect(() => {
        socket.emit('joystick_input', uiJoystick);
    });
    
    function cliffDetected(data: SensorData): boolean {
        return !data.ir_back || !data.ir_front;
    }
    
    function obstacleDetected(data: SensorData): boolean {
        return data.ultrasonic.distance < 10;
    }
    
    function updateLogs(){
        if (!sensorData) return;
        
        let newLog = {
            timestamp: new Date().toISOString(),
            message: '',
            icon: '',
        }
        if (!previousSensorData){
            newLog.message = 'Starting';
            newLog.icon = 'info';
            logs.push(newLog);
            return;
        }
        
        if (cliffDetected(sensorData) !== cliffDetected(previousSensorData)) {
            if (cliffDetected(sensorData)) {
                newLog.message = 'Cliff detected!';
                newLog.icon = 'warning';
            } else {
                newLog.message = 'Cliff cleared!';
                newLog.icon = 'check';
            }
        }
        
        if (obstacleDetected(sensorData) !== obstacleDetected(previousSensorData)) {
            if (obstacleDetected(sensorData)) {
                newLog.message = 'Obstacle detected!';
                newLog.icon = 'warning';
            } else {
                newLog.message = 'Path clear!';
                newLog.icon = 'check';
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
    
    $effect(() => {
        socket.emit('joystick_input', $state.snapshot(uiJoystick));
    });
</script>


<KeyboardHandler bind:joystick={uiJoystick} {inputFocus} />
<div class="w-screen h-screen max-w-screen flex flex-col bg-gray-50 gap-2 p-4">
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <Status {lastSensorUpdate} bind:logs={logs}/>
        <Uptime {lastSensorUpdate} />
        <SensorRate rate={sensorRate} />
    </div>
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <UltrasonicGraph {distanceHistory}/>
        <div class="flex flex-col w-1/2 shrink-0 items-start gap-2 h-[400px] "> 
            <div class="flex flex-row w-full shrink-0 gap-2">
                <TemperatureDisplay temperature={sensorData?.imu.temperature ?? null} />
                <ControlPad bind:joystick={uiJoystick} lastUpdateTime={lastSensorUpdate}/>
            </div>
            <Logs {logs} />
        </div>
    </div>
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <div class="flex flex-row w-1/2 gap-2">
            <JoystickStatus lastUpdateTime={lastSensorUpdate} joystick={joystickInput}  />
            <ObstructionStatus {sensorData} {lastSensorUpdate}/>
        </div>
        
        
        
    </div>
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <QueryInput {onSubmit} bind:query={input} bind:inputFocus={inputFocus}/>
    </div>
</div>