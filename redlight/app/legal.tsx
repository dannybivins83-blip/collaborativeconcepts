import React from 'react';
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Background } from '@/components/Background';
import { BackHeader } from '@/components/BackHeader';
import { colors, fonts, spacing, typography } from '@/theme';

const TERMS_URL = 'https://redlight.app/terms';
const PRIVACY_URL = 'https://redlight.app/privacy';
const CONTACT_EMAIL = 'support@redlight.app';

export default function Legal() {
  return (
    <Background>
      <SafeAreaView style={{ flex: 1 }} edges={['top']}>
        <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
          <BackHeader eyebrow="LEGAL" title="The fine print." />

          <View style={styles.section}>
            <Text style={typography.eyebrow}>SAFETY DISCLAIMER</Text>
            <Text style={styles.body}>
              Redlight is not a driver-assistance system. It is an attention-and-habit tracker. The
              camera’s green-light detection can produce false positives and false negatives. You
              are responsible for visually verifying every traffic signal yourself and for
              operating your vehicle safely and lawfully.
            </Text>
            <Text style={styles.body}>
              Mount your phone before driving. Do not touch the screen while the vehicle is moving.
              Use the calculator, share, streak, and track screens only when parked or as a
              passenger.
            </Text>
          </View>

          <View style={styles.section}>
            <Text style={typography.eyebrow}>WHAT WE COLLECT</Text>
            <Text style={styles.body}>
              Redlight is local-first. Your camera feed, location, and stop history never leave
              your device. Anonymous usage counts (sessions, lights caught, share-card exports)
              are sent to our analytics provider so we can improve the product. No personal
              identifiers, no location, no screen contents.
            </Text>
          </View>

          <View style={styles.section}>
            <Pressable onPress={() => Linking.openURL(TERMS_URL).catch(() => {})}>
              <Text style={styles.link}>Full Terms of Use ↗</Text>
            </Pressable>
            <Pressable onPress={() => Linking.openURL(PRIVACY_URL).catch(() => {})}>
              <Text style={styles.link}>Full Privacy Policy ↗</Text>
            </Pressable>
            <Pressable onPress={() => Linking.openURL(`mailto:${CONTACT_EMAIL}`).catch(() => {})}>
              <Text style={styles.link}>Contact: {CONTACT_EMAIL} ↗</Text>
            </Pressable>
          </View>

          <Text style={styles.footnote}>
            Use only when parked or as a passenger.
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
  section: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.sm,
  },
  body: {
    fontFamily: fonts.mono,
    color: colors.text,
    fontSize: 13,
    lineHeight: 19,
  },
  link: {
    fontFamily: fonts.monoBold,
    color: colors.accent,
    fontSize: 12,
    letterSpacing: 1.2,
    paddingVertical: 6,
    textTransform: 'uppercase',
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
