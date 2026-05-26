import React from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import Constants from 'expo-constants';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { Toggle } from '@/components/Toggle';
import { useStore } from '@/state/useStore';
import { setAnalyticsOptOut } from '@/services/analytics';
import { TRACKER_MODE } from '@/services/tracker';
import { DETECTOR_MODE } from '@/services/lightDetection';
import { colors, fonts, spacing, typography } from '@/theme';

export default function Settings() {
  const router = useRouter();
  const analyticsOptOut = useStore((s) => s.analyticsOptOut);
  const setOptOut = useStore((s) => s.setAnalyticsOptOut);
  const resetSession = useStore((s) => s.resetSession);
  const resetAll = useStore((s) => s.resetAll);

  const onToggleAnalytics = (enabled: boolean) => {
    const optedOut = !enabled;
    setOptOut(optedOut);
    setAnalyticsOptOut(optedOut);
  };

  const confirmClearStops = () => {
    Alert.alert('Clear today’s stops?', 'This removes the Auto-Track log. Your streak stays.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Clear', style: 'destructive', onPress: resetSession },
    ]);
  };

  const confirmResetAll = () => {
    Alert.alert(
      'Reset all data?',
      'Wipes your streak, attention, reclaimed seconds, achievements, and stops. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Reset everything', style: 'destructive', onPress: resetAll },
      ],
    );
  };

  const version = Constants.expoConfig?.version ?? '0.1.0';

  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <BackHeader eyebrow="SETTINGS" title="Your controls." />

          <View style={styles.section}>
            <Text style={typography.eyebrow}>PRIVACY</Text>
            <View style={styles.row}>
              <View style={styles.rowText}>
                <Text style={styles.rowTitle}>Anonymous usage events</Text>
                <Text style={styles.rowBody}>
                  Aggregate counts only — sessions, lights caught, share exports. No identifiers, no
                  location, no screen contents. Helps us improve the app.
                </Text>
              </View>
              <Toggle value={!analyticsOptOut} onChange={onToggleAnalytics} />
            </View>
          </View>

          <View style={styles.section}>
            <Text style={typography.eyebrow}>DATA</Text>
            <Pressable style={styles.actionRow} onPress={confirmClearStops}>
              <Text style={styles.actionLabel}>Clear today’s stops</Text>
              <Text style={styles.actionArrow}>→</Text>
            </Pressable>
            <Pressable style={styles.actionRow} onPress={confirmResetAll}>
              <Text style={[styles.actionLabel, { color: colors.danger }]}>Reset all data</Text>
              <Text style={[styles.actionArrow, { color: colors.danger }]}>→</Text>
            </Pressable>
          </View>

          <View style={styles.section}>
            <Text style={typography.eyebrow}>ABOUT</Text>
            <Pressable style={styles.actionRow} onPress={() => router.push('/legal')}>
              <Text style={styles.actionLabel}>Terms · Privacy · Safety</Text>
              <Text style={styles.actionArrow}>→</Text>
            </Pressable>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>VERSION</Text>
              <Text style={styles.metaValue}>{version}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>DETECTION MODE</Text>
              <Text style={styles.metaValue}>{DETECTOR_MODE}</Text>
            </View>
            <View style={styles.metaRow}>
              <Text style={styles.metaLabel}>TRACKER MODE</Text>
              <Text style={styles.metaValue}>{TRACKER_MODE}</Text>
            </View>
          </View>

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
  section: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  rowText: {
    flex: 1,
    gap: 4,
  },
  rowTitle: {
    fontFamily: fonts.serifItalic,
    color: colors.text,
    fontSize: 20,
  },
  rowBody: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 11,
    lineHeight: 16,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderColor: colors.border,
    paddingVertical: spacing.md,
  },
  actionLabel: {
    fontFamily: fonts.mono,
    color: colors.text,
    fontSize: 14,
  },
  actionArrow: {
    fontFamily: fonts.mono,
    color: colors.accent,
    fontSize: 16,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  metaLabel: {
    fontFamily: fonts.mono,
    color: colors.muted,
    fontSize: 10,
    letterSpacing: 1.4,
  },
  metaValue: {
    fontFamily: fonts.mono,
    color: colors.text,
    fontSize: 12,
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
