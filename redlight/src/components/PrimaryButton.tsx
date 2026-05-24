import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, ViewStyle } from 'react-native';
import { colors, spacing } from '@/theme';

interface Props {
  label: string;
  sub?: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  tone?: 'accent' | 'success' | 'danger' | 'ghost';
  style?: ViewStyle;
}

const TONE_MAP = {
  accent: { bg: colors.accent, fg: '#0a0807' },
  success: { bg: colors.success, fg: '#0a0807' },
  danger: { bg: colors.danger, fg: '#f5e9d4' },
  ghost: { bg: 'transparent', fg: colors.text },
} as const;

export function PrimaryButton({ label, sub, onPress, loading, disabled, tone = 'accent', style }: Props) {
  const t = TONE_MAP[tone];
  const isGhost = tone === 'ghost';
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.btn,
        { backgroundColor: t.bg },
        isGhost && { borderWidth: 1, borderColor: colors.borderStrong },
        pressed && { opacity: 0.8 },
        disabled && { opacity: 0.4 },
        style,
      ]}
    >
      <View style={styles.row}>
        {loading ? (
          <ActivityIndicator color={t.fg} />
        ) : (
          <>
            <Text style={[styles.label, { color: t.fg }]}>{label}</Text>
            {sub ? <Text style={[styles.sub, { color: t.fg }]}>{sub}</Text> : null}
          </>
        )}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 12,
  },
  label: {
    fontFamily: 'JetBrainsMono-Bold',
    fontSize: 13,
    letterSpacing: 1.4,
    textTransform: 'uppercase',
  },
  sub: {
    fontFamily: 'JetBrainsMono',
    fontSize: 11,
    opacity: 0.7,
  },
});
