import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { colors } from '@/theme';

interface Props {
  value: boolean;
  onChange: (v: boolean) => void;
}

export function Toggle({ value, onChange }: Props) {
  const offset = useSharedValue(value ? 1 : 0);
  offset.value = withTiming(value ? 1 : 0, { duration: 160 });

  const knob = useAnimatedStyle(() => ({
    transform: [{ translateX: offset.value * 20 }],
  }));

  return (
    <Pressable
      onPress={() => onChange(!value)}
      hitSlop={8}
      style={[styles.track, { backgroundColor: value ? colors.accent : colors.border }]}
    >
      <Animated.View style={[styles.knob, knob]}>
        <View />
      </Animated.View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  track: {
    width: 44,
    height: 24,
    padding: 3,
    justifyContent: 'center',
  },
  knob: {
    width: 18,
    height: 18,
    backgroundColor: colors.text,
  },
});
