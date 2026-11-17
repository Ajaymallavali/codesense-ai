// Game loop calculations
export function compute_tick_rate(fps: number): number {
    return Math.floor(1000 / fps);
}

export interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    radius: number;
}

export function updateEntities(particles: Particle[], delta: number): void {
    for (const p of particles) {
        p.x += p.vx * delta;
        p.y += p.vy * delta;
    }
}

export function connectParticles(ctx: CanvasRenderingContext2D, particles: Particle[], maxDistance: number): void {
    // Pairwise O(N^2) particle network connection
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < maxDistance) {
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.stroke();
            }
        }
    }
}

export function checkCollisions(p1: Particle, p2: Particle): boolean {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    return distance < (p1.radius + p2.radius);
}

export function renderGameLoop(ctx: CanvasRenderingContext2D, particles: Particle[]): void {
    ctx.clearRect(0, 0, 800, 600);
    updateEntities(particles, 0.016);
    connectParticles(ctx, particles, 100);
}
