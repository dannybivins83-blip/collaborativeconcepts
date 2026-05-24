import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors, spacing, typography } from '@/theme';

interface Props {
  eyebrow: string;
  title: string;
  body?: string;
  onPress?: () => void;
}

export function SmallCard({ eyebrow, title, body, onPress }: Props) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.wrap, pressed && { opacity: 0.7 }]}
    >
      <Text style={typography.eyebrow}>{eyebrow}</Text>
      <Text style={styles.title}>{title}</Text>
      {body ? <Text style={styles.body}>{body}</Text> : null}
      <View style={styles.arrowRow}>
        <Text style={styles.arrow}>→</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.cardBg,
    padding: spacing.md,
    gap: spacing.sm,
    minHeight: 140,
  },
  title: {
    fontFamily: 'DMSerifDisplay-Italic',
    color: colors.text,
    fontSize: 22,
    lineHeight: 26,
  },
  body: {
    fontFamily: 'JetBrainsMono',
    color: colors.muted,
    fontSize: 11,
    lineHeight: 16,
  },
  arrowRow: {
    marginTop: 'auto',
    alignItems: 'flex-end',
  },
  arrow: {
    fontFamily: 'JetBrainsMono',
    color: colors.accent,
    fontSize: 18,
  },
});
