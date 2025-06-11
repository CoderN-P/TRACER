<script lang="ts">
	import '../app.css';
	import { Toaster } from '$lib/components/ui/sonner';
	
	let { children } = $props();
	
	
	// Add viewport meta tag for mobile optimization
	// We need to do this in the layout to ensure it applies to all pages
	if (typeof document !== 'undefined') {
		// Make sure viewport meta tag exists
		let viewportMeta = document.querySelector('meta[name="viewport"]');
		if (!viewportMeta) {
			viewportMeta = document.createElement('meta');
			viewportMeta.setAttribute('name', 'viewport');
			document.head.appendChild(viewportMeta);
		}
		
		// Set viewport properties for mobile optimization
		viewportMeta.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
		
		// Add touch-action meta tag for mobile
		let touchMeta = document.querySelector('meta[name="touch-action"]');
		if (!touchMeta) {
			touchMeta = document.createElement('meta');
			touchMeta.setAttribute('name', 'touch-action');
			document.head.appendChild(touchMeta);
		}
		touchMeta.setAttribute('content', 'manipulation');
	}
</script>

<svelte:head>
	<style>
		/* Mobile-specific styles */
		@media (max-width: 640px) {
			.overscroll-contain {
				overscroll-behavior: contain;
				-webkit-overflow-scrolling: touch;
			}
			
			/* Better touch targets for mobile */
			.touch-manipulation {
				touch-action: manipulation;
			}
			
			/* Hide scrollbars but keep functionality */
			.hide-scrollbar::-webkit-scrollbar {
				width: 1px;
				height: 1px;
				background-color: transparent;
			}
		}
	</style>
</svelte:head>

<Toaster />
{@render children()}
