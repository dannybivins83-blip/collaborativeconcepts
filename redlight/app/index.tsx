import React, { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Background } from '@/components/Background';
import { AttentionRing } from '@/components/AttentionRing';
import { Stat } from '@/components/Stat';
import { SmallCard } from '@/components/SmallCard';
import { useStore } from '@/state/useStore';
import { colors, fonts, spacing, typography } from '@/theme';

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function Home() {
  const router = useRouter();
  const streak = useStore((s) => s.streak);
  const todayAttention = useStore((s) => s.todayAttention);
  const secondsReclaimed = useStore((s) => s.secondsReclaimed);
  const weeklyCaught = useStore((s) => s.weeklyCaught);
  const weeklyGoalLights = useStore((s) => s.weeklyGoalLights);

  const goalRatio = useMemo(
    () => Math.min(1, weeklyCaught / Math.max(1, weeklyGoalLights)),
    [weeklyCaught, weeklyGoalLights],
  );

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={styles.scroll}
          showsVerticalScrollIndicator={false}
        >
          <Animated.View entering={FadeInDown.duration(500)} style={styles.header}>
            <View style={styles.headerTop}>
              <Text style={typography.eyebrow}>{greeting().toUpperCase()}, DRIVER</Text>
              <Pressable onPress={() => router.push('/settings')} hitSlop={12}>
                <Text style={styles.settingsLink}>SETTINGS</Text>
              </Pressable>
            </View>
            <Text style={styles.headline}>Today’s the day{'\n'}you look up.</Text>
          </Animated.View>

          <Animated.View
            entering={FadeInDown.duration(600).delay(120)}
            style={styles.ringWrap}
          >
            <AttentionRing percent={todayAttention} size={180} label="ATTENTION" />
          </Animated.View>

          <Animated.View
            entering={FadeInDown.duration(600).delay(240)}
            style={styles.statsRow}
          >
            <Stat label="STREAK" value={`${streak}d`} />
            <View style={styles.divider} />
            <Stat label="RECLAIMED" value={`${Math.round(secondsReclaimed)}s`} accent />
            <View style={styles.divider} />
            <Stat label="TODAY" value={`${Math.round(todayAttention)}%`} />
          </Animated.View>

          <Animated.View entering={FadeInDown.duration(600).delay(360)}>
            <Pressable
              onPress={() => router.push('/camera')}
              style={({ pressed }) => [styles.cta, pressed && { opacity: 0.85 }]}
            >
              <View style={styles.ctaRow}>
                <Text style={styles.ctaLabel}>START DRIVING SESSION</Text>
                <Text style={styles.ctaArrow}>→</Text>
              </View>
              <Text style={styles.ctaSub}>Open camera</Text>
            </Pressable>
          </Animated.View>

          <Animated.View
            entering={FadeInDown.duration(600).delay(440)}
            style={styles.challenge}
          >
            <View style={styles.challengeHead}>
              <Text style={typography.eyebrow}>WEEKLY CHALLENGE</Text>
              <Text style={styles.challengeCount}>
                {weeklyCaught}/{weeklyGoalLights}
              </Text>
            </View>
            <Text style={styles.challengeTitle}>Catch fifty greens this week.</Text>
            <View style={styles.bar}>
              <View style={[styles.barFill, { width: `${goalRatio * 100}%` }]} />
            </View>
          </Animated.View>

          <Animated.View
            entering={FadeInDown.duration(600).delay(520)}
            style={styles.cardsRow}
          >
            <SmallCard
              eyebrow="THE MATH"
              title="See your time tax."
              body="How long a life of red lights actually costs you."
              onPress={() => router.push('/calc')}
            />
            <SmallCard
              eyebrow="SHARE"
              title="Post your number."
              body="Export a card. Dare your group chat to beat it."
              onPress={() => router.push('/share')}
            />
          </Animated.View>

          <Text style={styles.footnote}>
            Use only when parked or as a passenger. Mount your phone before driving.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </Background>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.xl,
    gap: spacing.lg,
  },
  header: {
    gap: spacing.sm,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  settingsLink: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.4,
  },
  headline: {
    ...typography.serifH1,
    fontSize: 40,
    lineHeight: 44,
  },
  ringWrap: {
    alignItems: 'center',
    paddingVertical: spacing.md,
  },
  statsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.md,
  },
  divider: {
    width: 1,
    height: 36,
    backgroundColor: colors.border,
    marginHorizontal: spacing.md,
  },
  cta: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    gap: 6,
  },
  ctaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  ctaLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 13,
    letterSpacing: 1.4,
  },
  ctaArrow: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 18,
  },
  ctaSub: {
    fontFamily: fonts.mono,
    color: '#0a0807',
    fontSize: 11,
    opacity: 0.75,
  },
  challenge: {
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: spacing.sm,
  },
  challengeHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  challengeCount: {
    fontFamily: fonts.mono,
    color: colors.accent,
    fontSize: 13,
  },
  challengeTitle: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 22,
    lineHeight: 26,
  },
  bar: {
    height: 3,
    backgroundColor: colors.border,
    marginTop: spacing.sm,
  },
  barFill: {
    height: 3,
    backgroundColor: colors.accent,
  },
  cardsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  footnote: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.2,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
