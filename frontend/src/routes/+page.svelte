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
    import {Skeleton} from "$lib/components/ui/skeleton";
    import JoystickStatus from "$lib/components/JoystickStatus.svelte";
    import UltrasonicGraph from "$lib/components/UltrasonicGraph.svelte";
    import SensorRate from "$lib/components/SensorRate.svelte";
    
    let sensorData = $state<SensorData | null>(null);
    let previousSensorData = $state<SensorData | null>(null);
    let logs = $state<LogEntry[]>([]);
    let joystickInput = $state<Joystick | null>(null);
    let uiJoystick = $state<Joystick | null>(null);
    let lastSensorUpdate = $state<number>(0);
    let packetCount = $state<number>(0);
    let sensorRate = $state<number>(-1);
    let lastRateUpdate = $state<number>(0);
    let distanceHistory = $state<DistanceEntry[]>([]);
    
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
            
            if (distanceHistory.length > 2){
                const start = distanceHistory[0].timestamp;
                const end = distanceHistory[distanceHistory.length - 1].timestamp;
                
                // Check if it covers the range of 10 seconds
                if (new Date(end).getTime() - new Date(start).getTime() >= 10000) {
                    distanceHistory.shift(); // Remove the oldest entry
                }
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
        return data.ultrasonic.distance < 20;
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
</script>

<div class="w-screen h-screen flex flex-col bg-white gap-2 p-4">
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <Status {lastSensorUpdate} bind:logs={logs}/>
        <Uptime {lastSensorUpdate} />
        <SensorRate rate={sensorRate} />
    </div>
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <UltrasonicGraph/>
    </div>
    <div class="w-full flex flex-row items-center gap-2 justify-between">
        <JoystickStatus lastUpdateTime={lastSensorUpdate} joystick={joystickInput}  />
        <Logs {logs} />
    </div>
</div>