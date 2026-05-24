import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';
import { PulseDot } from '@/components/PulseDot';
import { useStore } from '@/state/useStore';
import { createLightDetector, LightColor, LightDetector } from '@/services/lightDetection';
import { Events } from '@/services/analytics';
import { colors, fonts, spacing, typography } from '@/theme';

type Phase = 'setup' | 'red' | 'green' | 'missed' | 'result';

const REACT_WINDOW_MS = 4000;

export default function CameraScreen() {
  const router = useRouter();
  const [permission, requestPermission] = useCameraPermissions();
  const [phase, setPhase] = useState<Phase>('setup');
  const [elapsed, setElapsed] = useState(0);
  const recordLightCatch = useStore((s) => s.recordLightCatch);
  const recordLightMiss = useStore((s) => s.recordLightMiss);
  const reactionPenalty = useStore((s) => s.preferences.reactionPenalty);

  const detectorRef = useRef<LightDetector | null>(null);
  const redStartedAt = useRef<number | null>(null);
  const greenStartedAt = useRef<number | null>(null);
  const missTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const elapsedTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const flashOpacity = useSharedValue(0);
  const flashStyle = useAnimatedStyle(() => ({ opacity: flashOpacity.value }));

  const pulse = useSharedValue(1);
  useEffect(() => {
    pulse.value = withRepeat(
      withTiming(1.06, { duration: 900, easing: Easing.inOut(Easing.ease) }),
      -1,
      true,
    );
  }, [pulse]);
  const greenBtnStyle = useAnimatedStyle(() => ({ transform: [{ scale: pulse.value }] }));

  const cleanup = useCallback(() => {
    detectorRef.current?.stop();
    detectorRef.current = null;
    if (missTimer.current) clearTimeout(missTimer.current);
    missTimer.current = null;
    if (elapsedTimer.current) clearInterval(elapsedTimer.current);
    elapsedTimer.current = null;
  }, []);

  useEffect(() => () => cleanup(), [cleanup]);

  useEffect(() => {
    if (!permission?.granted) return;
    if (phase !== 'setup') return;
  }, [permission, phase]);

  const onLightChange = useCallback(
    (color: LightColor) => {
      if (color === 'red') {
        redStartedAt.current = Date.now();
        greenStartedAt.current = null;
        setElapsed(0);
        if (elapsedTimer.current) clearInterval(elapsedTimer.current);
        elapsedTimer.current = setInterval(() => {
          if (redStartedAt.current) {
            setElapsed(Math.floor((Date.now() - redStartedAt.current) / 1000));
          }
        }, 250);
        setPhase('red');
      } else if (color === 'green') {
        greenStartedAt.current = Date.now();
        if (elapsedTimer.current) clearInterval(elapsedTimer.current);
        elapsedTimer.current = null;
        setPhase('green');
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium).catch(() => {});
        if (missTimer.current) clearTimeout(missTimer.current);
        missTimer.current = setTimeout(() => {
          setPhase('missed');
          recordLightMiss(reactionPenalty);
          Events.lightMissed();
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {});
        }, REACT_WINDOW_MS);
      }
    },
    [recordLightMiss, reactionPenalty],
  );

  const beginDrive = useCallback(async () => {
    if (!permission?.granted) {
      const res = await requestPermission();
      if (!res.granted) return;
    }
    const detector = createLightDetector();
    detectorRef.current = detector;
    await detector.start(onLightChange);
    Events.sessionStarted();
  }, [permission, requestPermission, onLightChange]);

  const onCatch = useCallback(() => {
    if (phase !== 'green') return;
    if (missTimer.current) clearTimeout(missTimer.current);
    missTimer.current = null;
    const reactionMs = greenStartedAt.current ? Date.now() - greenStartedAt.current : 0;
    setPhase('result');
    recordLightCatch(reactionPenalty);
    Events.lightCaught(reactionMs);
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
    flashOpacity.value = withSequence(
      withTiming(0.6, { duration: 120 }),
      withTiming(0, { duration: 500 }),
    );
  }, [phase, recordLightCatch, reactionPenalty, flashOpacity]);

  const exit = useCallback(() => {
    cleanup();
    router.back();
  }, [cleanup, router]);

  if (!permission) {
    return <View style={styles.root} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.permWrap}>
        <Text style={styles.permTitle}>Camera access</Text>
        <Text style={styles.permBody}>
          Redlight needs the camera to detect when a light turns green. The phone must be mounted —
          the app never asks you to look at the screen while driving.
        </Text>
        <Pressable style={styles.permBtn} onPress={requestPermission}>
          <Text style={styles.permBtnLabel}>GRANT CAMERA</Text>
        </Pressable>
        <Pressable style={[styles.permBtn, styles.permBtnGhost]} onPress={exit}>
          <Text style={[styles.permBtnLabel, { color: colors.text }]}>BACK</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <CameraView style={StyleSheet.absoluteFill} facing="back" />

      <Animated.View
        pointerEvents="none"
        style={[StyleSheet.absoluteFill, { backgroundColor: colors.success }, flashStyle]}
      />

      <View style={styles.hudTop}>
        <Pressable onPress={exit} hitSlop={16}>
          <Text style={styles.hudText}>← EXIT</Text>
        </Pressable>
        <View style={styles.recRow}>
          <PulseDot color={colors.danger} size={8} />
          <Text style={styles.hudText}>RECORDING</Text>
        </View>
      </View>

      <View style={styles.actionPanel}>
        {phase === 'setup' && (
          <View style={styles.panelInner}>
            <Text style={typography.eyebrow}>STEP 1</Text>
            <Text style={styles.panelTitle}>
              Point at the windshield. We’ll detect lights automatically.
            </Text>
            <Pressable style={styles.cta} onPress={beginDrive}>
              <Text style={styles.ctaLabel}>BEGIN DRIVE →</Text>
            </Pressable>
            <Text style={styles.disclaimer}>
              Mount your phone now. Do not touch the screen while driving.
            </Text>
          </View>
        )}

        {phase === 'red' && (
          <View style={styles.panelInner}>
            <Text style={typography.eyebrow}>RED LIGHT</Text>
            <Text style={styles.elapsed}>{elapsed}s</Text>
            <Text style={styles.disclaimer}>Eyes on the road. We’ll alert you when it’s green.</Text>
          </View>
        )}

        {phase === 'green' && (
          <View style={styles.panelInner}>
            <Text style={[typography.eyebrow, { color: colors.success }]}>GREEN — GO</Text>
            <Animated.View style={greenBtnStyle}>
              <Pressable
                onPress={onCatch}
                style={({ pressed }) => [styles.greenBtn, pressed && { opacity: 0.85 }]}
              >
                <Text style={styles.greenBtnLabel}>I SEE IT ✓</Text>
              </Pressable>
            </Animated.View>
            <Text style={styles.disclaimer}>4-second window. Tap to confirm.</Text>
          </View>
        )}

        {phase === 'missed' && (
          <View style={styles.panelInner}>
            <Text style={[typography.eyebrow, { color: colors.danger }]}>MISSED</Text>
            <Text style={[styles.panelTitle, { color: colors.danger }]}>
              −{reactionPenalty} seconds of your life
            </Text>
            <Text style={styles.disclaimer}>…and the car behind you honked.</Text>
            <Pressable style={styles.cta} onPress={() => setPhase('red')}>
              <Text style={styles.ctaLabel}>NEXT LIGHT →</Text>
            </Pressable>
          </View>
        )}

        {phase === 'result' && (
          <View style={styles.panelInner}>
            <Text style={[typography.eyebrow, { color: colors.success }]}>RECLAIMED</Text>
            <Text style={[styles.panelTitle, { color: colors.success }]}>
              +{reactionPenalty} SECONDS
            </Text>
            <Text style={styles.disclaimer}>Nice. You saw it.</Text>
            <Pressable style={styles.cta} onPress={() => setPhase('red')}>
              <Text style={styles.ctaLabel}>NEXT LIGHT →</Text>
            </Pressable>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#000',
  },
  hudTop: {
    position: 'absolute',
    top: 56,
    left: spacing.lg,
    right: spacing.lg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  hudText: {
    fontFamily: fonts.monoBold,
    color: colors.text,
    fontSize: 11,
    letterSpacing: 1.4,
    textShadowColor: 'rgba(0,0,0,0.6)',
    textShadowRadius: 4,
  },
  recRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  actionPanel: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(10, 8, 7, 0.94)',
    borderTopWidth: 1,
    borderTopColor: colors.borderStrong,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.xl + 12,
  },
  panelInner: {
    gap: spacing.md,
  },
  panelTitle: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 28,
    lineHeight: 32,
  },
  elapsed: {
    fontFamily: fonts.serifItalic,
    color: colors.danger,
    fontSize: 80,
    lineHeight: 84,
  },
  cta: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignSelf: 'flex-start',
  },
  ctaLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 13,
    letterSpacing: 1.4,
  },
  greenBtn: {
    backgroundColor: colors.success,
    paddingVertical: 24,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
  },
  greenBtnLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 22,
    letterSpacing: 2,
  },
  disclaimer: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
  permWrap: {
    flex: 1,
    backgroundColor: colors.bgEnd,
    padding: spacing.lg,
    justifyContent: 'center',
    gap: spacing.md,
  },
  permTitle: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 36,
  },
  permBody: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 13,
    lineHeight: 19,
  },
  permBtn: {
    backgroundColor: colors.accent,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  permBtnGhost: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: colors.borderStrong,
  },
  permBtnLabel: {
    fontFamily: fonts.monoBold,
    color: '#0a0807',
    fontSize: 13,
    letterSpacing: 1.4,
  },
});
