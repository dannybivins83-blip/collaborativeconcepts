import React, { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Tabs, useRouter, useSegments } from 'expo-router';
import * as Font from 'expo-font';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useStore } from '@/state/useStore';
import { colors } from '@/theme';

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const [fontsLoaded, setFontsLoaded] = React.useState(false);
  const hydrated = useStore((s) => s.hydrated);
  const onboarded = useStore((s) => s.onboarded);
  const router = useRouter();
  const segments = useSegments();

  useEffect(() => {
    (async () => {
      try {
        await Font.loadAsync({
          'DMSerifDisplay-Italic': require('../assets/fonts/DMSerifDisplay-Italic.ttf'),
          DMSerifDisplay: require('../assets/fonts/DMSerifDisplay-Regular.ttf'),
          JetBrainsMono: require('../assets/fonts/JetBrainsMono-Regular.ttf'),
          'JetBrainsMono-Bold': require('../assets/fonts/JetBrainsMono-Bold.ttf'),
        });
      } catch {
        // Fonts are optional at boot; README documents the asset drop-in.
      } finally {
        setFontsLoaded(true);
      }
    })();
  }, []);

  useEffect(() => {
    if (fontsLoaded && hydrated) {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [fontsLoaded, hydrated]);

  useEffect(() => {
    if (!hydrated || !fontsLoaded) return;
    const top = segments[0];
    const inOnboarding = top === 'onboarding';
    if (!onboarded && !inOnboarding) {
      router.replace('/onboarding');
    } else if (onboarded && inOnboarding) {
      router.replace('/');
    }
  }, [hydrated, fontsLoaded, onboarded, segments, router]);

  if (!fontsLoaded || !hydrated) {
    return (
      <View style={styles.boot}>
        <ActivityIndicator color={colors.accent} />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: colors.bgEnd }}>
      <SafeAreaProvider>
        <StatusBar style="light" />
        <Tabs
          screenOptions={{
            headerShown: false,
            tabBarStyle: {
              backgroundColor: colors.bgEnd,
              borderTopColor: colors.border,
              borderTopWidth: 1,
              height: 64,
              paddingTop: 8,
              paddingBottom: 8,
            },
            tabBarActiveTintColor: colors.accent,
            tabBarInactiveTintColor: colors.muted,
            tabBarLabelStyle: {
              fontFamily: 'JetBrainsMono-Bold',
              fontSize: 9,
              letterSpacing: 1.2,
              textTransform: 'uppercase',
            },
            tabBarIcon: () => null,
            tabBarIconStyle: { display: 'none' },
          }}
        >
          <Tabs.Screen name="index" options={{ title: 'Home', tabBarLabel: 'Home' }} />
          <Tabs.Screen name="calc" options={{ title: 'Math', tabBarLabel: 'Math' }} />
          <Tabs.Screen name="track" options={{ title: 'Track', tabBarLabel: 'Track' }} />
          <Tabs.Screen name="streak" options={{ title: 'Streak', tabBarLabel: 'Streak' }} />
          <Tabs.Screen name="share" options={{ title: 'Share', tabBarLabel: 'Share' }} />
          <Tabs.Screen
            name="camera"
            options={{
              href: null,
              tabBarStyle: { display: 'none' },
            }}
          />
          <Tabs.Screen
            name="onboarding"
            options={{
              href: null,
              tabBarStyle: { display: 'none' },
            }}
          />
        </Tabs>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  boot: {
    flex: 1,
    backgroundColor: colors.bgEnd,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
