import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors, fonts, spacing, typography } from '@/theme';

interface Props {
  label: string;
  value: string;
  sub?: string;
  tone?: 'default' | 'danger' | 'success';
}

export function BigStat({ label, value, sub, tone = 'default' }: Props) {
  const color =
    tone === 'danger' ? colors.danger : tone === 'success' ? colors.success : colors.text;
  return (
    <View style={styles.wrap}>
      <Text style={typography.label}>{label}</Text>
      <Text style={[styles.value, { color }]}>{value}</Text>
      {sub ? <Text style={styles.sub}>{sub}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingVertical: spacing.md,
    gap: spacing.xs,
  },
  value: {
    fontFamily: fonts.serifItalic,
    fontSize: 64,
    lineHeight: 68,
  },
  sub: {
    fontFamily: fonts.mono,
    fontSize: 11,
    color: colors.muted,
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  },
});
