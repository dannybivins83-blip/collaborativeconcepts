export interface CalcInputs {
  drivesPerDay: number;
  lightsPerDrive: number;
  avgWait: number;
  phoneShare: number;
  reactionPenalty: number;
  yearsDriving: number;
}

export interface CalcResult {
  redsPerDay: number;
  baseSec: number;
  inattentive: number;
  taxSec: number;
  cascadeSec: number;
  totalDay: number;
  reclaimDay: number;
  totalYear: number;
  reclaimYear: number;
  totalLife: number;
  reclaimLife: number;
}

export function computeStats(inputs: CalcInputs): CalcResult {
  const { drivesPerDay, lightsPerDrive, avgWait, phoneShare, reactionPenalty, yearsDriving } = inputs;

  const redsPerDay = drivesPerDay * lightsPerDrive;
  const baseSec = redsPerDay * avgWait;
  const inattentive = redsPerDay * (phoneShare / 100);
  const taxSec = inattentive * reactionPenalty;
  const cascadeSec = inattentive * 0.25 * avgWait;
  const totalDay = baseSec + taxSec + cascadeSec;
  const reclaimDay = taxSec + cascadeSec;

  const daysPerYear = 365;
  const totalYear = totalDay * daysPerYear;
  const reclaimYear = reclaimDay * daysPerYear;
  const totalLife = totalYear * yearsDriving;
  const reclaimLife = reclaimYear * yearsDriving;

  return {
    redsPerDay,
    baseSec,
    inattentive,
    taxSec,
    cascadeSec,
    totalDay,
    reclaimDay,
    totalYear,
    reclaimYear,
    totalLife,
    reclaimLife,
  };
}

const SEC_PER_MIN = 60;
const SEC_PER_HOUR = 3600;
const SEC_PER_DAY = 86400;
const SEC_PER_MONTH = 2629800;
const SEC_PER_YEAR = 31557600;

export function fmt(sec: number): string {
  if (!isFinite(sec) || sec < 0) return '0s';
  if (sec < SEC_PER_MIN) return `${Math.round(sec)}s`;
  if (sec < SEC_PER_HOUR) return `${Math.round(sec / SEC_PER_MIN)}m`;
  if (sec < SEC_PER_DAY) return `${(sec / SEC_PER_HOUR).toFixed(1)}h`;
  if (sec < SEC_PER_MONTH) return `${(sec / SEC_PER_DAY).toFixed(1)}d`;
  if (sec < SEC_PER_YEAR) return `${(sec / SEC_PER_MONTH).toFixed(1)}mo`;
  return `${(sec / SEC_PER_YEAR).toFixed(1)}y`;
}

export const DEFAULT_INPUTS: CalcInputs = {
  drivesPerDay: 4,
  lightsPerDrive: 6,
  avgWait: 35,
  phoneShare: 60,
  reactionPenalty: 3,
  yearsDriving: 50,
};
