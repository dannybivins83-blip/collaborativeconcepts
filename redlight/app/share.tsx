import React, { useMemo, useRef, useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { captureRef } from 'react-native-view-shot';
import * as Sharing from 'expo-sharing';
import Svg, { Defs, LinearGradient, Rect, Stop } from 'react-native-svg';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { ShareBtn } from '@/components/ShareBtn';
import { useStore } from '@/state/useStore';
import { computeStats, fmt } from '@/services/math';
import { Events } from '@/services/analytics';
import { colors, fonts, spacing } from '@/theme';

export default function Share() {
  const prefs = useStore((s) => s.preferences);
  const streak = useStore((s) => s.streak);
  const cardRef = useRef<View>(null);
  const [busy, setBusy] = useState(false);

  const stats = useMemo(() => computeStats(prefs), [prefs]);
  const lifetimeTax = fmt(stats.totalLife);
  const reclaimable = fmt(stats.reclaimLife);

  const onShare = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const uri = await captureRef(cardRef, { format: 'png', quality: 1, result: 'tmpfile' });
      const can = await Sharing.isAvailableAsync();
      if (!can) {
        Alert.alert('Sharing unavailable', `Image saved to ${uri}`);
        return;
      }
      await Sharing.shareAsync(uri, { mimeType: 'image/png', dialogTitle: 'Share your time tax' });
      Events.shareCardExported(stats.totalLife, stats.reclaimLife);
    } catch (e) {
      const m = e instanceof Error ? e.message : 'Could not export the card.';
      Alert.alert('Export failed', m);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <BackHeader eyebrow="SHARE" title="Post your number." />

          <View style={styles.cardWrap}>
            <View ref={cardRef} collapsable={false} style={styles.card}>
              <Svg style={StyleSheet.absoluteFill} pointerEvents="none">
                <Defs>
                  <LinearGradient id="cardBg" x1="0" y1="0" x2="0" y2="1">
                    <Stop offset="0%" stopColor="#1a1410" />
                    <Stop offset="55%" stopColor="#2a1810" />
                    <Stop offset="100%" stopColor="#ff6b35" />
                  </LinearGradient>
                </Defs>
                <Rect x="0" y="0" width="100%" height="100%" fill="url(#cardBg)" />
              </Svg>

              <View style={styles.cardInner}>
                <View>
                  <Text style={styles.cardEyebrow}>REDLIGHT · TIME TAX</Text>
                  <Text style={styles.cardLine1}>
                    I’ll waste{' '}
                    <Text style={styles.cardLifetime}>{lifetimeTax}</Text>
                    {' '}of my life sitting at red lights.
                  </Text>
                </View>

                <View style={styles.cardDivider} />

                <View>
                  <Text style={styles.cardEyebrow}>BUT IF I LOOK UP</Text>
                  <Text style={styles.cardLine2}>
                    I get back{' '}
                    <Text style={styles.cardReclaim}>{reclaimable}</Text>.
                  </Text>
                </View>

                <View style={styles.cardFootRow}>
                  <View style={styles.streakBadge}>
                    <Text style={styles.badgeNum}>{streak}</Text>
                    <Text style={styles.badgeLabel}>DAY STREAK</Text>
                  </View>
                  <Text style={styles.watermark}>redlight.app/me</Text>
                </View>
              </View>
            </View>
          </View>

          <View style={styles.btnRow}>
            <ShareBtn label="Story" onPress={onShare} />
            <ShareBtn label="Post" onPress={onShare} />
            <ShareBtn label="DM" onPress={onShare} />
          </View>

          <Text style={styles.footnote}>
            Tap any button to open the share sheet. Use only when parked or as a passenger.
          </Text>
        </ScrollView>
      </SafeAreaView>
    </Background>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingBottom: spacing.xl,
  },
  cardWrap: {
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
  },
  card: {
    width: 270,
    aspectRatio: 9 / 16,
    overflow: 'hidden',
  },
  cardInner: {
    flex: 1,
    padding: 24,
    justifyContent: 'space-between',
  },
  cardEyebrow: {
    fontFamily: fonts.monoBold,
    fontSize: 9,
    letterSpacing: 1.6,
    color: '#f5e9d4',
    opacity: 0.75,
    textTransform: 'uppercase',
  },
  cardLine1: {
    fontFamily: fonts.serifItalic,
    color: '#f5e9d4',
    fontSize: 22,
    lineHeight: 26,
    marginTop: 8,
  },
  cardLifetime: {
    color: '#ff2d2d',
  },
  cardDivider: {
    height: 1,
    backgroundColor: 'rgba(245, 233, 212, 0.25)',
  },
  cardLine2: {
    fontFamily: fonts.serifItalic,
    color: '#f5e9d4',
    fontSize: 22,
    lineHeight: 26,
    marginTop: 8,
  },
  cardReclaim: {
    color: '#6dffa6',
  },
  cardFootRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
  },
  streakBadge: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: 'rgba(245, 233, 212, 0.55)',
    alignItems: 'center',
  },
  badgeNum: {
    fontFamily: fonts.serifItalic,
    color: '#f5e9d4',
    fontSize: 28,
    lineHeight: 30,
  },
  badgeLabel: {
    fontFamily: fonts.monoBold,
    color: '#f5e9d4',
    fontSize: 8,
    letterSpacing: 1.4,
  },
  watermark: {
    fontFamily: fonts.mono,
    color: '#f5e9d4',
    fontSize: 10,
    opacity: 0.8,
    letterSpacing: 1.2,
  },
  btnRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    marginTop: spacing.xl,
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
