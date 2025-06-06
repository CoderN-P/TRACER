<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { type LogEntry } from '$lib/types';
    import { TriangleAlert, Check, Info,  CircleX } from "lucide-svelte";

    let { log }: { log: LogEntry } = $props();
    let LogIcon = $derived.by(getLogIcon);
    
    function formatTimestamp(timestamp: string): string {
        const date = new Date(timestamp);
        return date.toLocaleTimeString();
    }
    
    function getLogIcon(){
        switch (log.icon) {
            case 'warning':
                return TriangleAlert;
            case 'check':
                return Check;
            case 'info':
                return Info;
            case 'error':
                return CircleX;
            default:
                return Info; // Fallback icon
        }
    }
    
    function getLogColor() {
        switch (log.icon) {
            case 'warning':
                return 'text-yellow-500';
            case 'check':
                return 'text-green-500';
            case 'info':
                return 'text-blue-500';
            case 'error':
                return 'text-red-500';
            default:
                return 'text-gray-500'; // Fallback color
        }
    }
</script>


<div class="flex flex-row gap-4 items-center  w-full rounded-xl p-2 hover:bg-gray-50">
    <div class="shrink-0 text-xs font-mono text-gray-500">
        {formatTimestamp(log.timestamp)}
    </div>
    <div class="flex flex-row shrink-0 w-full items-center gap-2">
        <LogIcon class="h-4 w-4 {getLogColor()}" />
        <span class="{getLogColor()}">{log.message}</span>
    </div>
</div>

