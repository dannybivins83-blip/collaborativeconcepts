import React, { useRef } from 'react';
import {
  DimensionValue,
  GestureResponderEvent,
  LayoutChangeEvent,
  PanResponder,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors, spacing, typography } from '@/theme';

interface Props {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
}

export function Slider({ label, value, min, max, step = 1, unit = '', onChange }: Props) {
  const widthRef = useRef(0);
  const containerX = useRef(0);

  const setFromX = (x: number) => {
    const w = widthRef.current || 1;
    const ratio = Math.max(0, Math.min(1, (x - containerX.current) / w));
    let next = min + ratio * (max - min);
    next = Math.round(next / step) * step;
    next = Math.max(min, Math.min(max, next));
    if (next !== value) onChange(next);
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (e: GestureResponderEvent) => setFromX(e.nativeEvent.pageX),
      onPanResponderMove: (e: GestureResponderEvent) => setFromX(e.nativeEvent.pageX),
    }),
  ).current;

  const ratio = (value - min) / (max - min);
  const pct = `${Math.max(0, Math.min(1, ratio)) * 100}%` as DimensionValue;

  const onLayout = (e: LayoutChangeEvent) => {
    widthRef.current = e.nativeEvent.layout.width;
  };

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        <Text style={typography.label}>{label}</Text>
        <Text style={styles.value}>
          {value}
          {unit}
        </Text>
      </View>
      <View
        style={styles.track}
        onLayout={onLayout}
        onStartShouldSetResponder={() => true}
        onResponderRelease={(e) => {
          containerX.current = e.nativeEvent.pageX - e.nativeEvent.locationX;
          setFromX(e.nativeEvent.pageX);
        }}
        {...panResponder.panHandlers}
      >
        <View style={[styles.fill, { width: pct }]} />
        <View style={[styles.thumb, { left: pct }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  value: {
    fontFamily: 'JetBrainsMono',
    color: colors.text,
    fontSize: 14,
  },
  track: {
    height: 4,
    backgroundColor: colors.border,
    borderRadius: 0,
    position: 'relative',
    justifyContent: 'center',
  },
  fill: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    backgroundColor: colors.accent,
  },
  thumb: {
    position: 'absolute',
    width: 14,
    height: 14,
    marginLeft: -7,
    top: -5,
    backgroundColor: colors.text,
    borderWidth: 2,
    borderColor: colors.accent,
  },
});
