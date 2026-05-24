import { computeStats, fmt, DEFAULT_INPUTS } from './math';

describe('fmt()', () => {
  it('formats sub-minute as seconds', () => {
    expect(fmt(0)).toBe('0s');
    expect(fmt(1)).toBe('1s');
    expect(fmt(59.4)).toBe('59s');
  });

  it('formats minutes', () => {
    expect(fmt(60)).toBe('1m');
    expect(fmt(150)).toBe('3m');
    expect(fmt(3599)).toBe('60m');
  });

  it('formats hours', () => {
    expect(fmt(3600)).toBe('1.0h');
    expect(fmt(7200)).toBe('2.0h');
    expect(fmt(86399)).toBe('24.0h');
  });

  it('formats days', () => {
    expect(fmt(86400)).toBe('1.0d');
    expect(fmt(86400 * 10)).toBe('10.0d');
  });

  it('formats months', () => {
    expect(fmt(2629800)).toBe('1.0mo');
    expect(fmt(2629800 * 6)).toBe('6.0mo');
  });

  it('formats years', () => {
    expect(fmt(31557600)).toBe('1.0y');
    expect(fmt(31557600 * 2.5)).toBe('2.5y');
  });

  it('clamps invalid input', () => {
    expect(fmt(-1)).toBe('0s');
    expect(fmt(NaN)).toBe('0s');
    expect(fmt(Infinity)).toBe('0s');
  });
});

describe('computeStats()', () => {
  it('matches the documented formula on defaults', () => {
    const r = computeStats(DEFAULT_INPUTS);
    expect(r.redsPerDay).toBe(24);
    expect(r.baseSec).toBe(24 * 35);
    expect(r.inattentive).toBeCloseTo(24 * 0.6);
    expect(r.taxSec).toBeCloseTo(24 * 0.6 * 3);
    expect(r.cascadeSec).toBeCloseTo(24 * 0.6 * 0.25 * 35);
    expect(r.totalDay).toBeCloseTo(r.baseSec + r.taxSec + r.cascadeSec);
    expect(r.reclaimDay).toBeCloseTo(r.taxSec + r.cascadeSec);
  });

  it('scales linearly across years', () => {
    const r = computeStats(DEFAULT_INPUTS);
    expect(r.totalYear).toBeCloseTo(r.totalDay * 365);
    expect(r.totalLife).toBeCloseTo(r.totalYear * DEFAULT_INPUTS.yearsDriving);
  });

  it('returns zero when inputs are zero', () => {
    const r = computeStats({
      drivesPerDay: 0,
      lightsPerDrive: 0,
      avgWait: 0,
      phoneShare: 0,
      reactionPenalty: 0,
      yearsDriving: 0,
    });
    expect(r.totalDay).toBe(0);
    expect(r.reclaimLife).toBe(0);
  });

  it('handles phoneShare = 100 (always inattentive)', () => {
    const r = computeStats({ ...DEFAULT_INPUTS, phoneShare: 100 });
    expect(r.inattentive).toBe(r.redsPerDay);
  });
});
