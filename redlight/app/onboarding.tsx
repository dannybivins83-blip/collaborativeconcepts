import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { Background } from '@/components/Background';
import { useStore } from '@/state/useStore';
import { scheduleDailyStreakReminder } from '@/services/notifications';
import { colors, fonts, spacing, typography } from '@/theme';

export default function Onboarding() {
  const router = useRouter();
  const setOnboarded = useStore((s) => s.setOnboarded);
  const [confirmed, setConfirmed] = useState(false);

  const finish = async () => {
    setOnboarded(true);
    scheduleDailyStreakReminder().catch(() => {});
    router.replace('/');
  };

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top', 'bottom']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <Animated.View entering={FadeInDown.duration(500)}>
            <Text style={typography.eyebrow}>FIRST RUN</Text>
            <Text style={styles.headline}>Mount your phone first.</Text>
          </Animated.View>

          <Animated.View entering={FadeInDown.duration(500).delay(120)} style={styles.bullets}>
            <Bullet n="01" label="MOUNT" body="Put your phone in a dash or windshield mount before you drive." />
            <Bullet n="02" label="DON’T TOUCH" body="The app never asks you to look at the screen while moving." />
            <Bullet n="03" label="LISTEN" body="Haptic + chime when the light goes green — the camera does the watching." />
          </Animated.View>

          <Animated.View entering={FadeInDown.duration(500).delay(240)}>
            <View style={styles.disclaimer}>
              <Text style={styles.disclaimerEyebrow}>SAFETY NOTICE</Text>
              <Text style={styles.disclaimerBody}>
                Redlight is not a driver-assistance system. It can produce false positives and
                false negatives. You remain responsible for visually verifying every traffic
                signal and operating your vehicle safely. By continuing you accept the Terms of
                Use and Privacy Policy.
              </Text>
            </View>

            <Pressable
              style={styles.checkRow}
              onPress={() => setConfirmed((v) => !v)}
              hitSlop={8}
            >
              <View style={[styles.check, confirmed && styles.checkActive]}>
                {confirmed ? <Text style={styles.checkMark}>✓</Text> : null}
              </View>
              <Text style={styles.checkLabel}>
                I confirm my phone is mounted, I will not touch it while driving, and I accept the
                Terms and Privacy Policy.
              </Text>
            </Pressable>
          </Animated.View>

          <Pressable
            disabled={!confirmed}
            onPress={finish}
            style={({ pressed }) => [
              styles.cta,
              !confirmed && { opacity: 0.35 },
              pressed && { opacity: 0.85 },
            ]}
          >
            <Text style={styles.ctaLabel}>BEGIN →</Text>
          </Pressable>
        </ScrollView>
      </SafeAreaView>
    </Background>
  );
}

function Bullet({ n, label, body }: { n: string; label: string; body: string }) {
  return (
    <View style={styles.bullet}>
      <Text style={styles.bulletN}>{n}</Text>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={[typography.label, { color: colors.accent }]}>{label}</Text>
        <Text style={styles.bulletBody}>{body}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: {
    padding: spacing.lg,
    paddingTop: spacing.xl,
    gap: spacing.xl,
    flexGrow: 1,
  },
  headline: {
    ...typography.serifHero,
    fontSize: 48,
    lineHeight: 52,
    marginTop: spacing.sm,
  },
  bullets: {
    gap: spacing.lg,
  },
  bullet: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  bulletN: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 11,
    width: 28,
    paddingTop: 2,
    letterSpacing: 1.4,
  },
  bulletBody: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 20,
    lineHeight: 26,
  },
  disclaimer: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: spacing.md,
    gap: spacing.sm,
    marginBottom: spacing.lg,
  },
  disclaimerEyebrow: {
    fontFamily: fonts.monoBold,
    fontSize: 10,
    letterSpacing: 1.6,
    color: colors.danger,
    textTransform: 'uppercase',
  },
  disclaimerBody: {
    fontFamily: fonts.mono,
    color: colors.text,
    fontSize: 12,
    lineHeight: 18,
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
    borderTopWidth: 1,
    borderColor: colors.border,
    paddingTop: spacing.lg,
  },
  check: {
    width: 22,
    height: 22,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  checkMark: {
    color: '#0a0807',
    fontWeight: '700',
  },
  checkLabel: {
    flex: 1,
    fontFamily: fonts.mono,
    color: colors.text,
    fontSize: 13,
    lineHeight: 19,
  },
  cta: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    marginTop: 'auto',
  },
  ctaLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 14,
    letterSpacing: 1.6,
  },
});
