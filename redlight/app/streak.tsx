import React, { useEffect } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { useStore, AchievementId } from '@/state/useStore';
import { scheduleDailyStreakReminder } from '@/services/notifications';
import { colors, fonts, spacing, typography } from '@/theme';

const DAY_LABELS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

const ACHIEVEMENTS: {
  id: AchievementId;
  title: string;
  body: string;
}[] = [
  { id: 'firstDay', title: 'First Day', body: 'Logged your first attentive drive.' },
  { id: 'weekOne', title: 'Week One', body: 'Seven days in a row. Habit forming.' },
  { id: 'eyesUp', title: 'Eyes Up', body: 'Hit 90% attention in a single day.' },
  { id: 'timeLord', title: 'Time Lord', body: 'Reclaimed a full hour of your life.' },
];

export default function Streak() {
  const router = useRouter();
  const streak = useStore((s) => s.streak);
  const weekHistory = useStore((s) => s.weekHistory);
  const achievements = useStore((s) => s.achievements);

  useEffect(() => {
    scheduleDailyStreakReminder().catch(() => {});
  }, []);

  const maxBar = Math.max(100, ...weekHistory);

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <BackHeader eyebrow="STREAK" title="Day after day." />

          <View style={styles.bigWrap}>
            <Text style={styles.bigNumber}>{streak}</Text>
            <Text style={typography.eyebrow}>DAY STREAK</Text>
          </View>

          <View style={styles.chart}>
            <Text style={typography.eyebrow}>THIS WEEK</Text>
            <View style={styles.bars}>
              {weekHistory.map((v, i) => {
                const h = Math.max(4, (v / maxBar) * 120);
                const active = v >= 80;
                return (
                  <View key={i} style={styles.barCol}>
                    <View
                      style={[
                        styles.bar,
                        {
                          height: h,
                          backgroundColor: active ? colors.accent : colors.border,
                        },
                      ]}
                    />
                    <Text style={styles.barLabel}>{DAY_LABELS[i]}</Text>
                  </View>
                );
              })}
            </View>
          </View>

          <View style={styles.section}>
            <Text style={typography.eyebrow}>ACHIEVEMENTS</Text>
            <View style={styles.achList}>
              {ACHIEVEMENTS.map((a) => {
                const unlocked = !!achievements[a.id];
                return (
                  <View
                    key={a.id}
                    style={[styles.achCard, !unlocked && styles.achCardLocked]}
                  >
                    <Text style={[styles.achTitle, !unlocked && styles.dim]}>{a.title}</Text>
                    <Text style={[styles.achBody, !unlocked && styles.dim]}>{a.body}</Text>
                    <Text style={[styles.achStatus, !unlocked && styles.dim]}>
                      {unlocked ? '✓ UNLOCKED' : '— LOCKED'}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>

          <Pressable onPress={() => router.push('/settings')} style={styles.legalLink}>
            <Text style={styles.legalLinkLabel}>SETTINGS · PRIVACY · SAFETY →</Text>
          </Pressable>
          <Text style={styles.footnote}>Use only when parked or as a passenger.</Text>
        </ScrollView>
      </SafeAreaView>
    </Background>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: spacing.xl,
  },
  bigWrap: {
    alignItems: 'center',
    paddingVertical: spacing.lg,
    gap: spacing.sm,
  },
  bigNumber: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 144,
    lineHeight: 150,
  },
  chart: {
    marginTop: spacing.lg,
    marginHorizontal: spacing.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.md,
  },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    height: 140,
    paddingTop: spacing.sm,
  },
  barCol: {
    alignItems: 'center',
    gap: spacing.xs,
    width: 28,
  },
  bar: {
    width: 16,
  },
  barLabel: {
    fontFamily: fonts.mono,
    fontSize: 10,
    color: colors.muted,
    letterSpacing: 1.2,
  },
  section: {
    marginTop: spacing.xl,
    marginHorizontal: spacing.lg,
    gap: spacing.md,
  },
  achList: {
    gap: spacing.sm,
  },
  achCard: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: spacing.md,
    gap: spacing.xs,
  },
  achCardLocked: {
    borderStyle: 'dashed',
    borderColor: colors.border,
    opacity: 0.55,
  },
  achTitle: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 22,
  },
  achBody: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 11,
    lineHeight: 16,
  },
  achStatus: {
    fontFamily: fonts.monoBold,
    color: colors.success,
    fontSize: 10,
    letterSpacing: 1.4,
    marginTop: spacing.xs,
  },
  dim: {
    color: colors.muted,
  },
  legalLink: {
    alignItems: 'center',
    marginTop: spacing.xl,
    paddingVertical: spacing.sm,
  },
  legalLinkLabel: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.4,
  },
  footnote: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.2,
    textAlign: 'center',
    marginTop: spacing.md,
    paddingHorizontal: spacing.lg,
  },
});
