import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { colors, spacing, typography } from '@/theme';

interface Props {
  title: string;
  eyebrow?: string;
}

export function BackHeader({ title, eyebrow }: Props) {
  const router = useRouter();
  return (
    <View style={styles.wrap}>
      <Pressable
        onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
        hitSlop={16}
      >
        <Text style={[typography.label, styles.back]}>← Back</Text>
      </Pressable>
      {eyebrow ? <Text style={[typography.eyebrow, { marginTop: spacing.lg }]}>{eyebrow}</Text> : null}
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.lg,
  },
  back: {
    color: colors.muted,
    fontSize: 11,
    letterSpacing: 1.4,
  },
  title: {
    fontFamily: 'DMSerifDisplay-Italic',
    fontSize: 44,
    color: colors.text,
    marginTop: spacing.sm,
    lineHeight: 48,
  },
});
