import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { PulseDot } from '@/components/PulseDot';
import { Stat } from '@/components/Stat';
import { useStore } from '@/state/useStore';
import { createTracker, Tracker } from '@/services/tracker';
import { colors, fonts, spacing, typography } from '@/theme';

export default function Track() {
  const stops = useStore((s) => s.stops);
  const addStop = useStore((s) => s.addStop);
  const resetSession = useStore((s) => s.resetSession);
  const prefs = useStore((s) => s.preferences);

  const trackerRef = useRef<Tracker | null>(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    return () => {
      trackerRef.current?.stop();
      trackerRef.current = null;
    };
  }, []);

  const start = useCallback(async () => {
    if (running) return;
    const tracker = createTracker();
    trackerRef.current = tracker;
    try {
      await tracker.start((stop) => {
        addStop(stop);
      });
      setRunning(true);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Could not start tracking';
      Alert.alert('Tracking unavailable', message);
      trackerRef.current = null;
    }
  }, [addStop, running]);

  const stop = useCallback(() => {
    trackerRef.current?.stop();
    trackerRef.current = null;
    setRunning(false);
  }, []);

  const totals = useMemo(() => {
    const totalWait = stops.reduce((acc, s) => acc + s.waitSec, 0);
    const lost = stops
      .filter((s) => !s.attentive)
      .reduce((acc, s) => acc + s.waitSec * prefs.reactionPenalty * 0.1, 0);
    return {
      count: stops.length,
      timeLost: totalWait,
      taxPaid: lost,
    };
  }, [stops, prefs.reactionPenalty]);

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <BackHeader eyebrow="AUTO-TRACK" title="Stops, logged." />

        <View style={styles.statusRow}>
          {running ? <PulseDot color={colors.danger} size={10} /> : <View style={styles.dotIdle} />}
          <Text style={styles.statusLabel}>{running ? 'TRACKING' : 'IDLE'}</Text>
          <View style={{ flex: 1 }} />
          <Pressable
            onPress={running ? stop : start}
            style={({ pressed }) => [
              styles.toggle,
              { backgroundColor: running ? colors.danger : colors.accent },
              pressed && { opacity: 0.8 },
            ]}
          >
            <Text style={styles.toggleLabel}>{running ? 'STOP' : 'START'}</Text>
          </Pressable>
        </View>

        <View style={styles.statsRow}>
          <Stat label="STOPS" value={totals.count} />
          <View style={styles.statDivider} />
          <Stat label="TIME LOST" value={`${totals.timeLost}s`} />
          <View style={styles.statDivider} />
          <Stat label="TAX PAID" value={`${Math.round(totals.taxPaid)}s`} accent />
        </View>

        <View style={styles.listHead}>
          <Text style={typography.eyebrow}>TODAY’S STOPS</Text>
          <Pressable onPress={resetSession} hitSlop={8}>
            <Text style={styles.clear}>CLEAR</Text>
          </Pressable>
        </View>

        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        >
          {stops.length === 0 ? (
            <Text style={styles.empty}>
              No stops yet. Hit START to begin logging — the simulator will drop in a fake stop every
              four seconds so you can see how the live log feels.
            </Text>
          ) : (
            stops.map((s) => (
              <View key={s.id} style={styles.row}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.intersection}>{s.intersection}</Text>
                  <Text style={styles.meta}>
                    {new Date(s.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                    {'  ·  '}
                    {s.waitSec}s
                  </Text>
                </View>
                <Text
                  style={[
                    styles.badge,
                    s.attentive ? styles.badgeOk : styles.badgeBad,
                  ]}
                >
                  {s.attentive ? 'ATTENTIVE' : 'LOST'}
                </Text>
              </View>
            ))
          )}
        </ScrollView>

        <Text style={styles.footnote}>
          Use only when parked or as a passenger. The simulator is on — see TODO.md to enable real GPS.
        </Text>
      </SafeAreaView>
    </Background>
  );
}

const styles = StyleSheet.create({
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.border,
  },
  dotIdle: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.muted,
  },
  statusLabel: {
    fontFamily: fonts.monoBold,
    color: colors.text,
    fontSize: 11,
    letterSpacing: 1.4,
    marginLeft: 6,
  },
  toggle: {
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  toggleLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 11,
    letterSpacing: 1.4,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderColor: colors.border,
  },
  statDivider: {
    width: 1,
    height: 36,
    backgroundColor: colors.border,
    marginHorizontal: spacing.md,
  },
  listHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  clear: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.muted,
    letterSpacing: 1.4,
  },
  list: {
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
    gap: spacing.sm,
  },
  empty: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 12,
    lineHeight: 18,
    marginTop: spacing.md,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.sm,
  },
  intersection: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 18,
  },
  meta: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 11,
    marginTop: 2,
    letterSpacing: 1,
  },
  badge: {
    fontFamily: fonts.monoBold,
    fontSize: 9,
    letterSpacing: 1.4,
    paddingHorizontal: 6,
    paddingVertical: 4,
    borderWidth: 1,
  },
  badgeOk: {
    color: colors.success,
    borderColor: colors.success,
  },
  badgeBad: {
    color: colors.danger,
    borderColor: colors.danger,
  },
  footnote: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.2,
    textAlign: 'center',
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.md,
  },
});
