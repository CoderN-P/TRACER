export class QuinticHermiteSplineSvelte {
    x0: number  = $state(0);
    y0: number  = $state(0);
    dx0: number = $state(0);
    dy0: number = $state(0);
    ddx0: number = $state(0);
    ddy0: number = $state(0);
    x1: number  = $state(0);
    y1: number  = $state(0);
    dx1: number = $state(0);
    dy1: number = $state(0);
    ddx1: number = $state(0);
    ddy1: number = $state(0);
    
    constructor(
        x0: number, y0: number, dx0: number, dy0: number, ddx0: number, ddy0: number,
        x1: number, y1: number, dx1: number, dy1: number, ddx1: number, ddy1: number
    ) {
        this.x0 = x0;
        this.y0 = y0;
        this.dx0 = dx0;
        this.dy0 = dy0;
        this.ddx0 = ddx0;
        this.ddy0 = ddy0;
        this.x1 = x1;
        this.y1 = y1;
        this.dx1 = dx1;
        this.dy1 = dy1;
        this.ddx1 = ddx1;
        this.ddy1 = ddy1;
    }
    
    public evaluate(t: number): { x: number; y: number } {
        const h05 = 1 - 10*t**3 + 15*t**4 - 6*t**5
        const h15 = t -6*t**3 + 8*t**4 - 3*t**5
        const h25 = 0.5*t**2 - 1.5*t**3 + 1.5*t**4 - 0.5*t**5
        const h35 = 0.5*t**3 - t**4 + 0.5*t**5
        const h45 = -4*t**3 + 7*t**4 -3*t**5
        const h55 = 10*t**3 - 15*t**4 + 6*t**5
        
        const x = h05*this.x0 + h15*this.dx0 + h25*this.ddx0 + h35*this.ddx1 + h45*this.dx1 + h55*this.x1
        const y = h05*this.y0 + h15*this.dy0 + h25*this.ddy0 + h35*this.ddy1 + h45*this.dy1 + h55*this.y1
        
        return { x, y }
    }
}