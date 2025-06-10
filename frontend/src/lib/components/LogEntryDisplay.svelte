<script lang="ts">
    import { Skeleton } from '$lib/components/ui/skeleton';
    import { type LogEntry } from '$lib/types';
    import { TriangleAlert, Check, Info, CircleX } from "lucide-svelte";

    let { log }: { log: LogEntry } = $props();
    let LogIcon = $derived.by(getLogIcon);
    
    // Format timestamp to show hours, minutes, seconds and milliseconds
    function formatTimestamp(timestamp: string): string {
        const date = new Date(timestamp);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');
        const milliseconds = date.getMilliseconds().toString().padStart(3, '0');
        return `${hours}:${minutes}:${seconds}.${milliseconds.substring(0,2)}`;
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
    
    function getLogBackground() {
        switch (log.icon) {
            case 'warning':
                return 'bg-yellow-50';
            case 'check':
                return 'bg-green-50';
            case 'info':
                return 'bg-blue-50';
            case 'error':
                return 'bg-red-50';
            default:
                return 'bg-gray-50'; // Fallback background
        }
    }
    
    function getIconBackground() {
        switch (log.icon) {
            case 'warning':
                return 'bg-yellow-100';
            case 'check':
                return 'bg-green-100';
            case 'info':
                return 'bg-blue-100';
            case 'error':
                return 'bg-red-100';
            default:
                return 'bg-gray-100'; // Fallback background
        }
    }
</script>

<div class="flex flex-row items-center w-full rounded-md py-1.5 px-2 hover:{getLogBackground()} border-l-2 border-transparent hover:border-l-2 hover:border-l-{getLogColor().replace('text-', '')} transition-colors">
    <div class="shrink-0 text-xs font-mono text-gray-400 mr-2 hidden sm:block">
        {formatTimestamp(log.timestamp)}
    </div>
    
    <div class="flex flex-row items-center gap-2 w-full">
        <div class="shrink-0 p-1 rounded-full {getIconBackground()}">
            <LogIcon class="h-3.5 w-3.5 {getLogColor()}" />
        </div>
        
        <div class="flex-grow">
            <span class="text-sm font-medium {getLogColor()}">{log.message}</span>
        </div>
        
        <div class="text-[10px] font-mono text-gray-400 ml-2 sm:hidden">
            {formatTimestamp(log.timestamp)}
        </div>
    </div>
</div>

