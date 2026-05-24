import React, { useMemo } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { Slider } from '@/components/Slider';
import { useStore } from '@/state/useStore';
import { computeStats, fmt } from '@/services/math';
import { colors, fonts, spacing, typography } from '@/theme';

export default function Calc() {
  const prefs = useStore((s) => s.preferences);
  const update = useStore((s) => s.updatePreferences);

  const stats = useMemo(() => computeStats(prefs), [prefs]);

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <BackHeader eyebrow="THE MATH" title="Your time tax." />

          <View style={styles.sliders}>
            <Slider
              label="DRIVES PER DAY"
              value={prefs.drivesPerDay}
              min={0}
              max={20}
              onChange={(v) => update({ drivesPerDay: v })}
            />
            <Slider
              label="LIGHTS PER DRIVE"
              value={prefs.lightsPerDrive}
              min={0}
              max={30}
              onChange={(v) => update({ lightsPerDrive: v })}
            />
            <Slider
              label="AVG WAIT"
              value={prefs.avgWait}
              min={0}
              max={120}
              unit="s"
              onChange={(v) => update({ avgWait: v })}
            />
            <Slider
              label="% ON PHONE AT REDS"
              value={prefs.phoneShare}
              min={0}
              max={100}
              unit="%"
              onChange={(v) => update({ phoneShare: v })}
            />
            <Slider
              label="EXTRA SECONDS WHEN MISSED"
              value={prefs.reactionPenalty}
              min={0}
              max={15}
              unit="s"
              onChange={(v) => update({ reactionPenalty: v })}
            />
            <Slider
              label="YEARS DRIVING"
              value={prefs.yearsDriving}
              min={1}
              max={80}
              onChange={(v) => update({ yearsDriving: v })}
            />
          </View>

          <View style={styles.outputs}>
            <Output label="PER DAY" value={fmt(stats.totalDay)} />
            <View style={styles.divider} />
            <Output label="PER YEAR" value={fmt(stats.totalYear)} />
            <View style={styles.divider} />
            <Output label="LIFETIME" value={fmt(stats.totalLife)} tone="danger" big />
          </View>

          <View style={styles.reclaim}>
            <Text style={[typography.label, { color: '#0a0807' }]}>RECLAIMABLE</Text>
            <Text style={styles.reclaimValue}>{fmt(stats.reclaimLife)}</Text>
            <Text style={styles.reclaimSub}>Time you’d save by just looking up.</Text>
          </View>

          <Text style={styles.footnote}>
            Use only when parked or as a passenger.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </Background>
  );
}

function Output({
  label,
  value,
  tone = 'default',
  big = false,
}: {
  label: string;
  value: string;
  tone?: 'default' | 'danger';
  big?: boolean;
}) {
  const color = tone === 'danger' ? colors.danger : colors.text;
  return (
    <View style={styles.outputRow}>
      <Text style={typography.label}>{label}</Text>
      <Text
        style={[
          styles.outputValue,
          { color, fontSize: big ? 56 : 36, lineHeight: big ? 60 : 40 },
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: spacing.xl,
  },
  sliders: {
    paddingHorizontal: spacing.lg,
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  outputs: {
    marginTop: spacing.xl,
    marginHorizontal: spacing.lg,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.md,
  },
  outputRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    paddingVertical: spacing.sm,
  },
  outputValue: {
    fontFamily: fonts.serifItalic,
  },
  divider: {
    height: 1,
    backgroundColor: colors.border,
  },
  reclaim: {
    marginTop: spacing.lg,
    marginHorizontal: spacing.lg,
    backgroundColor: colors.success,
    padding: spacing.md,
    gap: 4,
  },
  reclaimValue: {
    fontFamily: fonts.serifItalic,
    fontSize: 56,
    color: '#0a0807',
    lineHeight: 60,
  },
  reclaimSub: {
    fontFamily: fonts.mono,
    color: '#0a0807',
    fontSize: 11,
    opacity: 0.7,
  },
  footnote: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.2,
    textAlign: 'center',
    marginTop: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
});
