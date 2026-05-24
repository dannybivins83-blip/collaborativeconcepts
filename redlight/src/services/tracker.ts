import * as Location from 'expo-location';

export interface DetectedStop {
  intersection: string;
  waitSec: number;
  attentive: boolean;
  lat?: number;
  lng?: number;
}

export interface Tracker {
  start(onStop: (stop: DetectedStop) => void): Promise<void>;
  stop(): void;
  isRunning(): boolean;
}

const FAKE_INTERSECTIONS = [
  'Main St & 5th Ave',
  'Oak Blvd & Mission',
  'Park Pl & Larkin',
  'Sunset & 14th',
  'Pine St & Cole',
  'Cedar Ave & 23rd',
  'Bay Pkwy & Lincoln',
];

export class SimulatedTracker implements Tracker {
  private interval: ReturnType<typeof setInterval> | null = null;
  private running = false;

  async start(onStop: (stop: DetectedStop) => void): Promise<void> {
    this.running = true;
    this.interval = setInterval(() => {
      if (!this.running) return;
      const intersection =
        FAKE_INTERSECTIONS[Math.floor(Math.random() * FAKE_INTERSECTIONS.length)] ?? 'Unknown';
      const waitSec = 18 + Math.floor(Math.random() * 40);
      const attentive = Math.random() > 0.45;
      onStop({ intersection, waitSec, attentive });
    }, 4000);
  }

  stop(): void {
    this.running = false;
    if (this.interval) clearInterval(this.interval);
    this.interval = null;
  }

  isRunning(): boolean {
    return this.running;
  }
}

export class RealTracker implements Tracker {
  private subscription: Location.LocationSubscription | null = null;
  private running = false;
  private stopStart: number | null = null;
  private stopCoord: { lat: number; lng: number } | null = null;
  private callback: ((stop: DetectedStop) => void) | null = null;

  async start(onStop: (stop: DetectedStop) => void): Promise<void> {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      throw new Error('Location permission denied');
    }
    this.callback = onStop;
    this.running = true;
    this.subscription = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.BestForNavigation,
        timeInterval: 1000,
        distanceInterval: 1,
      },
      (loc) => this.onLocation(loc),
    );
  }

  private onLocation(loc: Location.LocationObject): void {
    const speedMps = loc.coords.speed ?? 0;
    const speedMph = speedMps * 2.23694;
    const now = Date.now();
    if (speedMph < 2) {
      if (this.stopStart === null) {
        this.stopStart = now;
        this.stopCoord = { lat: loc.coords.latitude, lng: loc.coords.longitude };
      } else {
        const waitSec = (now - this.stopStart) / 1000;
        if (waitSec > 15 && this.stopCoord && this.callback) {
          this.callback({
            intersection: 'Unknown intersection',
            waitSec: Math.round(waitSec),
            attentive: true,
            lat: this.stopCoord.lat,
            lng: this.stopCoord.lng,
          });
          this.stopStart = null;
          this.stopCoord = null;
        }
      }
    } else {
      this.stopStart = null;
      this.stopCoord = null;
    }
  }

  stop(): void {
    this.running = false;
    this.stopStart = null;
    this.stopCoord = null;
    this.callback = null;
    if (this.subscription) {
      this.subscription.remove();
      this.subscription = null;
    }
  }

  isRunning(): boolean {
    return this.running;
  }
}

export const TRACKER_MODE: 'SIM' | 'REAL' = 'SIM';

export function createTracker(): Tracker {
  return TRACKER_MODE === 'SIM' ? new SimulatedTracker() : new RealTracker();
}
