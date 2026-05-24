export type LightColor = 'red' | 'yellow' | 'green' | 'none';

export interface LightDetector {
  start(onLightChange: (color: LightColor) => void): Promise<void>;
  stop(): void;
}

export class SimulatedLightDetector implements LightDetector {
  private interval: ReturnType<typeof setTimeout> | null = null;
  private timeouts: ReturnType<typeof setTimeout>[] = [];
  private running = false;

  async start(onLightChange: (color: LightColor) => void): Promise<void> {
    this.running = true;
    const cycle = () => {
      if (!this.running) return;
      onLightChange('red');
      this.timeouts.push(
        setTimeout(() => {
          if (!this.running) return;
          onLightChange('green');
          this.timeouts.push(
            setTimeout(() => {
              if (!this.running) return;
              cycle();
            }, 4000),
          );
        }, 8000),
      );
    };
    cycle();
  }

  stop(): void {
    this.running = false;
    if (this.interval) clearInterval(this.interval);
    this.timeouts.forEach(clearTimeout);
    this.timeouts = [];
    this.interval = null;
  }
}

export class TFLiteLightDetector implements LightDetector {
  async start(_onLightChange: (color: LightColor) => void): Promise<void> {
    throw new Error(
      'TFLiteLightDetector not implemented yet. Add react-native-fast-tflite, ship a traffic-light model, and wire it to the camera frame processor. See TODO.md.',
    );
  }
  stop(): void {
    // no-op
  }
}

export const DETECTOR_MODE: 'SIM' | 'REAL' = 'SIM';

export function createLightDetector(): LightDetector {
  return DETECTOR_MODE === 'SIM' ? new SimulatedLightDetector() : new TFLiteLightDetector();
}
