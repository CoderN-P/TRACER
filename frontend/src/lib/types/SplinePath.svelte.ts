import { QuinticHermiteSplineSvelte } from "./QuinticHermiteSpline.svelte";

export class SplinePathSvelte {
    public QuinticHermiteSplines: QuinticHermiteSplineSvelte[] = $state([]);

    constructor() {
    }

    public addSpline(spline: QuinticHermiteSplineSvelte) {
        this.QuinticHermiteSplines.push(spline);
    }
    
    
    public render(dt: number = 0.01, scale: number = 100, canvasWidth: number = 800, canvasHeight: number = 800): number[] {
        const points: number[] = [];
        
        for (let i = 0; i < this.QuinticHermiteSplines.length; i++) {
            const spline = this.QuinticHermiteSplines[i];
            for (let t = 0; t <= 1; t += dt) {
                const { x, y } = spline.evaluate(t);
                points.push(x * scale, -y * scale);
            }
        }
        return points;
    }
    
    public getControlPoints(scale: number = 100, canvasWidth: number = 800, canvasHeight: number = 800): { x: number; y: number }[] {
        const controlPoints: { x: number; y: number }[] = [];
        
        for (let i = 0; i < this.QuinticHermiteSplines.length; i++) {
            const spline = this.QuinticHermiteSplines[i];
            controlPoints.push({ x: scale * spline.x0, y: -scale * spline.y0 });
            controlPoints.push({ x: scale * (spline.x0 + spline.dx0), y: -scale * (spline.y0 + spline.dy0) });
            controlPoints.push({ x: scale * (spline.x0 + 0.5 * spline.ddx0), y: -scale * (spline.y0 + 0.5 * spline.ddy0) });
            
            // Only draw final control points for the last spline to avoid duplicates
            if (i === this.QuinticHermiteSplines.length - 1) {
                controlPoints.push({ x: scale * spline.x1, y: -scale * spline.y1 });
                controlPoints.push({
                    x: scale * (spline.x1 + spline.dx1),
                    y: -scale * (spline.y1 + spline.dy1)
                });
                controlPoints.push({
                    x: scale * (spline.x1 + 0.5 * spline.ddx1),
                    y: -scale * (spline.y1 + 0.5 * spline.ddy1)
                });
            }
        }
        return controlPoints;
    }
    
    public getControlLines(scale: number = 100, canvasWidth: number = 800, canvasHeight: number = 800): { x1: number; y1: number; x2: number; y2: number, label: string }[] {
        const controlLines: { x1: number; y1: number; x2: number, y2: number, label: string }[] = [];
        
        for (let i = 0; i < this.QuinticHermiteSplines.length; i++) {
            const spline = this.QuinticHermiteSplines[i];
            controlLines.push({ x1: scale * spline.x0, y1: -scale * spline.y0, x2: scale * (spline.x0 + spline.dx0), y2: -scale * (spline.y0 + spline.dy0), label: "vel" });
            controlLines.push({ x1: scale * spline.x0, y1: -scale * spline.y0, x2: scale * (spline.x0 + 0.5 * spline.ddx0), y2: -scale * (spline.y0 + 0.5 * spline.ddy0), label: "accel" });
            
            if (i === this.QuinticHermiteSplines.length - 1) {
                controlLines.push({
                    x1: scale * spline.x1,
                    y1: -scale * spline.y1,
                    x2: scale * (spline.x1 + spline.dx1),
                    y2: -scale * (spline.y1 + spline.dy1),
                    label: "vel"
                });
                controlLines.push({
                    x1: scale * spline.x1,
                    y1: -scale * spline.y1,
                    x2: scale * (spline.x1 + 0.5 * spline.ddx1),
                    y2: -scale * (spline.y1 + 0.5 * spline.ddy1),
                    label: "accel"
                });
            }
        }
        return controlLines;
    }
    
    public updateControlPoint(controlPointIndex: number, newX: number, newY: number, scale: number = 100, canvasWidth: number = 800, canvasHeight: number = 800) {
        const totalControlPoints = this.QuinticHermiteSplines.length * 6 - (this.QuinticHermiteSplines.length - 1) * 3; // Each spline has 6 control points, but adjacent splines share control points
        
        if (controlPointIndex >= totalControlPoints) {
            throw new Error("Control point index out of range");
        }
        
        let splineIndex = Math.floor(controlPointIndex / 3);
        let pointType = controlPointIndex % 3;
        // If we are in the last 3 control points, we need to adjust the spline index and point type to account for shared control points
        if (controlPointIndex >= totalControlPoints - 3) { 
            splineIndex--;
            pointType += 3; // Shift to the last 3 control points of the last spline
        }
        
        if (splineIndex >= this.QuinticHermiteSplines.length) {
            throw new Error("Control point index out of range");
        }
        
        const spline = this.QuinticHermiteSplines[splineIndex];
        
        const scaledX = newX / scale;
        const scaledY = -newY / scale; // Invert Y (canvas Y-down → world Y-up)
        
        switch (pointType) {
            case 0:
                spline.x0 = scaledX;
                spline.y0 = scaledY;
                
                if (splineIndex > 0) {
                    const prevSpline = this.QuinticHermiteSplines[splineIndex - 1];
                    prevSpline.x1 = scaledX;
                    prevSpline.y1 = scaledY;
                }
                break;
            case 1:
                spline.dx0 = scaledX - spline.x0;
                spline.dy0 = scaledY - spline.y0;
                
                if (splineIndex > 0) {
                    const prevSpline = this.QuinticHermiteSplines[splineIndex - 1];
                    prevSpline.dx1 = scaledX - prevSpline.x1;
                    prevSpline.dy1 = scaledY - prevSpline.y1;
                }
                break;
            case 2:
                spline.ddx0 = 2 * (scaledX - spline.x0);
                spline.ddy0 = 2 * (scaledY - spline.y0);
                
                if (splineIndex > 0) {
                    const prevSpline = this.QuinticHermiteSplines[splineIndex - 1];
                    prevSpline.ddx1 = 2 * (scaledX - prevSpline.x1);
                    prevSpline.ddy1 = 2 * (scaledY - prevSpline.y1);
                }
                break;
            case 3:
                spline.x1 = scaledX;
                spline.y1 = scaledY;
                break;
            case 4:
                spline.dx1 = scaledX - spline.x1;
                spline.dy1 = scaledY - spline.y1;
                break;
            case 5:
                spline.ddx1 = 2 * (scaledX - spline.x1);
                spline.ddy1 = 2 * (scaledY - spline.y1);
                break;
        }
    }
        

    public exportToJSON(): {
        splines: {
            start: [number, number];
            end: [number, number];
            start_velocity: [number, number];
            end_velocity: [number, number];
            start_acceleration: [number, number];
            end_acceleration: [number, number];
        }[]
    } {
        const splines = this.QuinticHermiteSplines.map(spline => ({
            start: [spline.x0, spline.y0] as [number, number],
            end: [spline.x1, spline.y1] as [number, number],
            start_velocity: [spline.dx0, spline.dy0] as [number, number],
            end_velocity: [spline.dx1, spline.dy1] as [number, number],
            start_acceleration: [spline.ddx0, spline.ddy0] as [number, number],
            end_acceleration: [spline.ddx1, spline.ddy1] as [number, number],
        }));
        
        return {
            splines
        }
    }
}
    