import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { CalcInputs, DEFAULT_INPUTS } from '@/services/math';

export type AchievementId = 'firstDay' | 'weekOne' | 'eyesUp' | 'timeLord';

export interface SessionStop {
  id: string;
  timestamp: number;
  intersection: string;
  waitSec: number;
  attentive: boolean;
}

interface RedlightState {
  hydrated: boolean;
  onboarded: boolean;
  streak: number;
  lastSessionDate: string | null;
  todayAttention: number;
  secondsReclaimed: number;
  weekHistory: number[];
  achievements: Record<AchievementId, boolean>;
  preferences: CalcInputs;
  stops: SessionStop[];
  weeklyGoalLights: number;
  weeklyCaught: number;
  analyticsOptOut: boolean;

  setHydrated: () => void;
  setOnboarded: (v: boolean) => void;
  updatePreferences: (p: Partial<CalcInputs>) => void;
  recordLightCatch: (reclaimedSec: number) => void;
  recordLightMiss: (lostSec: number) => void;
  addStop: (s: Omit<SessionStop, 'id' | 'timestamp'>) => void;
  resetSession: () => void;
  bumpStreakIfNewDay: () => void;
  unlock: (id: AchievementId) => void;
  setAnalyticsOptOut: (v: boolean) => void;
  resetAll: () => void;
}

const todayKey = (): string => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

const dayDiff = (a: string, b: string): number => {
  const da = new Date(a + 'T00:00:00').getTime();
  const db = new Date(b + 'T00:00:00').getTime();
  return Math.round((db - da) / 86400000);
};

const initialWeek = (): number[] => [0, 0, 0, 0, 0, 0, 0];

const initialAchievements: Record<AchievementId, boolean> = {
  firstDay: false,
  weekOne: false,
  eyesUp: false,
  timeLord: false,
};

export const useStore = create<RedlightState>()(
  persist(
    (set, get) => ({
      hydrated: false,
      onboarded: false,
      streak: 0,
      lastSessionDate: null,
      todayAttention: 0,
      secondsReclaimed: 0,
      weekHistory: initialWeek(),
      achievements: { ...initialAchievements },
      preferences: { ...DEFAULT_INPUTS },
      stops: [],
      weeklyGoalLights: 50,
      weeklyCaught: 0,
      analyticsOptOut: false,

      setHydrated: () => set({ hydrated: true }),
      setOnboarded: (v) => set({ onboarded: v }),

      updatePreferences: (p) =>
        set((s) => ({ preferences: { ...s.preferences, ...p } })),

      recordLightCatch: (reclaimedSec) => {
        get().bumpStreakIfNewDay();
        const s = get();
        const newAttention = Math.min(100, s.todayAttention + 4);
        const newReclaimed = s.secondsReclaimed + reclaimedSec;
        const week = [...s.weekHistory];
        week[6] = newAttention;
        const weeklyCaught = s.weeklyCaught + 1;
        set({
          todayAttention: newAttention,
          secondsReclaimed: newReclaimed,
          weekHistory: week,
          weeklyCaught,
        });
        if (newAttention >= 90) get().unlock('eyesUp');
        if (newReclaimed >= 3600) get().unlock('timeLord');
      },

      recordLightMiss: (_lostSec) => {
        get().bumpStreakIfNewDay();
        const s = get();
        const newAttention = Math.max(0, s.todayAttention - 6);
        const week = [...s.weekHistory];
        week[6] = newAttention;
        set({ todayAttention: newAttention, weekHistory: week });
      },

      addStop: (s) =>
        set((state) => ({
          stops: [
            {
              id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
              timestamp: Date.now(),
              ...s,
            },
            ...state.stops,
          ].slice(0, 100),
        })),

      resetSession: () => set({ stops: [] }),

      bumpStreakIfNewDay: () => {
        const today = todayKey();
        const s = get();
        if (s.lastSessionDate === today) return;
        let nextStreak = 1;
        if (s.lastSessionDate) {
          const diff = dayDiff(s.lastSessionDate, today);
          if (diff === 1) nextStreak = s.streak + 1;
          else if (diff === 0) nextStreak = s.streak;
          else nextStreak = 1;
        }
        const week = [...s.weekHistory.slice(1), 0];
        set({
          streak: nextStreak,
          lastSessionDate: today,
          todayAttention: 0,
          weekHistory: week,
        });
        get().unlock('firstDay');
        if (nextStreak >= 7) get().unlock('weekOne');
      },

      unlock: (id) =>
        set((s) =>
          s.achievements[id]
            ? s
            : { achievements: { ...s.achievements, [id]: true } },
        ),

      setAnalyticsOptOut: (v) => set({ analyticsOptOut: v }),

      resetAll: () =>
        set({
          streak: 0,
          lastSessionDate: null,
          todayAttention: 0,
          secondsReclaimed: 0,
          weekHistory: initialWeek(),
          achievements: { ...initialAchievements },
          stops: [],
          weeklyCaught: 0,
        }),
    }),
    {
      name: 'redlight-store-v1',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({
        onboarded: s.onboarded,
        streak: s.streak,
        lastSessionDate: s.lastSessionDate,
        todayAttention: s.todayAttention,
        secondsReclaimed: s.secondsReclaimed,
        weekHistory: s.weekHistory,
        achievements: s.achievements,
        preferences: s.preferences,
        weeklyGoalLights: s.weeklyGoalLights,
        weeklyCaught: s.weeklyCaught,
        analyticsOptOut: s.analyticsOptOut,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHydrated();
      },
    },
  ),
);
