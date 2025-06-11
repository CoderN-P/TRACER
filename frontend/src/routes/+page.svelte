<script lang="ts">
    import { io as socket } from '$lib/api/socket';
    import { onMount } from 'svelte';
    import {
        type SensorData,
        type Command,
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
    import BatteryPercentage from "$lib/components/BatteryPercentage.svelte";
    import ObstructionStatus from "$lib/components/ObstructionStatus.svelte";
    import CommandList from "$lib/components/CommandList.svelte";
    import Recordings from "$lib/components/Recordings.svelte";
    
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
    let loadingAICommands = $state<boolean>(false);
    let aiCommands = $state<Command[]>([]);
    let activeCommand = $state<string | null>(null);
    let recordings = $state<{timestamp: string, isPlaying?: boolean, name?: string, duration: number}[]>([]);
   
    
    function onSubmit(e) {
        if (input.trim() === '') return;
        loadingAICommands = true;
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
        
        socket.on('active_command', (data) => {
            if (!data.ID) { // Finished command sequence
                loadingAICommands = false;
                activeCommand = null;
            } else {
                aiCommands.push(data);
                activeCommand = data.ID;
            }
        });
        
        // Handle recording events
        socket.on('start_playback', (data) => {
            // If we don't already have this recording, add it
            if (!recordings.some(r => r.timestamp === data.timestamp)) {
                recordings.push({
                    timestamp: data.timestamp,
                    duration: data.duration,
                    isPlaying: true
                });
            } else {
                // Update existing recording status
                recordings = recordings.map(r => 
                    r.timestamp === data.timestamp ? {...r, isPlaying: true} : r
                );
            }
            
            // Add a log entry
            logs.push({
                timestamp: new Date().toISOString(),
                message: 'Started playback of recorded movements',
                icon: 'info'
            });
        });
        
        socket.on('stop_playback', () => {
            // Update all recordings to not playing
            recordings = recordings.map(r => ({ ...r, isPlaying: false }));
            
            // Add a log entry
            logs.push({
                timestamp: new Date().toISOString(),
                message: 'Finished playback of recorded movements',
                icon: 'info'
            });
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
<div class="flex flex-col gap-2 p-4 ">
    <!-- Status bar - Keep row on mobile but make it wrap -->
    <div class="w-full flex flex-col md:flex-row items-center gap-2 justify-between">
        <Status {lastSensorUpdate} bind:logs={logs}/>
        <BatteryPercentage percent={sensorData?.battery ?? 0} 
                          lastSensorUpdateTime={lastSensorUpdate} />
        <div class="flex flex-row gap-2 w-full justify-between md:justify-end">
            <Uptime {lastSensorUpdate} />
            <SensorRate rate={sensorRate} />
        </div>
    </div>
    
    <!-- Main content area - Stack on mobile, side by side on desktop -->
    <div class="w-full flex flex-col md:flex-row items-stretch gap-2">
        <!-- Left column on desktop, top section on mobile -->
        <div class="w-full md:w-1/2 flex-grow">
            <UltrasonicGraph {distanceHistory}/>
        </div>
        
        <!-- Right column on desktop, bottom section on mobile -->
        <div class="flex flex-col w-full md:w-1/2 items-start gap-2"> 
            <!-- Temperature and Control Pad - Stack on small mobile, side by side otherwise -->
            <div class="flex flex-col sm:flex-row w-full gap-2">
                <TemperatureDisplay temperature={sensorData?.imu.temperature ?? null}/>
                <ControlPad bind:joystick={uiJoystick} 
                            lastUpdateTime={lastSensorUpdate}
                            class="w-full sm:w-1/2"/>
            </div>
            
            <!-- Logs section with mobile optimizations -->
            <Logs {logs} class="w-full" />
        </div>
    </div>
    
    <!-- Joystick status and obstruction area -->
    <div class="w-full flex flex-col sm:flex-row items-stretch gap-2">
        <JoystickStatus lastUpdateTime={lastSensorUpdate} 
                       joystick={joystickInput}
                       class="w-full h-full sm:w-1/2"/>
        <ObstructionStatus {sensorData} 
                          {lastSensorUpdate}
                          class="w-full h-full sm:w-1/2"/>
    </div>
    
    <!-- Recordings and Command List Section - Side by side on large screens -->
    <div class="w-full flex flex-col lg:flex-row items-stretch gap-2">
        <!-- Recordings section -->
        <div class="w-full lg:w-2/5">
            <Recordings bind:recordings={recordings} class="h-full" />
        </div>
        
        <!-- Command list section - Full width with mobile optimizations -->
        <div class="w-full lg:w-3/5">
            <CommandList commands={aiCommands} 
                        activeCommand={activeCommand} 
                        lastSensorUpdateTime={lastSensorUpdate} 
                        loading={loadingAICommands} 
                        bind:query={input} 
                        onSubmit={onSubmit} 
                        bind:inputFocus 
                        class="overscroll-contain touch-manipulation hide-scrollbar" />
        </div>
    </div>
</div>