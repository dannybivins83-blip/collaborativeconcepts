import React from 'react';
import { StyleSheet, View, ViewStyle } from 'react-native';
import Svg, { Defs, RadialGradient, Rect, Stop } from 'react-native-svg';
import { colors } from '@/theme';

interface Props {
  children?: React.ReactNode;
  style?: ViewStyle;
}

export function Background({ children, style }: Props) {
  return (
    <View style={[styles.root, style]}>
      <Svg style={StyleSheet.absoluteFill} pointerEvents="none">
        <Defs>
          <RadialGradient id="bg" cx="50%" cy="20%" r="120%">
            <Stop offset="0%" stopColor={colors.bgStart} />
            <Stop offset="55%" stopColor={colors.bgMid} />
            <Stop offset="100%" stopColor={colors.bgEnd} />
          </RadialGradient>
        </Defs>
        <Rect x="0" y="0" width="100%" height="100%" fill="url(#bg)" />
      </Svg>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.bgEnd,
  },
});
