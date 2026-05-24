import React from 'react';
import { StyleSheet, Text, View, ViewStyle } from 'react-native';
import { colors, fonts, typography } from '@/theme';

interface Props {
  label: string;
  value: string | number;
  accent?: boolean;
  style?: ViewStyle;
}

export function Stat({ label, value, accent, style }: Props) {
  return (
    <View style={[styles.wrap, style]}>
      <Text style={typography.label}>{label}</Text>
      <Text style={[styles.value, accent && { color: colors.accent }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'flex-start',
    gap: 6,
  },
  value: {
    fontFamily: fonts.serifItalic,
    fontSize: 30,
    color: colors.text,
    lineHeight: 34,
  },
});
